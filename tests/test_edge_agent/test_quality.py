"""Block 6 quality stage and its "monitoring unavailable" reasons (M43): fake number sequences, no image."""

import numpy as np

from edge_agent.config import load_thresholds
from edge_agent.context.can_sim import CanSimulator, scenario_from_dict
from edge_agent.decision.pipeline import DecisionPipeline
from edge_agent.perception.features import FrameFeatures
from edge_agent.perception.landmarks import FaceLandmarks
from edge_agent.perception.preprocess import PreprocessedFrame
from edge_agent.perception.quality import (
    QualityConfig,
    QualityMonitor,
    frame_issue,
    laplacian_variance,
    measure,
)
from edge_agent.runtime import TripRuntime
from tests.test_edge_agent.test_runtime import FakeSelector, Recorder

FPS = 15
CFG = QualityConfig()
OPEN, SHUT = 0.30, 0.08

STRIDE = 4  # preprocess.sample_stride


def face(t, ear=OPEN, **q):
    """A face looking at the road; q: face_brightness, sharpness, scene_brightness, scene_contrast."""
    return FrameFeatures(round(t * FPS), t, True, 1.0, ear=ear, mar=0.05, pitch=0.0, yaw=0.0, roll=0.0, **q)


def no_face(t, **q):
    return FrameFeatures(round(t * FPS), t, False, 0.0, face_reliable=False, **q)


# ------------------------------------------------------------------ one frame
def test_numbers_not_measured_are_never_an_issue():
    assert frame_issue(face(0.0), CFG) is None
    assert frame_issue(no_face(0.0), CFG) is None  # a lost face in an unknown image: block 8 times it


def test_each_issue_from_its_number():
    assert frame_issue(face(0, face_brightness=10), CFG) == "low_light"
    assert frame_issue(face(0, face_brightness=250), CFG) == "glare"
    assert frame_issue(face(0, face_brightness=120, sharpness=0.5), CFG) == "blur"
    assert frame_issue(face(0, face_brightness=120, sharpness=80), CFG) is None
    assert frame_issue(no_face(0, scene_brightness=3, scene_contrast=2), CFG) == "camera_blocked"
    assert frame_issue(no_face(0, scene_brightness=120, scene_contrast=1), CFG) == "camera_blocked"  # flat
    assert frame_issue(no_face(0, scene_brightness=90, scene_contrast=50), CFG) is None  # driver out of view
    half = FrameFeatures(0, 0.0, True, 0.6, face_reliable=False, ear=OPEN, pitch=0.0, yaw=0.0)
    assert frame_issue(half, CFG) == "bad_angle"


def test_a_dark_face_is_low_light_before_blur():
    # A dark image has little contrast, so its Laplacian is small too: say the cause, not the symptom.
    assert frame_issue(face(0, face_brightness=10, sharpness=0.1), CFG) == "low_light"


def test_limit_zero_switches_a_check_off():
    cfg = QualityConfig(dark_face_brightness=0, blur_sharpness=0)
    assert frame_issue(face(0, face_brightness=5, sharpness=0.1), cfg) is None
    assert frame_issue(face(0, face_brightness=5), QualityConfig(enabled=False)) is None


# ------------------------------------------------------------------ over time
def test_issue_lasts_until_usable_for_clear_s():
    m = QualityMonitor(CFG)
    s = None
    for i in range(3 * FPS):
        s = m.update(face(i / FPS, face_brightness=10))
    assert s.issue == "low_light" and 2.8 <= s.duration <= 3.0
    s = m.update(face(3.0 + 0.5, face_brightness=120))  # one usable frame: not over yet
    assert s.issue == "low_light"
    for i in range(2 * FPS):
        s = m.update(face(3.6 + i / FPS, face_brightness=120))
    assert s.issue is None and s.duration == 0.0


def test_score_is_the_usable_share_of_the_window():
    m = QualityMonitor(CFG)
    s = None
    for i in range(10 * FPS):
        t = i / FPS
        s = m.update(face(t, face_brightness=10 if t < 5 else 120))
    assert 0.45 <= s.score <= 0.55
    assert QualityMonitor(CFG).update(face(0.0)).score == 1.0


# ------------------------------------------------------------------ measured on the device (numpy only)
def _pre(luma):
    return PreprocessedFrame(
        image=np.empty((0, 0, 3), np.uint8),
        gray=luma,
        brightness=float(luma.mean()),
        is_ir=False,
        scale=1.0,
        frame_id=0,
        timestamp=0.0,
        luma=luma,
    )


def _lm(x1, y1, x2, y2, w, h):
    pts = np.zeros((478, 3), np.float32)
    pts[:, 0] = np.linspace(x1, x2, 478)
    pts[:, 1] = np.linspace(y1, y2, 478)
    return FaceLandmarks(
        points=pts, image_width=w, image_height=h, face_conf=1.0, num_faces=1, frame_id=0, timestamp=0.0
    )


def test_measure_reads_the_face_box_and_the_whole_image():
    rng = np.random.default_rng(0)
    luma = np.full((120, 160), 20, np.uint8)
    luma[30:90, 40:100] = rng.integers(100, 200, (60, 60), dtype=np.uint8)  # a lit, textured "face"
    m = measure(_pre(luma), _lm(40, 30, 100, 90, 160, 120), STRIDE)
    assert 140 < m["face_brightness"] < 160 and m["sharpness"] > 100
    assert m["scene_brightness"] < 60 and m["scene_contrast"] > 20
    flat = measure(_pre(np.full((120, 160), 4, np.uint8)), None, STRIDE)
    assert flat["scene_contrast"] == 0.0 and flat["face_brightness"] is None and flat["sharpness"] is None


def test_laplacian_variance_drops_when_the_patch_is_smoothed():
    rng = np.random.default_rng(1)
    sharp = rng.integers(0, 255, (64, 64)).astype(np.float32)
    smooth = (sharp + np.roll(sharp, 1, 0) + np.roll(sharp, 1, 1) + np.roll(sharp, (1, 1), (0, 1))) / 4
    assert laplacian_variance(smooth) < 0.5 * laplacian_variance(sharp)
    assert laplacian_variance(np.zeros((2, 2), np.uint8)) is None


def test_web_placeholder_without_luma_measures_nothing():
    pre = PreprocessedFrame(
        image=np.empty((0, 0, 3), np.uint8),
        gray=np.empty((0, 0), np.uint8),
        brightness=128.0,
        is_ir=False,
        scale=1.0,
        frame_id=0,
        timestamp=0.0,
    )
    assert set(measure(pre, None, STRIDE).values()) == {None}


# ------------------------------------------------------------------ block 9: unavailable with a reason
def drive(frames, speed=60.0):
    th = load_thresholds()
    th["enrollment"] = {**th["enrollment"], "enabled": False}
    p = DecisionPipeline(th)
    can = CanSimulator(scenario_from_dict({"start_clock": "12:00", "timeline": [{"t": 0, "speed_kmh": speed}]}))
    return [p.step(f, False, can.sample(f.timestamp)) for f in frames]


def seq(seconds, make, t0=0.0):
    return [make(t0 + i / FPS) for i in range(round(seconds * FPS))]


def test_dark_face_becomes_unavailable_low_light_after_low_quality_s():
    good = seq(10, lambda t: face(t, face_brightness=120, sharpness=80))
    dark = seq(8, lambda t: face(t, face_brightness=10), t0=10.0)
    out = drive(good + dark)
    assert not any(r.risk.unavailable for r in out[: len(good)])
    at = next(r.risk.t for r in out if r.risk.unavailable)
    assert 14.9 <= at <= 15.2  # risk.unavailable.low_quality_s = 5
    assert out[-1].risk.unavailable_reason == "low_light"


def test_short_shadow_does_not_stop_monitoring():
    frames = seq(10, lambda t: face(t, face_brightness=120)) + seq(3, lambda t: face(t, face_brightness=10), t0=10)
    frames += seq(5, lambda t: face(t, face_brightness=120), t0=13)
    assert not any(r.risk.unavailable for r in drive(frames))


def test_no_alert_from_eyes_read_on_an_unusable_face():
    # Glare: EAR collapses and reads as closed for good. Before M43 that was an endless L3.
    frames = seq(10, lambda t: face(t, face_brightness=120))
    frames += seq(12, lambda t: face(t, ear=SHUT, face_brightness=250), t0=10)
    out = drive(frames)
    last = out[-1]
    assert last.risk.unavailable and last.risk.unavailable_reason == "glare"
    assert last.risk.level == 0 and last.risk.hits == ()


def test_reason_of_a_lost_face_blocked_or_out_of_view():
    good = seq(5, lambda t: face(t, face_brightness=120))
    covered = drive(good + seq(5, lambda t: no_face(t, scene_brightness=2, scene_contrast=1), t0=5))
    assert covered[-1].risk.unavailable_reason == "camera_blocked"
    away = drive(good + seq(5, lambda t: no_face(t, scene_brightness=100, scene_contrast=60), t0=5))
    assert away[-1].risk.unavailable_reason == "no_face"
    unknown = drive(good + seq(5, no_face, t0=5))  # nothing measured (old traces): as before M43
    assert unknown[-1].risk.unavailable and unknown[-1].risk.unavailable_reason == "no_face"


def test_parked_is_never_unavailable():
    out = drive(seq(12, lambda t: face(t, face_brightness=10)), speed=0.0)
    assert not any(r.risk.unavailable for r in out)
    assert out[-1].quality.issue == "low_light"  # still measured, for the HUD state


def test_event_carries_the_cause_and_the_summary_the_seconds():
    th = load_thresholds()
    th["enrollment"] = {**th["enrollment"], "enabled": False}
    rec = Recorder()
    can = CanSimulator(scenario_from_dict({"start_clock": "12:00", "timeline": [{"t": 0, "speed_kmh": 60}]}))
    rt = TripRuntime(th, "trip-1", can, "t", FakeSelector(), emit=rec)
    frames = seq(6, lambda t: face(t, face_brightness=120)) + seq(9, lambda t: face(t, sharpness=0.2), t0=6)
    frames += seq(4, lambda t: face(t, face_brightness=120, sharpness=80), t0=15)
    for f in frames:
        rt.step(f, False, f.timestamp)
    events = [d for k, d in rec.records if k == "event"]
    assert [e["reasons"][0] for e in events] == ["monitoring_unavailable", "monitoring_restored"]
    assert events[0]["metrics"] == {"cause": "blur"} and events[1]["metrics"] == {}
    assert rt.hud.to_json()["unavailable_reason"] is None
    summary = rt.end_trip()
    assert set(summary["unavailable_by_cause"]) == {"blur"}
    assert 3.5 <= summary["unavailable_by_cause"]["blur"] <= 5.5
