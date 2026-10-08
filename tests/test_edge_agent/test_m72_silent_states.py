"""M72: two states in which nothing was measured and nobody was told (audit 08/10, A2 H1 and A3 M4).

- A face partly out of the image (block 6 `bad_angle`): blocks 7 / 8 do not read it, block 8's
  no-face time does not run, and block 9 timed only low_light / glare / blur. So no "monitoring
  unavailable" and no alert for as long as it lasted, and an "off road" from before it was held
  without limit.
- A crawl between context.stationary_kmh and context.min_speed_kmh (a jam): "unavailable" needed
  `moving`, so a covered camera at 3 km/h was silent.
Fake sequences, the real config/thresholds.yaml, no video.
"""

from dataclasses import replace

import pytest

from edge_agent.analysis.distraction import DistractionAnalyzer, DistractionConfig
from edge_agent.config import load_thresholds
from edge_agent.context.can_sim import CanSimulator, scenario_from_dict
from edge_agent.context.vehicle_context import ContextTracker
from edge_agent.decision.pipeline import DecisionPipeline
from edge_agent.decision.risk_engine import RiskEngine
from edge_agent.perception.features import FrameFeatures
from edge_agent.perception.quality import QualityState
from tests.test_edge_agent.test_decision import C0, D0, X0

FPS = 30.0
OPEN, SHUT = 0.30, 0.05
TH = load_thresholds()
HOLD_S = TH["distraction"]["pose_hold_s"]
LOW_QUALITY_S = TH["risk"]["unavailable"]["low_quality_s"]
NO_FACE_S = TH["risk"]["unavailable"]["no_face_s"]


def face(t, ear=OPEN, yaw=0.0, pitch=0.0, **q):
    return FrameFeatures(round(t * FPS), t, True, 1.0, ear=ear, mar=0.05, pitch=pitch, yaw=yaw, roll=0.0, **q)


def partial(t, ear=OPEN, yaw=0.0):
    """A face cut by the edge of the image: landmarks and a pose are there, block 6 does not trust them."""
    return FrameFeatures(
        round(t * FPS), t, True, 0.6, face_reliable=False, ear=ear, mar=0.05, pitch=0.0, yaw=yaw, roll=0.0
    )


def no_face(t):
    return FrameFeatures(round(t * FPS), t, False, 0.0, face_reliable=False)


def seq(t0, seconds, make):
    return [make(t0 + i / FPS) for i in range(round(seconds * FPS))]


def drive(frames, speed=60.0):
    """The decision chain at a constant speed by day. Returns (alerts, results)."""
    th = load_thresholds()
    th["enrollment"] = {**th["enrollment"], "enabled": False}
    p = DecisionPipeline(th)
    can = CanSimulator(scenario_from_dict({"start_clock": "12:00", "timeline": [{"t": 0, "speed_kmh": speed}]}))
    results = [p.step(f, False, can.sample(f.timestamp)) for f in frames]
    alerts = [(round(r.alert.new_alert.t, 1), r.alert.new_alert.level) for r in results if r.alert.new_alert]
    return alerts, results


def first_unavailable(results):
    return next((r.risk.t for r in results if r.risk.unavailable), None)


# ---------------------------------------------------------------- block 9: bad_angle is timed


def test_a_face_partly_out_of_the_image_becomes_unavailable_bad_angle():
    # The audit's case: 60 s partly out of the image, the eyes shut for 40 s of it.
    frames = seq(0, 10, face) + seq(10, 60, lambda t: partial(t, ear=SHUT if 20 <= t < 60 else OPEN))
    alerts, results = drive(frames)
    assert first_unavailable(results) == pytest.approx(10.0 + LOW_QUALITY_S, abs=0.1)
    late = [r for r in results if r.risk.t >= 10.0 + LOW_QUALITY_S + 0.1]
    assert all(r.risk.unavailable and r.risk.unavailable_reason == "bad_angle" for r in late)
    assert all(r.distraction.no_face_duration == 0.0 for r in late)  # a face is there: block 8 does not time it
    assert alerts == []  # nothing is read from such a face, so nothing is alerted either
    assert not any(r.presence.asking for r in results)  # the driver is in view: not "Bạn còn ở đó không?"


def test_a_short_partial_face_does_not_stop_monitoring():
    frames = seq(0, 10, face) + seq(10, LOW_QUALITY_S - 1.0, partial) + seq(9 + LOW_QUALITY_S, 5, face)
    alerts, results = drive(frames)
    assert first_unavailable(results) is None and alerts == []


def test_monitoring_comes_back_when_the_face_is_whole_again():
    frames = seq(0, 10, face) + seq(10, 10, partial) + seq(20, 5, face)
    _, results = drive(frames)
    assert results[-1].risk.unavailable is False and results[-1].quality.issue is None
    back = next(r.risk.t for r in results if r.risk.t > 20.0 and not r.risk.unavailable)
    assert back == pytest.approx(20.0 + TH["quality"]["clear_s"], abs=0.1)


def test_a_partial_face_while_parked_is_not_unavailable():
    _, results = drive(seq(0, 15, partial), speed=0.0)
    assert first_unavailable(results) is None
    assert results[-1].quality.issue == "bad_angle"  # still named, for the HUD


def test_a_closure_carried_through_a_head_drop_is_still_watched_on_a_partial_face():
    """A dropped head is often partly out of the image: the microsleep alarm must not be cut at 5 s."""
    q = QualityState(issue="bad_angle", duration=LOW_QUALITY_S + 1.0)
    dropped = replace(D0, closed_duration=4.0, microsleep=True, head_drop=True, eye_closed=None)
    r = RiskEngine().assess(dropped, X0, C0, quality=q)
    assert not r.unavailable and r.level == 3 and r.reasons == ("microsleep",)
    r = RiskEngine().assess(replace(dropped, head_drop=False), X0, C0, quality=q)
    assert r.unavailable and r.unavailable_reason == "bad_angle" and r.level == 0


def test_bad_angle_is_timed_against_low_quality_s():
    engine = RiskEngine()
    short = engine.assess(D0, X0, C0, quality=QualityState(issue="bad_angle", duration=LOW_QUALITY_S - 0.1))
    long = engine.assess(D0, X0, C0, quality=QualityState(issue="bad_angle", duration=LOW_QUALITY_S))
    assert not short.unavailable and long.unavailable


# ---------------------------------------------------------------- block 8: the held "off road" ends


def analyzer(**over):
    return DistractionAnalyzer(DistractionConfig(baseline_adapt=False, **over))


def test_off_road_is_held_for_pose_hold_s_then_ends():
    a = analyzer()
    states = [a.update(f, False, True) for f in seq(0, 0.5, lambda t: face(t, yaw=35.0)) + seq(0.5, 9.5, partial)]
    last_pose_t = 0.5 - 1 / FPS
    held = [s for s in states if s.off_road]
    assert held[-1].timestamp == pytest.approx(last_pose_t + HOLD_S, abs=1.5 / FPS)
    assert states[-1].off_road_duration == 0.0


def test_before_m72_the_held_off_road_never_ended():
    a = analyzer(pose_hold_s=0.0)  # 0 = no limit
    states = [a.update(f, False, True) for f in seq(0, 0.5, lambda t: face(t, yaw=35.0)) + seq(0.5, 9.5, partial)]
    assert states[-1].off_road and states[-1].off_road_duration == pytest.approx(10.0, abs=0.1)


def test_a_glance_then_a_partial_face_is_not_an_alert_for_ever():
    """The audit's other direction: a 0.5 s glance, then the face partly out for 9.5 s."""
    frames = seq(0, 10, face) + seq(10, 0.5, lambda t: face(t, yaw=35.0)) + seq(10.5, 9.5, partial) + seq(20, 5, face)
    alerts, results = drive(frames)
    off = [r.risk.t for r in results if r.distraction.off_road]
    assert off[-1] <= 10.5 + HOLD_S + 0.1  # before: off road until the face came back at 20 s
    assert len(alerts) <= 1  # the held state may still reach the rule once (as for a lost face), never again


def test_the_hold_also_ends_for_a_lost_face():
    a = analyzer()
    states = [a.update(f, False, True) for f in seq(0, 1.0, lambda t: face(t, yaw=35.0)) + seq(1.0, 6.0, no_face)]
    assert not states[-1].off_road and not states[-1].turned_away
    assert states[-1].no_face_duration == pytest.approx(6.0, abs=0.1)  # its own timer goes on


def test_looking_behind_keeps_its_own_longer_hold():
    a = analyzer()
    max_s = a.config.turned_away_max_s
    assert max_s > HOLD_S
    states = [
        a.update(f, False, True) for f in seq(0, 1.0, lambda t: face(t, yaw=60.0)) + seq(1.0, max_s - 1.0, no_face)
    ]
    assert states[-1].off_road and states[-1].turned_away


def test_a_pose_now_and_then_keeps_the_state_alive():
    """A reliable pose every second (still turned): the hold starts again from each of them."""
    a = analyzer()
    frames = []
    for k in range(8):
        frames += seq(k, 0.1, lambda t: face(t, yaw=40.0)) + seq(k + 0.1, 0.9, partial)
    states = [a.update(f, False, True) for f in frames]
    assert states[-1].off_road and states[-1].off_road_duration == pytest.approx(8.0, abs=0.1)


# ---------------------------------------------------------------- 1-5 km/h: unavailable in a crawl


def test_rolling_is_moving_or_a_crawl():
    tracker = ContextTracker()
    kmh = lambda v: tracker.update(  # noqa: E731
        CanSimulator(scenario_from_dict({"timeline": [{"t": 0, "speed_kmh": v}]})).sample(0.0)
    )
    assert (kmh(0.0).rolling, kmh(0.9).rolling) == (False, False)  # standing still
    assert kmh(3.0).rolling and not kmh(3.0).moving  # a crawl
    assert kmh(60.0).rolling and kmh(60.0).moving
    assert replace(C0, speed_kmh=None, moving=True).rolling  # no speed signal: monitored as moving
    assert not replace(C0, speed_kmh=None, moving=False).rolling


def test_face_lost_in_a_crawl_is_unavailable():
    alerts, results = drive(seq(0, 10, face) + seq(10, 12, no_face), speed=3.0)
    assert first_unavailable(results) == pytest.approx(10.0 + NO_FACE_S, abs=0.1)
    assert results[-1].risk.unavailable_reason == "no_face"
    assert alerts == []
    assert any(r.presence.asking for r in results)  # out of view: the HUD asks, as at speed
    assert not any(r.distraction.active for r in results)  # the distraction rules stay off below min_speed


def test_face_lost_while_standing_still_is_still_silent():
    _, results = drive(seq(0, 10, face) + seq(10, 12, no_face), speed=0.0)
    assert first_unavailable(results) is None
    assert results[-1].distraction.no_face_duration == 0.0


def test_unreadable_face_in_a_crawl_is_unavailable():
    dark = seq(10, 8, lambda t: face(t, face_brightness=10))
    _, results = drive(seq(0, 10, lambda t: face(t, face_brightness=120)) + dark, speed=3.0)
    assert results[-1].risk.unavailable and results[-1].risk.unavailable_reason == "low_light"
    _, results = drive(seq(0, 10, face) + seq(10, 8, partial), speed=3.0)
    assert results[-1].risk.unavailable and results[-1].risk.unavailable_reason == "bad_angle"


def test_the_no_face_time_runs_through_a_change_of_speed():
    """Lost in a crawl, then the vehicle speeds up: one no-face time, not two."""
    a = analyzer()
    for f in seq(0, 2.0, no_face):
        s = a.update(f, False, False, rolling=True)
    assert s.no_face_duration == pytest.approx(2.0, abs=0.05) and not s.active
    for f in seq(2.0, 2.0, no_face):
        s = a.update(f, False, True, rolling=True)
    assert s.no_face_duration == pytest.approx(4.0, abs=0.05) and s.active
    s = a.update(no_face(4.0), False, False, rolling=False)  # stopped: nothing is timed
    assert s.no_face_duration == 0.0


def test_a_frame_gap_in_a_crawl_restarts_the_no_face_time():
    a = analyzer()
    for f in seq(0, 2.0, no_face):
        a.update(f, False, False, rolling=True)
    s = a.update(no_face(2.0 + a.config.max_gap_s + 1.0), False, False, rolling=True)  # M71: not seen in between
    assert s.no_face_duration == 0.0
