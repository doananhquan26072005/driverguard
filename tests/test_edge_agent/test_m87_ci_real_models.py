"""M87: CI on the working branch, with the real model files and an FPS measurement (audit 08/10, A5 M5).

- Blocks 3, 4, 5, 6 on the real pretrained files, fed a face drawn with ellipses (tools/drawn_face.py,
  not a person) and frames without one. models/ is not in git: these tests skip where the files are
  missing, and fail instead under DG_REQUIRE_MODELS=1 (the CI job `models`).
- tools/benchmark.py --check: the exit code of the FPS gate, on fake samples.
- The workflow itself: it runs on a push to DAQuan and still has the two steps above.
"""

import dataclasses
import threading

import numpy as np
import pytest
import yaml

from edge_agent.capture import Frame
from edge_agent.config import PROJECT_ROOT, load_thresholds
from edge_agent.perception import PreprocessConfig, Preprocessor
from edge_agent.perception.eye_state import EyeStateConfig, EyeStateEstimator
from edge_agent.perception.features import FeatureConfig, FeatureExtractor
from edge_agent.perception.landmarks import FaceLandmarkDetector, LandmarkConfig
from edge_agent.perception.phone_detector import AsyncPhoneDetector, PhoneDetectorConfig, YoloPhoneModel
from tests.test_edge_agent.test_m42_soak import result, samples
from tools import benchmark as bm
from tools.drawn_face import drawn_face, drawn_face_frames
from tools.metrics import EvalConfig

TH = load_thresholds()
LANDMARKS = LandmarkConfig.from_dict(TH["landmarks"])
EYE = EyeStateConfig.from_dict(TH["eye_state"])
PHONE = PhoneDetectorConfig.from_dict(TH["phone"])
FPS = 30


def preprocessed(images):
    pre = Preprocessor(PreprocessConfig.from_dict(TH["preprocess"]))
    return [pre(Frame(img, i, i / FPS)) for i, img in enumerate(images)]


def sway(eyes_open, n=10):
    """The drawn face moving a pixel or two, as consecutive video frames."""
    return preprocessed([drawn_face(eyes_open=eyes_open, dx=i % 3) for i in range(n)])


# ---------------------------------------------------------------- the drawn face (no model)


def test_drawn_face_is_an_image_made_in_ram():
    opened, shut = drawn_face(640, 480), drawn_face(640, 480, eyes_open=False)
    assert opened.shape == (480, 640, 3) and opened.dtype == np.uint8
    assert (opened != shut).any() and (opened != drawn_face(640, 480, dx=2)).any()
    frames, described = drawn_face_frames(20, 320, 240)
    assert len(frames) == 20 and frames[0].shape == (240, 320, 3)
    assert "not a person" in described
    assert any((a != b).any() for a, b in zip(frames, frames[1:], strict=False))  # it moves: not a frozen camera


# ---------------------------------------------------------------- blocks 3 and 6 on face_landmarker.task


def test_real_landmarker_finds_the_drawn_face_and_block_6_reads_its_eyes(need_model):
    need_model(LANDMARKS.resolved_model_path())
    ext = FeatureExtractor(FeatureConfig.from_dict(TH["features"]))
    seen = {}
    for eyes_open in (True, False):
        with FaceLandmarkDetector(LANDMARKS) as detector:
            found = [detector.detect(p) for p in sway(eyes_open)]
        assert all(lm is not None for lm in found)
        last = found[-1]
        assert last.points.shape == (478, 3) and np.isfinite(last.points).all()
        assert last.num_faces == 1 and last.face_conf == pytest.approx(1.0)
        seen[eyes_open] = (last, ext(last, 0, 0.0))
    (lm_open, f_open), (lm_shut, f_shut) = seen[True], seen[False]
    assert f_open.ear > f_shut.ear + 0.2  # measured 0.41 against 0.02
    assert max(abs(f_open.yaw), abs(f_open.pitch), abs(f_open.roll)) < 15.0  # drawn facing the camera
    assert max(lm_open.eye_blink) < 0.2 and min(lm_shut.eye_blink) > 0.3  # measured 0.001 against 0.60


def test_real_landmarker_finds_no_face_in_frames_without_one(need_model):
    need_model(LANDMARKS.resolved_model_path())
    rng = np.random.default_rng(0)
    images = [np.full((720, 1280, 3), 128, np.uint8), rng.integers(0, 255, (720, 1280, 3), dtype=np.uint8)]
    with FaceLandmarkDetector(LANDMARKS) as detector:
        assert [detector.detect(p) for p in preprocessed(images)] == [None, None]


# ---------------------------------------------------------------- block 5 on open_closed_eye.onnx


def test_real_eye_state_cnn_runs_on_the_crops_block_3_gives(need_model):
    """The whole path of a triggered frame: landmarks -> eye crops -> CNN -> p_closed on the features.
    Which output is "closed" is pinned by test_eye_state.test_real_model_class_order."""
    need_model(LANDMARKS.resolved_model_path())
    need_model(EYE.resolved_model_path())
    ext = FeatureExtractor(FeatureConfig.from_dict(TH["features"]))
    p_closed = {}
    for eyes_open in (True, False):
        estimator = EyeStateEstimator(dataclasses.replace(EYE, always_run=True))
        with FaceLandmarkDetector(LANDMARKS) as detector:
            for i, p in enumerate(sway(eyes_open)):
                lm = detector.detect(p)
                feats = estimator(p, lm, ext(lm, i, i / FPS))
        assert feats.eye_cnn_reason == "always" and 0.0 <= feats.p_closed <= 1.0
        p_closed[eyes_open] = feats.p_closed
    assert estimator.runs == 10
    assert p_closed[True] < 0.05 < p_closed[False]  # measured 0.00 against 0.09-0.18 (a drawn line, not an eyelid)


# ---------------------------------------------------------------- block 4 on yolov8n.onnx


def test_real_yolo_runs_and_sees_no_phone_where_none_is(need_model):
    need_model(PHONE.resolved_model_path())
    model = YoloPhoneModel(PHONE)
    assert model(np.full((720, 1280, 3), 128, np.uint8)) == ()
    assert model(drawn_face()) == ()
    assert model(np.full((240, 320, 3), 128, np.uint8)) == ()  # another frame size goes through the letterbox


def test_real_yolo_on_its_own_thread_answers_for_the_frame_it_was_given(need_model):
    need_model(PHONE.resolved_model_path())
    frame = preprocessed([drawn_face()])[0]
    done = threading.Event()
    model = YoloPhoneModel(PHONE)

    def watched(image):
        try:
            return model(image)
        finally:
            done.set()

    with AsyncPhoneDetector(dataclasses.replace(PHONE, max_result_age_s=60.0), model=watched) as detector:
        detector.submit(frame)
        assert done.wait(60.0)
        for _ in range(1000):  # the result is stored right after the model returns
            if detector.runs:
                break
            done.wait(0.01)
        latest = detector.latest(now=frame.timestamp)
    assert latest is not None and latest.frame_id == frame.frame_id and latest.detections == ()


# ---------------------------------------------------------------- tools/benchmark.py --check


def test_check_fails_on_low_fps_and_on_fps_that_was_not_measured():
    cfg = EvalConfig.from_dict(TH["eval"])

    def failed(smp):
        return bm.check_failures(bm.soak_verdict(result(smp), cfg.soak_min_fps, cfg.soak_rss_growth_mb_per_h))

    assert failed(samples(90)) == []  # memory and temperature are not judged in 90 s: not a failure
    slow = failed(samples(90, fps=cfg.soak_min_fps - 1))
    assert len(slow) == 1 and slow[0].startswith("FPS at least 15") and "14.0 FPS" in slow[0]
    assert len(failed(samples(20))) == 1  # under 30 s nothing was measured: the gate must not pass
    leak = failed(samples(600, rss=lambda t: 500.0 + 0.1 * t))
    assert len(leak) == 1 and leak[0].startswith("memory")


@pytest.mark.parametrize(("fps", "code"), [(30.0, 0), (9.0, 1)])
def test_check_sets_the_exit_code_of_a_long_run(monkeypatch, capsys, fps, code):
    monkeypatch.setattr(bm, "soak", lambda args, th: result(samples(90, fps=fps)))
    argv = ["--duration", "90s", "--condition", "drawn_face"]
    assert bm.main([*argv, "--check"]) == code
    assert ("FAILED FPS" in capsys.readouterr().err) is bool(code)
    assert bm.main(argv) == 0  # without --check a slow run is only reported


# ---------------------------------------------------------------- the workflow


def test_ci_runs_on_the_working_branch_with_real_models_and_an_fps_gate():
    workflow = yaml.safe_load((PROJECT_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    triggers = workflow[True]  # YAML 1.1 reads the key `on` as a boolean
    assert {"main", "DAQuan"} <= set(triggers["push"]["branches"])
    job = workflow["jobs"]["models"]
    commands = "\n".join(step.get("run", "") for step in job["steps"])
    assert job["env"]["DG_REQUIRE_MODELS"] == "1"  # a model that failed to download is a red job, not a skip
    assert "tools/download_models.py" in commands and "test_m87_ci_real_models.py" in commands
    assert "tools/benchmark.py" in commands and "--check" in commands and "drawn_face" in commands
