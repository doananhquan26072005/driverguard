"""M86: eval hygiene. Video time from the container's timestamps, pinned libraries and model checksums,
reading numpy 2 traces with numpy 1, the personalisation report scored with eval.*. Fake numbers only:
no video, no model, no network."""

import gzip
import importlib
import json
import pickle
import re

import numpy as np
import pytest

from edge_agent.config import PROJECT_ROOT, load_thresholds
from tools import download_models as dm
from tools import metrics as M  # noqa: N812
from tools import seq_eval as se
from tools import uta_rldd as U  # noqa: N812

# ---------------------------------------------------------------- frame times of a video file


def clock_times(fps, stamps_ms):
    clock = se.VideoClock(fps)
    return clock, [clock.time(ms) for ms in stamps_ms]


def test_a_constant_rate_video_gets_the_times_of_frame_index_over_fps():
    clock, t = clock_times(25.0, [i * 40.0 for i in range(100)])
    assert t == pytest.approx([i / 25.0 for i in range(100)])
    s = clock.summary()
    assert s["source"] == "container" and s["patched_frames"] == 0
    assert s["duration_s"] == pytest.approx(4.0) and s["drift_s"] == pytest.approx(0.0)


def test_the_first_timestamp_is_the_origin_whatever_the_container_starts_at():
    _, t = clock_times(30.0, [-1.667, 31.667, 65.0])  # a .mov of UTA-RLDD starts just below zero
    assert t == pytest.approx([0.0, 0.033334, 0.066667], abs=1e-6)


def test_a_stretch_without_frames_keeps_its_real_length():
    # 2 s recorded, 3 s with no frame, 2 s recorded: 100 frames over 7 s, which a container calls 14.3 FPS
    stamps = [i * 40.0 for i in range(50)] + [5000.0 + i * 40.0 for i in range(50)]
    fps = 100 / 7.0
    clock, t = clock_times(fps, stamps)
    assert t[49] == pytest.approx(1.96) and t[50] == pytest.approx(5.0)  # by index: 3.43 s and 3.50 s
    s = clock.summary()
    assert s["patched_frames"] == 0 and s["offset_max_s"] == pytest.approx(1.5, abs=0.05)
    assert abs(s["drift_s"]) < 0.1  # the two clocks agree at the end: the total hides the gap


def test_timestamps_that_are_missing_or_go_back_are_replaced_by_one_nominal_frame():
    clock, t = clock_times(10.0, [0.0, 100.0, 100.0, 50.0, 400.0, float("nan"), None])
    assert t == pytest.approx([0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
    assert clock.patched == 4 and clock.summary()["source"] == "container"


def test_a_container_without_timestamps_falls_back_to_frame_index_over_fps_and_says_so():
    clock, t = clock_times(20.0, [0.0] * 50)  # an OpenCV backend that reports nothing
    assert t == pytest.approx([i / 20.0 for i in range(50)])
    assert clock.summary()["source"] == "index" and clock.duration_s == pytest.approx(2.5)
    clock, t = clock_times(20.0, [None] * 3)
    assert t == pytest.approx([0.0, 0.05, 0.1]) and clock.summary()["source"] == "index"


def test_gap_stats_show_the_offset_inside_the_video_and_count_long_gaps():
    times = np.concatenate([np.arange(50) * 0.04, 5.0 + np.arange(50) * 0.04])
    g = se.gap_stats(times, 100 / 7.0, long_gap=2.0)
    assert g["frames"] == 100 and g["long_gaps"] == 1 and g["gap_max_ms"] == pytest.approx(3040.0)
    assert g["offset_max_s"] == pytest.approx(1.5, abs=0.05) and abs(g["drift_s"]) < 0.1
    even = se.gap_stats(np.arange(100) / 25.0, 25.0, long_gap=2.0)
    assert even["long_gaps"] == 0 and even["offset_max_s"] == 0.0 and even["drift_s"] == 0.0
    assert se.gap_stats(np.array([0.0]), 25.0, 2.0)["long_gaps"] == 0  # one frame: nothing to measure


def old_trace(n=50, fps=25.0):
    return {"fps": fps, "n": n, "cols": {"t": np.arange(n) / fps}}


def test_a_trace_made_before_the_clock_keeps_exactly_the_times_it_was_scored_on():
    tr = old_trace()
    assert se.trace_seconds(tr) == 50 / 25.0
    assert [se.frame_seconds(tr, f) for f in (0, 7, 49, 50)] == [0 / 25.0, 7 / 25.0, 49 / 25.0, 50 / 25.0]
    assert se.trace_seconds({"fps": 25.0, "n": 0, "cols": {"t": np.zeros(0)}}) == 0.0


def test_a_clocked_trace_is_as_long_as_its_clock_says_and_frames_sit_at_their_own_time():
    t = np.concatenate([np.arange(50) * 0.04, 5.0 + np.arange(50) * 0.04])
    tr = {"fps": 100 / 7.0, "n": 100, "cols": {"t": t}, "duration_s": 7.03, "events": [], "alerts": []}
    assert se.trace_seconds(tr) == 7.03  # not 100 / 14.29
    assert se.frame_seconds(tr, 50) == 5.0
    assert se.frame_seconds(tr, 100) == 7.03  # one past the last frame: the end of the trace
    assert se.trace_seconds(se.resample_trace(tr, 5.0)) == 7.03  # frames left out: the video is as long


def awake_trace(n=2400, fps=20.0):
    """Eyes open, facing the camera, 120 s."""
    cols = {c: np.full(n, np.nan) for c in se.COLUMNS}
    cols |= {"t": np.arange(n) / fps, "face": np.ones(n), "reliable": np.ones(n), "is_ir": np.zeros(n)}
    cols |= {k: np.full(n, v) for k, v in (("ear", 0.3), ("ear_l", 0.3), ("ear_r", 0.3), ("mar", 0.1))}
    cols |= {k: np.zeros(n) for k in ("pitch", "yaw")} | {"face_bright": np.full(n, 120.0)}
    return {"fps": fps, "n": n, "cols": cols, "events": [], "alerts": []}


def test_the_uta_summary_counts_the_hours_of_the_clock():
    th = load_thresholds()
    tr = awake_trace()
    by_index = U.summarize(U.replay_plus(tr, th), th)
    clocked = U.summarize(U.replay_plus({**tr, "duration_s": 150.0}, th), th)
    assert by_index["dur_s"] == 120.0 and by_index["score_s"] == 90.0
    assert clocked["dur_s"] == 150.0 and clocked["score_s"] == 120.0


def test_the_clock_report_lists_the_video_with_the_largest_offset_first():
    th = load_thresholds()
    even = se.gap_stats(np.arange(1000) / 25.0, 25.0, 2.0) | {"patched": 0}
    gap = se.gap_stats(np.concatenate([np.arange(500) / 25.0, 60.0 + np.arange(500) / 25.0]), 12.5, 2.0)
    rows = [
        {"key": "F1_S01_0", **even, "error": ""},
        {"key": "F4_S44_0", **gap, "patched": 2, "error": ""},
        {"key": "F9_S99_0", "frames": 0, "error": "RuntimeError: cannot open"},
    ]
    text = U.clock_report(rows, th, "title", "note")
    table = [line for line in text.splitlines() if line.startswith("| F")]
    assert [line.split("|")[1].strip() for line in table] == ["F4_S44_0", "F1_S01_0"]
    assert "Videos read: 2 of 3" in text and "videos where it reaches 1 s: 1" in text
    assert "Videos below 15 FPS (`eval.min_video_fps`): 1" in text
    assert "Not read: F9_S99_0 (RuntimeError: cannot open)" in text
    assert "No video could be read." in U.clock_report([rows[2]], th, "title")


# ---------------------------------------------------------------- numpy 2 traces read with numpy 1


def test_the_numpy2_modules_a_kaggle_trace_names_resolve_whatever_was_imported_before():
    importlib.import_module("numpy._core")  # what edge_agent pulls in, and what used to switch the shim off
    U.numpy2_pickle_shim()
    for name in U.NUMPY2_PICKLE_MODULES:
        assert importlib.import_module(f"numpy._core.{name}") is not None
    # the global a numpy 2 pickle of an array starts with (protocol 0 text form: module, then name)
    assert callable(pickle.loads(b"cnumpy._core.numeric\n_frombuffer\n."))
    assert callable(pickle.loads(b"cnumpy._core.multiarray\n_reconstruct\n."))


def test_load_trace_reads_back_what_save_trace_wrote(tmp_path):
    tr = {"fps": 25.0, "n": 3, "cols": {"t": np.arange(3) / 25.0}, "events": [], "alerts": []}
    path = tmp_path / "F1_S01_0.pkl.gz"
    U.save_trace(path, tr)
    back = U.load_trace(path)
    assert back["n"] == 3 and back["cols"]["t"].tolist() == tr["cols"]["t"].tolist()
    with gzip.open(path, "rb") as f:  # a trace is numbers: nothing image-sized in the file
        assert len(f.read()) < 2000


# ---------------------------------------------------------------- pinned libraries and models


def test_the_libraries_that_decide_the_numbers_are_pinned_exactly():
    lines = (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    specs = [line.split(";")[0].strip() for line in lines if line and not line.startswith("#")]
    for package in ("opencv-python", "numpy", "mediapipe", "onnxruntime"):
        mine = [s for s in specs if re.split(r"[=<>!~]", s)[0] == package]
        assert mine and all(re.fullmatch(rf"{package}==[\d.]+", s) for s in mine), (package, mine)


def test_every_model_has_a_fixed_url_and_a_full_sha256():
    for name, (url, sha) in dm.MODELS.items():
        assert "latest" not in url and url.startswith("https://"), name
        assert re.fullmatch(r"[0-9a-f]{64}", sha), name
    assert all(re.fullmatch(r"[0-9a-f]{64}", sha) for sha in dm.EXPORTED.values())


def test_verify_refuses_a_downloaded_model_that_differs_and_only_reports_another_export(tmp_path, capsys):
    assert dm.verify(tmp_path) == 0  # nothing there: reported, not an error
    assert capsys.readouterr().out.count("[absent]") == len(dm.MODELS) + len(dm.EXPORTED)
    (tmp_path / "yolov8n.onnx").write_bytes(b"another export")
    assert dm.verify(tmp_path) == 0 and "[warning] yolov8n.onnx" in capsys.readouterr().out
    assert dm.verify(tmp_path, strict=True) == 1
    (tmp_path / "face_landmarker.task").write_bytes(b"not the pinned file")
    assert dm.verify(tmp_path) == 1 and "[error] face_landmarker.task" in capsys.readouterr().out


def test_the_models_on_this_machine_are_the_pinned_ones():
    if not (dm.MODELS_DIR / "face_landmarker.task").exists():
        pytest.skip("models/ is not downloaded here (CI)")
    assert dm.verify() == 0


def test_the_kaggle_run_records_in_the_repo_name_the_pinned_models_and_libraries():
    runs = sorted(U.RUN_DIR.glob("session*_run_info.json"))
    assert len(runs) == 2
    for p in runs:
        info = json.loads(p.read_text(encoding="utf-8"))
        assert info["versions"] == {"mediapipe": "1.0.1", "opencv": "4.14.0", "numpy": "2.1.3", "onnxruntime": "1.30.0"}
        for name, sha in info["models_sha256"].items():
            assert dm.MODELS[name][1] == sha
    text = U.traced_with()
    assert "mediapipe 1.0.1" in text and "numpy 2.1.3" in text and "[2 tracing sessions]" in text
    assert "no run record" in U.traced_with(U.RUN_DIR / "nowhere")


def test_a_trace_records_what_made_it(tmp_path):
    (tmp_path / "face_landmarker.task").write_bytes(b"model")
    (tmp_path / "notes.txt").write_text("not a model")
    env = M.environment(tmp_path)
    assert set(env) == {"commit", "tree", "thresholds_sha256", "python", "versions", "models_sha256"}
    assert set(env["versions"]) == set(M.MODEL_LIBRARIES) and env["versions"]["numpy"] == np.__version__
    assert (
        list(env["models_sha256"]) == ["face_landmarker.task"]
        and len(env["models_sha256"]["face_landmarker.task"]) == 64
    )
    json.dumps(env)  # plain values: it goes into a pickled trace and into reports
    text = M.environment_text([env, env, None])
    assert f"numpy {np.__version__}" in text and "[2 traces]" in text and "1 traces without a record" in text
    assert M.environment_text([None, None]) == "Traced with: not recorded (2 traces made before M86)."


# ---------------------------------------------------------------- the personalisation report and eval.*


def test_the_personal_report_scores_with_the_eval_settings_it_is_given(monkeypatch):
    seen = []
    real = U.metrics

    def spy(rows, cfg=None):
        seen.append(cfg)
        return real(rows, cfg)

    monkeypatch.setattr(U, "metrics", spy)
    th = load_thresholds()
    cfg = M.EvalConfig.from_dict({**th["eval"], "bootstrap_resamples": 50})
    summary = U.summarize(U.replay_plus(awake_trace(), th), th)
    rows = [{"key": f"F1_S01_{lb}", "fold": 1, "subject": "F1_S01", "label": lb, **summary} for lb in U.LABELS]
    text = U.personal_report({name: rows for name, _ in U.PERSONAL_SETTINGS}, {"all": None}, "title", cfg)
    assert "| all (1) | fixed |" in text
    assert len(seen) == len(U.PERSONAL_SETTINGS) and all(c is cfg for c in seen)
