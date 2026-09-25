"""Block 5 (eye-state CNN) and how block 7 uses it. Fake classifier except the one real-model test."""

import cv2
import numpy as np
import pytest

from edge_agent.analysis.drowsiness import DrowsinessAnalyzer
from edge_agent.perception.eye_state import (
    LEFT_EYE_CORNERS,
    RIGHT_EYE_CORNERS,
    EyeStateConfig,
    EyeStateEstimator,
    OnnxEyeClassifier,
    eye_crop,
    make_estimator,
    trigger_reason,
)
from edge_agent.perception.features import FrameFeatures
from edge_agent.perception.landmarks import FaceLandmarks
from edge_agent.perception.preprocess import PreprocessedFrame

CFG = EyeStateConfig()


def frame(brightness=120.0, is_ir=False, image=None, t=0.0):
    img = image if image is not None else np.full((360, 640, 3), 120, np.uint8)
    return PreprocessedFrame(img, img[..., 0], brightness, is_ir, 1.0, 0, t)


def feats(ear_l=0.3, ear_r=0.3, t=0.0):
    return FrameFeatures(0, t, True, 1.0, ear=(ear_l + ear_r) / 2, ear_left=ear_l, ear_right=ear_r, mar=0.05,
                         pitch=0.0, yaw=0.0, roll=0.0)  # fmt: skip


def landmarks():
    pts = np.zeros((478, 3), np.float32)
    for (a, b), cx in ((LEFT_EYE_CORNERS, 400), (RIGHT_EYE_CORNERS, 240)):
        pts[a, :2], pts[b, :2] = (cx + 20, 150), (cx - 20, 150)
    return FaceLandmarks(pts, 640, 360, 1.0, 1, 0, 0.0)


class FakeClassifier:
    def __init__(self, p=0.9):
        self.p, self.calls = p, 0

    def __call__(self, crops):
        assert crops.shape == (2, 32, 32, 3) and crops.dtype == np.uint8
        self.calls += 1
        return np.full(len(crops), self.p)


# ---------------------------------------------------------------- crop


def test_eye_crop_levels_and_centres_the_eye():
    img = np.zeros((200, 200, 3), np.uint8)
    p1, p2 = np.array([70.0, 120.0]), np.array([130.0, 85.36])  # eye line tilted by -30 deg
    cv2.line(img, (70, 120), (130, 85), (255, 255, 255), 3)
    crop = eye_crop(img, p1, p2, scale=1.8, size=32)
    assert crop.shape == (32, 32, 3)
    rows = crop[..., 0].astype(float).sum(axis=1)
    assert abs(int(np.argmax(rows)) - 16) <= 1  # the (now horizontal) line crosses the middle row
    assert rows[16] > 5 * rows[4]  # and nothing much above it: it really is horizontal


def test_eye_crop_corner_order_does_not_flip():
    img = np.zeros((100, 100, 3), np.uint8)
    img[40:60, 30:50] = 255  # bright left half of the eye
    a = eye_crop(img, np.array([30.0, 50.0]), np.array([70.0, 50.0]), 1.8, 32)
    b = eye_crop(img, np.array([70.0, 50.0]), np.array([30.0, 50.0]), 1.8, 32)
    assert np.array_equal(a, b)


# ---------------------------------------------------------------- when the CNN is called


@pytest.mark.parametrize(
    ("pre", "f", "expected"),
    [
        (frame(), feats(), None),  # daylight, both eyes agree: EAR is trusted
        (frame(is_ir=True), feats(), "ir"),
        (frame(brightness=40), feats(), "low_light"),
        (frame(), feats(0.30, 0.12), "ear_asymmetry"),  # glare / occlusion on one eye
        (frame(), feats(0.30, 0.26), None),
    ],
)
def test_trigger_reason(pre, f, expected):
    assert trigger_reason(pre, f, CFG) == expected


def test_always_run():
    assert trigger_reason(frame(), feats(), EyeStateConfig(always_run=True)) == "always"


def test_estimator_adds_p_closed_only_when_needed():
    fake = FakeClassifier(p=0.8)
    est = EyeStateEstimator(CFG, classifier=fake)
    same = est(frame(), landmarks(), feats())
    assert same.p_closed is None and fake.calls == 0
    out = est(frame(is_ir=True), landmarks(), feats())
    assert out.p_closed == pytest.approx(0.8) and out.eye_cnn_reason == "ir" and est.runs == 1
    assert est(frame(is_ir=True), None, feats()).p_closed is None  # no face: nothing to crop


def test_missing_model_falls_back_to_ear(tmp_path):
    assert make_estimator(EyeStateConfig(model_path=str(tmp_path / "none.onnx"))) is None
    assert make_estimator(EyeStateConfig(enabled=False)) is None


def test_real_model_class_order():
    """open_closed_eye.onnx: index 0 = closed (Intel's demo: out[0] < out[1] means open)."""
    if not CFG.resolved_model_path().exists():
        pytest.skip("models/open_closed_eye.onnx not downloaded")
    clf = OnnxEyeClassifier(CFG)
    skin = np.full((64, 64, 3), (150, 170, 200), np.uint8)
    opened = skin.copy()
    cv2.ellipse(opened, (32, 32), (26, 14), 0, 0, 360, (235, 235, 235), -1)
    cv2.circle(opened, (32, 32), 11, (60, 50, 40), -1)
    cv2.circle(opened, (32, 32), 5, (10, 10, 10), -1)
    closed = skin.copy()
    cv2.line(closed, (6, 34), (58, 34), (40, 40, 50), 2)
    p = clf(np.stack([cv2.resize(opened, (32, 32)), cv2.resize(closed, (32, 32))]))
    assert p[0] < 0.5 < p[1]


# ---------------------------------------------------------------- block 7 with the CNN


def run(analyzer, seconds, ear, p_closed=None, t0=0.0, fps=30):
    states = []
    for i in range(round(seconds * fps)):
        t = t0 + i / fps
        f = FrameFeatures(i, t, True, 1.0, ear=ear, ear_left=ear, ear_right=ear, mar=0.05, pitch=0.0, yaw=0.0,
                          roll=0.0, p_closed=p_closed, eye_cnn_reason=None if p_closed is None else "ir")  # fmt: skip
        states.append(analyzer.update(f))
    return states


def test_cnn_decides_when_ear_is_wrong():
    # Night: EAR looks open (0.30) but the CNN sees closed eyes -> microsleep is still caught.
    a = DrowsinessAnalyzer()
    run(a, 15, 0.30)
    s = run(a, 1.6, 0.30, p_closed=0.95, t0=15)
    assert s[-1].eye_closed is True and s[-1].eye_source == "cnn"
    assert any("microsleep" in x.events for x in s)


def test_cnn_open_overrides_a_low_ear():
    # Glare: EAR collapses (0.08) but the CNN sees an open eye -> no false closure.
    a = DrowsinessAnalyzer()
    run(a, 15, 0.30)
    s = run(a, 3, 0.08, p_closed=0.05, t0=15)
    assert all(x.eye_closed is False for x in s) and s[-1].closed_duration == 0.0


def test_cnn_hysteresis():
    a = DrowsinessAnalyzer()
    run(a, 15, 0.30)
    assert run(a, 0.2, 0.3, p_closed=0.5, t0=15)[-1].eye_closed is False  # between 0.4 and 0.6: stay open
    assert run(a, 0.2, 0.3, p_closed=0.7, t0=15.2)[-1].eye_closed is True
    assert run(a, 0.2, 0.3, p_closed=0.5, t0=15.4)[-1].eye_closed is True  # stays closed until <= 0.4
    assert run(a, 0.2, 0.3, p_closed=0.3, t0=15.6)[-1].eye_closed is False


def test_unreliable_ear_does_not_shift_the_baseline():
    a = DrowsinessAnalyzer()
    run(a, 15, 0.30)
    base = run(a, 0.1, 0.30, t0=15)[-1].ear_open_baseline
    s = run(a, 30, 0.12, p_closed=0.9, t0=15.1)  # long closure seen by the CNN, EAR garbage
    assert s[-1].ear_open_baseline == pytest.approx(base)


def test_ear_path_unchanged_without_cnn():
    s = run(DrowsinessAnalyzer(), 5, 0.30)
    assert s[-1].eye_source == "ear" and s[-1].eye_closed is False


# ---------------------------------------------------------------- no EAR <-> CNN flicker


def dusk(i):
    return 59.0 if i % 2 == 0 else 61.0  # brightness wobbling around low_light_brightness (60)


def test_cnn_is_held_so_the_eye_source_does_not_flicker():
    est = EyeStateEstimator(CFG, classifier=FakeClassifier(p=0.1))
    used = [est(frame(dusk(i), t=i / 30), landmarks(), feats(t=i / 30)).p_closed is not None for i in range(60)]
    assert all(used)  # CNN on every frame once triggered, not every other frame
    t = 2.0 + CFG.hold_s + 0.1  # bright again for longer than hold_s: back to EAR
    assert est(frame(120.0, t=t), landmarks(), feats(t=t)).p_closed is None


def test_dusk_flicker_does_not_fake_perclos():
    # In the dark EAR collapses (0.10) although the CNN sees open eyes. Switching source every
    # frame counted the EAR frames as closed: PERCLOS ~ 1/3 over the window, drowsy L1.
    est = EyeStateEstimator(CFG, classifier=FakeClassifier(p=0.1))
    a = DrowsinessAnalyzer()
    run(a, 15, 0.30)
    for i in range(40 * 30):
        t = 15 + i / 30
        s = a.update(est(frame(dusk(i), t=t), landmarks(), feats(0.10, 0.10, t=t)))
    assert s.perclos_60s < 0.05
