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
    model = FakeModel()
    cfg = PhoneDetectorConfig(target_fps=10.0, max_result_age_s=10.0)
    with AsyncPhoneDetector(cfg, model=model) as detector:
        t_end = time.monotonic() + 1.0
        i = 0
        while time.monotonic() < t_end:  # main loop at ~100 FPS
            detector.submit(make_frame(i, time.monotonic()))
            i += 1
            time.sleep(0.01)
        result = detector.latest()
    assert 6 <= model.calls <= 12  # ~10 runs in 1 s, not one per frame
    assert result is not None and result.detections
    assert result.frame_id >= i - 15  # ran on a recent frame, not a queued old one


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
    with AsyncPhoneDetector(PhoneDetectorConfig(target_fps=100.0), model=FakeModel(delay=0.3)) as detector:
        t0 = time.perf_counter()
        for i in range(50):
            detector.submit(make_frame(i, 0.0))
        assert time.perf_counter() - t0 < 0.1
