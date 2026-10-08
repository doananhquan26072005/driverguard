"""M77: numbers that are not finite (audit 08/10, A1 M4 and A3 L1).

- Block 3 let a face with a NaN landmark through: EAR was NaN, and one NaN EAR kept block 7's
  open-eye baseline NaN, so the eyes read as open while they were shut. Now such a face is no face,
  on the device (`FaceLandmarkDetector.detect`) and in the browser (`WebAgent.frame`).
- Block 9 turned one NaN measurement into a NaN drowsy_score: level 0 whatever the other signs said,
  a NaN minute in trip memory, and a record that is not JSON. Now it reads as 0 for its own term.
Fake numbers and a stand-in for the MediaPipe model, no video.
"""

import json
import logging
import math
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

import edge_agent.web.bridge as bridge
from edge_agent.decision.risk_engine import DISTRACTION_INPUTS, DROWSY_INPUTS, RiskEngine
from edge_agent.decision.trip_memory import TripMemory, TripState
from edge_agent.perception.features import LEFT_EYE
from edge_agent.perception.landmarks import FaceLandmarkDetector, LandmarkConfig, finite_faces, finite_scores
from edge_agent.perception.preprocess import PreprocessedFrame
from edge_agent.web.bridge import WebAgent
from tests.test_edge_agent.test_decision import C0, D0, X0
from tests.test_edge_agent.test_web_bridge import FPS, H, W, synthetic_face

NAN, INF = float("nan"), float("inf")
EYELID = LEFT_EYE[1]  # an upper-lid point EAR is computed from; not a head-pose point


def broken(points: np.ndarray, value: float = NAN, index: int = EYELID) -> np.ndarray:
    out = points.copy()
    out[index, 1] = value
    return out


def passenger() -> np.ndarray:
    """A smaller face further back, eyes half shut (so it is told apart by its EAR)."""
    small = synthetic_face(ear=0.20)
    small[:, :2] = (small[:, :2] - small[1, :2]) * 0.6 + (120, 300)
    return small


# ---------------------------------------------------------------- block 3: the helpers


def test_a_face_with_a_nan_or_inf_landmark_is_not_a_face():
    good = synthetic_face()
    assert finite_faces([good]) == [0]
    assert finite_faces([broken(good), good, broken(good, INF), broken(good, -INF, index=1)]) == [1]
    assert finite_faces([]) == []


def test_a_blendshape_score_that_is_not_finite_is_a_missing_one():
    assert finite_scores(0.1, 0.9) == (pytest.approx(0.1), pytest.approx(0.9))
    assert finite_scores(0.1, NAN) is None and finite_scores(INF) is None


# ---------------------------------------------------------------- block 3: on the device


class Model:
    """Stand-in for MediaPipe's FaceLandmarker: answers with the given faces (pixels) and blendshapes."""

    def __init__(self, faces, blendshapes=None):
        self.result = SimpleNamespace(
            face_landmarks=[[SimpleNamespace(x=x / W, y=y / H, z=z / W) for x, y, z in f] for f in faces],
            face_blendshapes=[
                [SimpleNamespace(category_name=name, score=score) for name, score in b.items()] for b in blendshapes
            ]
            if blendshapes
            else None,
        )

    def detect(self, image):
        return self.result


def detect(faces, blendshapes=None):
    detector = FaceLandmarkDetector.__new__(FaceLandmarkDetector)  # no model file, no MediaPipe
    detector.config, detector.image_mode = LandmarkConfig(), True
    detector._mp = SimpleNamespace(Image=lambda **kw: None, ImageFormat=SimpleNamespace(SRGB=0))
    detector._landmarker = Model(faces, blendshapes)
    detector.selector = bridge.DriverSelector(detector.config)
    image = np.zeros((H, W, 3), np.uint8)
    return detector.detect(PreprocessedFrame(image, image[:, :, 0], 128.0, False, 1.0, 7, 0.5))


def blend(blink, brow=0.1):
    return {"eyeBlinkLeft": blink, "eyeBlinkRight": blink, "browOuterUpLeft": brow, "browOuterUpRight": brow}


def test_device_keeps_a_finite_face():
    lm = detect([synthetic_face()], [blend(0.2)])
    assert lm is not None and lm.num_faces == 1 and np.isfinite(lm.points).all()
    assert lm.eye_blink == (pytest.approx(0.2), pytest.approx(0.2)) and lm.brow_up == pytest.approx(0.1)


@pytest.mark.parametrize("value", [NAN, INF])
def test_device_drops_a_face_with_a_non_finite_landmark(value):
    assert detect([broken(synthetic_face(), value)], [blend(0.2)]) is None


def test_device_picks_among_the_finite_faces_and_keeps_that_faces_own_blendshapes():
    # The larger face (the driver before enrollment) is broken: the other one is what is left, and
    # its blink score is its own, not the broken face's.
    lm = detect([broken(synthetic_face()), passenger()], [blend(0.9), blend(0.3)])
    assert lm is not None and lm.num_faces == 1
    assert lm.eye_blink == (pytest.approx(0.3), pytest.approx(0.3))
    lm = detect([passenger(), synthetic_face()], [blend(0.3), blend(0.9)])  # nothing broken: the largest, as before
    assert lm.num_faces == 2 and lm.eye_blink == (pytest.approx(0.9), pytest.approx(0.9))


def test_device_drops_non_finite_blendshape_scores_only():
    lm = detect([synthetic_face()], [blend(NAN, brow=INF) | {"jawOpen": NAN, "mouthClose": 0.4}])
    assert lm is not None and lm.eye_blink is None and lm.brow_up is None
    assert lm.blendshapes == {"mouthClose": pytest.approx(0.4)}


# ---------------------------------------------------------------- block 3: in the browser


def web_frame(agent, t, points, blink=(0.05, 0.05), faces=1, brow=None):
    p = None if points is None else np.asarray(points, np.float32).ravel()
    return json.loads(agent.frame(t, round(t * FPS), W, H, p, faces, blink, 12.0, 140.0, brow))


def drive_with_one_nan_frame(agent):
    """The audit's sequence: 30 s at EAR 0.30 with one NaN eyelid frame at 15 s, then the eyes shut 2.5 s."""
    good, shut = synthetic_face(), synthetic_face(ear=0.05)
    state = None
    for i in range(round(32.5 * FPS)):
        t = i / FPS
        if t >= 30.0:
            state = web_frame(agent, t, shut, blink=(0.9, 0.9))
        else:
            state = web_frame(agent, t, broken(good) if i == round(15 * FPS) else good)
    return state


def test_web_one_nan_frame_does_not_blind_the_drowsiness_branch():
    agent = WebAgent("web-an", "trip-web-1", scenario="highway_night")
    state = drive_with_one_nan_frame(agent)
    assert state["level"] == 3 and "microsleep" in state["reasons"]
    assert "error" not in state


def test_web_control_without_the_guard_the_same_sequence_raises_nothing(monkeypatch):
    # The behaviour before M77, to show the sequence above is the audit's failure and not an easy one.
    monkeypatch.setattr(bridge, "finite_faces", lambda faces: list(range(len(faces))))
    agent = WebAgent("web-an", "trip-web-1", scenario="highway_night")
    state = drive_with_one_nan_frame(agent)
    assert state["level"] == 0 and state["reasons"] == []


def test_web_a_nan_face_is_a_frame_without_a_face():
    agent = WebAgent("web-an", "trip-web-1", scenario="highway_night")
    state = web_frame(agent, 0.0, broken(synthetic_face()))
    assert state["measures"] == {"face": False, "ear": None, "mar": None, "yaw": None, "pitch": None, "phone": None}
    assert "error" not in state  # not a failed frame: it is measured as "no face"


def test_web_picks_among_the_finite_faces_with_that_faces_own_blink():
    agent = WebAgent("web-an", "trip-web-1", scenario="highway_night")
    faces = np.stack([broken(synthetic_face()), passenger()])
    state = web_frame(agent, 0.0, faces, blink=(0.9, 0.9, 0.05, 0.05), faces=2)
    assert state["measures"]["ear"] == pytest.approx(0.20, abs=0.01)


def test_web_a_nan_blink_or_brow_score_is_a_missing_one():
    agent = WebAgent("web-an", "trip-web-1", scenario="highway_night")
    seen = {}
    inner = agent.extractor
    agent.extractor = lambda lm, *a: seen.update(lm=lm) or inner(lm, *a)
    web_frame(agent, 0.0, synthetic_face(), blink=(NAN, 0.1), brow=(NAN,))
    assert seen["lm"].eye_blink is None and seen["lm"].brow_up is None
    web_frame(agent, 1 / FPS, synthetic_face(), blink=(0.2, 0.1), brow=(0.3,))
    assert seen["lm"].eye_blink == (pytest.approx(0.2), pytest.approx(0.1)) and seen["lm"].brow_up == pytest.approx(0.3)


# ---------------------------------------------------------------- block 9


SIGNS = replace(D0, events=("microsleep",), yawn_count_10min=3, nod_count_5min=2)  # 25 + 15 + 20 = 60, L1


def test_a_normal_frame_is_not_copied():
    engine = RiskEngine()
    assert engine._finite(D0, DROWSY_INPUTS) == (D0, ())
    assert engine._finite(D0, DROWSY_INPUTS)[0] is D0 and engine._finite(X0, DISTRACTION_INPUTS)[0] is X0


@pytest.mark.parametrize("value", [NAN, INF, -INF])
def test_a_non_finite_perclos_only_loses_its_own_term(value):
    r = RiskEngine().assess(replace(SIGNS, perclos_60s=value, perclos_ready=True), X0, C0)
    assert r.drowsy_score == pytest.approx(60.0) and r.level == 1 and r.reasons == ("drowsy_score",)
    assert r.drowsy_terms[0] == 0.0 and all(math.isfinite(v) for v in r.drowsy_terms)
    json.dumps([r.drowsy_score, r.distraction_score, *r.drowsy_terms], allow_nan=False)  # raises on NaN


@pytest.mark.parametrize("name", [n for n in DROWSY_INPUTS if n != "perclos_60s"])
def test_every_drowsiness_input_is_guarded(name):
    r = RiskEngine().assess(replace(SIGNS, **{name: NAN}), X0, C0)
    assert math.isfinite(r.drowsy_score) and all(math.isfinite(h.value) for h in r.hits)
    assert r.drowsy_score >= 40.0  # the two signs that are left still add up


def test_a_non_finite_closed_duration_is_not_a_microsleep_and_not_a_nan_score():
    for value in (NAN, INF):  # how long is unknown: no L3 on a number nobody measured
        r = RiskEngine().assess(replace(D0, closed_duration=value), X0, C0)
        assert r.level == 0 and r.hits == () and r.drowsy_score == 0.0


def test_an_unknown_blink_rate_is_not_blinking_too_little():
    trip = TripState(100.0, 600.0, (), None, None, (0, 0, 0, 0))
    engine = RiskEngine()
    seen = replace(D0, blink_observed_s=60.0)  # a minute of eye data: the rule reads the rate
    assert [h.reason for h in engine.assess(replace(seen, blink_rate=2.0), X0, C0, trip).hits] == ["blink_rate"]
    assert engine.assess(replace(seen, blink_rate=NAN), X0, C0, trip).hits == ()


def test_a_non_finite_off_road_duration_leaves_the_phone_rule_and_a_finite_score():
    r = RiskEngine().assess(D0, replace(X0, off_road_duration=NAN, phone_ratio_2s=1.0), C0)
    assert r.distraction_score == 100.0 and [h.reason for h in r.hits] == ["phone"]
    r = RiskEngine().assess(D0, replace(X0, off_road_duration=NAN), C0)
    assert r.distraction_score == 0.0 and r.level == 0
    r = RiskEngine().assess(D0, replace(X0, phone_ratio_2s=NAN, off_road_duration=5.0), C0)
    assert r.distraction_score == 100.0 and [h.reason for h in r.hits] == ["off_road"]


def test_a_non_finite_no_face_duration_is_not_unavailable():
    r = RiskEngine().assess(D0, replace(X0, no_face_duration=INF), C0)
    assert not r.unavailable


def test_each_field_is_logged_once(caplog):
    engine = RiskEngine()
    with caplog.at_level(logging.WARNING, logger="driverguard.risk"):
        for _ in range(50):
            engine.assess(replace(D0, perclos_60s=NAN), replace(X0, off_road_duration=NAN), C0)
        engine.assess(replace(D0, perclos_60s=NAN, closed_duration=NAN), X0, C0)
    named = [rec.getMessage().split(" ")[0] for rec in caplog.records]
    assert named == ["perclos_60s", "off_road_duration", "closed_duration"]


# ---------------------------------------------------------------- block 11


def test_trip_memory_does_not_bin_a_non_finite_score():
    memory = TripMemory()
    state = None
    for minute, score in enumerate((10.0, 20.0, 30.0)):
        for i in range(60):
            t = minute * 60.0 + i
            state = memory.update(t, NAN if (minute, i) == (1, 30) else score)
    state = memory.update(180.0, 30.0)
    assert state.minute_scores == (10.0, 20.0, 30.0) and state.trend_15min == pytest.approx(10.0)


def test_a_minute_of_only_non_finite_scores_is_skipped_like_a_minute_without_frames():
    memory = TripMemory()
    for t in range(60):
        memory.update(float(t), NAN, events=("microsleep",) if t == 5 else ())
    state = memory.update(60.0, 0.0)
    assert state.minute_scores == () and state.bins_completed == 0
    assert state.last_microsleep_t == 5.0  # the event was seen; only the number is unusable
