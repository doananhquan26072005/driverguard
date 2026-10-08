import threading
import time

import numpy as np
import pytest

from edge_agent.perception.phone_detector import (
    AsyncPhoneDetector,
    FaceBoxMemory,
    PhoneDetection,
    PhoneDetectorConfig,
    decode_yolov8,
    driver_zone,
    letterbox,
    phone_near_face,
)
from edge_agent.perception.preprocess import PreprocessedFrame

CFG = PhoneDetectorConfig()
FACE = (300.0, 100.0, 400.0, 220.0)  # x1, y1, x2, y2: 100 x 120 face


def yolo_output(boxes, num_classes=80):
    """boxes: list of (cx, cy, w, h, class_id, score) in letterboxed input pixels."""
    out = np.zeros((1, 4 + num_classes, max(len(boxes), 1)), dtype=np.float32)
    for i, (cx, cy, w, h, cls, score) in enumerate(boxes):
        out[0, :4, i] = (cx, cy, w, h)
        out[0, 4 + cls, i] = score
    return out


def test_letterbox_keeps_aspect_and_pads():
    img = np.zeros((360, 640, 3), dtype=np.uint8)
    boxed, scale, pad = letterbox(img, 640)
    assert boxed.shape == (640, 640, 3)
    assert scale == 1.0 and pad == (0, 140)


def test_decode_keeps_phone_class_and_applies_nms():
    out = yolo_output(
        [
            (320, 300, 40, 80, 67, 0.9),  # phone
            (322, 302, 40, 80, 67, 0.8),  # duplicate of the same phone -> NMS
            (100, 300, 50, 50, 0, 0.95),  # person, other class
            (500, 300, 40, 80, 67, 0.2),  # phone below conf threshold
        ]
    )
    dets = decode_yolov8(out, 67, 0.35, 0.45, scale=1.0, pad=(0, 140), image_size=(640, 360))
    assert len(dets) == 1
    assert dets[0].score == pytest.approx(0.9)
    assert dets[0].bbox == pytest.approx((300, 120, 340, 200))  # pad removed


def test_decode_scales_back_to_original_image():
    out = yolo_output([(320, 320, 64, 64, 67, 0.9)])
    dets = decode_yolov8(out, 67, 0.35, 0.45, scale=0.5, pad=(0, 0), image_size=(1280, 1280))
    assert dets[0].bbox == pytest.approx((576, 576, 704, 704))


def test_decode_empty():
    assert decode_yolov8(yolo_output([]), 67, 0.35, 0.45, 1.0, (0, 0), (640, 640)) == ()


def det(cx, cy, size=30):
    return PhoneDetection((cx - size / 2, cy - size / 2, cx + size / 2, cy + size / 2), 0.9)


def test_driver_zone():
    assert driver_zone(FACE, CFG) == pytest.approx((200, 40, 500, 400))


@pytest.mark.parametrize(
    ("dets", "expected"),
    [
        ((det(410, 160),), True),  # at the ear: call
        ((det(350, 330),), True),  # in front of the chest: texting
        ((det(600, 160),), False),  # passenger side, outside zone
        ((det(350, 470),), False),  # lap, far below
        ((), False),
    ],
)
def test_phone_near_face(dets, expected):
    assert phone_near_face(dets, FACE, CFG) is expected


def test_no_face_means_no_phone_near_face():
    assert phone_near_face((det(350, 160),), None, CFG) is False


def test_face_memory_keeps_zone_when_phone_hides_face():
    mem = FaceBoxMemory(3.0)
    assert mem.update(None, 0.0) is None  # no face seen yet
    assert mem.update(FACE, 1.0) == FACE
    # Phone in front of the face: MediaPipe loses it, the zone is still known.
    face = mem.update(None, 3.5)
    assert face == FACE and phone_near_face((det(350, 160),), face, CFG) is True
    assert mem.update(None, 4.1) is None  # too old


def make_frame(i, t):
    img = np.zeros((8, 8, 3), dtype=np.uint8)
    return PreprocessedFrame(img, img[..., 0], 0.0, False, 1.0, i, t)


class FakeModel:
    def __init__(self, delay=0.0):
        self.delay = delay
        self.calls = 0

    def __call__(self, image):
        self.calls += 1
        time.sleep(self.delay)
        return (det(10, 10),)


def test_async_detector_runs_at_target_fps_on_latest_frame():
    # The real thread, as a smoke test: it runs, and not once per frame. The schedule itself (when it
    # runs, on which frame) is asserted exactly on a fake clock in test_m88_missing_tests.py; a lower
    # bound on the runs of a real second ("6 to 12") only measured how busy the machine was.
    model = FakeModel()
    cfg = PhoneDetectorConfig(target_fps=10.0, max_result_age_s=10.0)
    with AsyncPhoneDetector(cfg, model=model) as detector:
        t0 = time.monotonic()
        i = 0
        while time.monotonic() < t0 + 0.5 or detector.runs < 2:  # main loop at ~100 FPS
            detector.submit(make_frame(i, time.monotonic()))
            i += 1
            time.sleep(0.01)
            assert time.monotonic() < t0 + 10.0, "the detector thread never ran"
        elapsed = time.monotonic() - t0
        result = detector.latest()
    assert model.calls <= elapsed * cfg.target_fps + 2  # one run per period at most, not one per frame
    assert result is not None and result.detections


def test_async_detector_result_goes_stale():
    cfg = PhoneDetectorConfig(target_fps=50.0, max_result_age_s=0.5)
    with AsyncPhoneDetector(cfg, model=FakeModel()) as detector:
        assert detector.latest() is None
        detector.submit(make_frame(0, 100.0))
        for _ in range(100):
            if detector.runs:
                break
            time.sleep(0.01)
        assert detector.latest(now=100.2) is not None
        assert detector.latest(now=100.7) is None


def test_slow_model_does_not_block_submit():
    """No stopwatch: the model is held inside one run, and every submit has to return meanwhile."""
    entered, release, finished = threading.Event(), threading.Event(), []

    def held(image):
        entered.set()
        release.wait(10.0)  # a submit that waited for the model would sit here until this gives up
        finished.append(1)
        return (det(10, 10),)

    with AsyncPhoneDetector(PhoneDetectorConfig(target_fps=100.0), model=held) as detector:
        try:
            detector.submit(make_frame(0, 0.0))
            assert entered.wait(5.0)
            for i in range(1, 50):
                detector.submit(make_frame(i, 0.0))
            assert not finished
        finally:
            release.set()


def test_too_slow_model_is_counted_and_warned_once(capsys):
    # Inference (0.1 s) longer than max_result_age_s (0.05 s): every result is unknown.
    cfg = PhoneDetectorConfig(target_fps=100.0, max_result_age_s=0.05)
    with AsyncPhoneDetector(cfg, model=FakeModel(delay=0.1)) as detector:
        for i in range(40):
            detector.submit(make_frame(i, time.monotonic()))
            if detector.runs >= 2:
                break
            time.sleep(0.02)
        assert detector.runs >= 2 and detector.stale_results == detector.runs
        assert detector.latest() is None
    assert capsys.readouterr().out.count("WARNING") == 1


def test_fast_model_is_not_stale(capsys):
    cfg = PhoneDetectorConfig(target_fps=100.0, max_result_age_s=0.5)
    with AsyncPhoneDetector(cfg, model=FakeModel()) as detector:
        for i in range(50):
            detector.submit(make_frame(i, time.monotonic()))
            if detector.runs >= 3:
                break
            time.sleep(0.01)
        assert detector.runs >= 3 and detector.stale_results == 0
    assert "WARNING" not in capsys.readouterr().out


def test_yolo_session_does_not_spin(monkeypatch):
    from edge_agent.perception.onnx import load_ort

    ort = load_ort()

    from edge_agent.perception.phone_detector import YoloPhoneModel

    seen = {}

    class FakeSession:
        def __init__(self, path, opts, providers):
            seen["spin"] = opts.get_session_config_entry("session.intra_op.allow_spinning")

        def get_inputs(self):
            return [type("I", (), {"name": "images"})()]

    monkeypatch.setattr(ort, "InferenceSession", FakeSession)
    monkeypatch.setattr(PhoneDetectorConfig, "resolved_model_path", lambda self: __import__("pathlib").Path(__file__))
    YoloPhoneModel(PhoneDetectorConfig())
    assert seen["spin"] == "0"


# --------------------------------------------------------------------------- a run that raises (A1 M1)


class FlakyModel:
    """Raises on the calls numbered in `bad` (1-based), answers on the others."""

    def __init__(self, bad):
        self.bad = bad
        self.calls = 0

    def __call__(self, image):
        self.calls += 1
        if self.calls in self.bad:
            raise RuntimeError(f"boom {self.calls}")
        return (det(10, 10),)


def feed_until(detector, done, seconds=3.0):
    """Offer frames like the main loop until done() or the deadline; True when done() came."""
    deadline = time.monotonic() + seconds
    i = 0
    while time.monotonic() < deadline:
        if done():
            return True
        detector.submit(make_frame(i, time.monotonic()))
        i += 1
        time.sleep(0.005)
    return done()


def test_thread_survives_a_run_that_raises(capsys):
    model = FlakyModel(bad={2})
    cfg = PhoneDetectorConfig(target_fps=200.0, max_result_age_s=10.0)
    with AsyncPhoneDetector(cfg, model=model) as detector:
        assert feed_until(detector, lambda: detector.runs >= 3)
        assert detector._thread.is_alive()
        assert detector.errors == 1 and model.calls >= 4
        assert detector.latest() is not None
    out = capsys.readouterr().out
    assert out.count("run failed") == 1 and "RuntimeError: boom 2" in out


def test_failing_streak_is_warned_once_and_counted(capsys):
    model = FlakyModel(bad={2, 3, 4, 6})  # two streaks: 2-4 and 6
    cfg = PhoneDetectorConfig(target_fps=200.0, max_result_age_s=10.0)
    with AsyncPhoneDetector(cfg, model=model) as detector:
        assert feed_until(detector, lambda: detector.runs >= 4)
        assert detector.errors == 4
    assert capsys.readouterr().out.count("run failed") == 2


def test_result_ages_out_while_every_run_raises(capsys):
    # The answer of the last good run is not kept alive by failing ones: it goes "unknown" after
    # max_result_age_s, which is what PhoneHealth counts.
    model = FlakyModel(bad=set(range(2, 10_000)))
    cfg = PhoneDetectorConfig(target_fps=200.0, max_result_age_s=0.5)
    with AsyncPhoneDetector(cfg, model=model) as detector:
        detector.submit(make_frame(0, 100.0))
        for _ in range(300):  # the one good run takes this frame before any other is offered
            if detector.runs:
                break
            time.sleep(0.01)
        assert feed_until(detector, lambda: detector.errors >= 5)
        assert detector._thread.is_alive() and detector.runs == 1
        assert detector.latest(now=100.2) is not None and detector.latest(now=100.7) is None
    assert capsys.readouterr().out.count("run failed") == 1


def test_model_that_never_works_keeps_the_thread_and_gives_no_result():
    def broken(image):
        raise ValueError("no session")

    with AsyncPhoneDetector(PhoneDetectorConfig(target_fps=200.0), model=broken) as detector:
        assert feed_until(detector, lambda: detector.errors >= 3)
        assert detector._thread.is_alive() and detector.runs == 0 and detector.latest() is None
