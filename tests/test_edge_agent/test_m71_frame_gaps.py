"""M71: a long gap between two frames (the loop stood still, frames were lost) is not an observation.

Blocks 7, 8 and 12 measure durations as differences of timestamps. Two frames on either side of a
freeze used to be joined into one long closure / look away / confirmation. Fake sequences with
holes in them, the real config/thresholds.yaml, no video.
"""

import pytest

from edge_agent.analysis.distraction import DistractionAnalyzer, DistractionConfig
from edge_agent.analysis.drowsiness import DrowsinessAnalyzer
from edge_agent.config import load_thresholds
from edge_agent.context.can_sim import CanSimulator, scenario_from_dict
from edge_agent.decision.alert_manager import AlertConfig, AlertManager
from edge_agent.decision.pipeline import DecisionPipeline
from edge_agent.decision.risk_engine import RiskAssessment, RuleHit
from edge_agent.perception.features import FrameFeatures

OPEN, SHUT = 0.30, 0.05
WARM_S = 30.0  # eyes open, looking ahead: the baselines settle


def span(t0, seconds, fps=30.0, **signals):
    """Frames from t0 for `seconds`, every 1 / fps: [(t, signals)]."""
    return [(t0 + i / fps, signals) for i in range(round(seconds * fps))]


def features(i, t, ear=OPEN, mar=0.05, yaw=0.0, pitch=0.0, face=True):
    if not face:
        return FrameFeatures(i, t, False, 0.0)
    return FrameFeatures(i, t, True, 1.0, ear=ear, mar=mar, pitch=pitch, yaw=yaw, roll=0.0)


def drive(frames):
    """The decision chain at a constant 60 km/h by day. Returns (alerts, results)."""
    th = load_thresholds()
    th["enrollment"] = {**th["enrollment"], "enabled": False}
    pipeline = DecisionPipeline(th)
    timeline = [{"t": 0, "speed_kmh": 60}, {"t": 100000, "speed_kmh": 60}]
    can = CanSimulator(
        scenario_from_dict({"name": "t", "start_clock": "15:00", "initial_drive_time_s": 600, "timeline": timeline})
    )
    alerts, results = [], []
    for i, (t, signals) in enumerate(frames):
        r = pipeline.step(features(i, t, **signals), False, can.sample(t))
        results.append(r)
        if r.alert.new_alert is not None:
            alerts.append((round(r.alert.new_alert.t, 1), r.alert.new_alert.level, r.alert.new_alert.reasons))
    return alerts, results


def events(results):
    return [e for r in results for e in r.drowsiness.events if e != "blink"]


# ---------------------------------------------------------------- block 7: eyes


@pytest.mark.parametrize("freeze_s", [1.0, 2.0, 7.0])
def test_a_blink_on_each_side_of_a_freeze_is_not_one_long_closure(freeze_s):
    """Before M71: 1 s -> a `microsleep` event (25 points for 5 minutes), 2 s -> L3, 7 s -> L3 + unresponsive."""
    t1 = WARM_S + 0.1 + freeze_s
    frames = span(0, WARM_S) + span(WARM_S, 0.1, ear=SHUT) + span(t1, 0.1, ear=SHUT) + span(t1 + 0.1, 5)
    alerts, results = drive(frames)
    assert alerts == []
    assert events(results) == []
    assert max(r.drowsiness.closed_duration for r in results) < 0.2
    assert max(r.risk.drowsy_score for r in results) == 0.0


def test_eyes_still_shut_after_a_freeze_reach_l3_on_what_is_seen():
    """The closure starts again at the first frame after the freeze: L3 after microsleep_l3_s of frames."""
    back = WARM_S + 0.1 + 3.0
    frames = span(0, WARM_S) + span(WARM_S, 0.1, ear=SHUT) + span(back, 3.0, ear=SHUT)
    alerts, _ = drive(frames)
    assert [(lv, reasons) for _, lv, reasons in alerts] == [(3, ("microsleep",))]
    assert alerts[0][0] == pytest.approx(back + 1.5, abs=0.1)


def test_a_gap_within_max_gap_s_does_not_break_a_closure():
    """A few lost frames are not a freeze: 1.0 s shut, 0.4 s without frames, shut again is one closure."""
    frames = span(0, WARM_S) + span(WARM_S, 1.0, ear=SHUT) + span(WARM_S + 1.4, 1.0, ear=SHUT)
    alerts, _ = drive(frames)
    assert [(lv, reasons) for _, lv, reasons in alerts] == [(3, ("microsleep",))]
    assert alerts[0][0] == pytest.approx(WARM_S + 1.5, abs=0.1)


@pytest.mark.parametrize("fps", [5.0, 10.0, 12.0])
def test_a_slow_loop_still_times_a_microsleep(fps):
    """Frames 0.1-0.2 s apart are far inside max_gap_s: the L3 rule does not depend on 30 FPS."""
    frames = span(0, WARM_S, fps) + span(WARM_S, 3.0, fps, ear=SHUT)
    alerts, _ = drive(frames)
    assert [(lv, reasons) for _, lv, reasons in alerts] == [(3, ("microsleep",))]
    assert alerts[0][0] == pytest.approx(WARM_S + 1.5, abs=1.5 / fps + 0.05)


def test_a_carried_closure_ends_at_a_freeze():
    """Eyes shut, head dropped (closure carried), then 7 s without frames: not `unresponsive`."""
    drop = WARM_S + 1.0
    frames = (
        span(0, WARM_S)
        + span(WARM_S, 1.0, ear=SHUT)
        + span(drop, 0.5, ear=SHUT, pitch=40.0)
        + span(drop + 7.5, 1.0, ear=SHUT, pitch=40.0)
    )
    alerts, results = drive(frames)
    assert results[-1].drowsiness.closed_duration == 0.0
    assert not any("unresponsive" in reasons for _, _, reasons in alerts)


# ---------------------------------------------------------------- block 7: mouth, head, brow


def run_block7(frames):
    a = DrowsinessAnalyzer()
    return [a.update(features(i, t, **signals)) for i, (t, signals) in enumerate(frames)]


def test_an_open_mouth_on_each_side_of_a_freeze_is_not_a_yawn():
    states = run_block7(span(0, 5) + span(5, 0.2, mar=1.0) + span(8.2, 0.2, mar=1.0) + span(8.4, 2))
    assert not any("yawn" in s.events for s in states)


def test_a_yawn_already_counted_is_not_counted_again_after_a_short_freeze():
    states = run_block7(span(0, 5) + span(5, 2.5, mar=1.0) + span(8.2, 2.5, mar=1.0) + span(10.7, 2))
    assert sum("yawn" in s.events for s in states) == 1


def test_a_head_dip_across_a_freeze_is_neither_a_nod_nor_a_bow():
    """Head down, 3 s without frames, head level: how it came back up was not seen."""
    states = run_block7(span(0, 10) + span(10, 0.3, pitch=30.0, ear=SHUT) + span(13.3, 2))
    assert not any(e in s.events for s in states for e in ("nod", "bow"))


# ---------------------------------------------------------------- block 8


def test_a_glance_on_each_side_of_a_freeze_is_not_one_long_look_away():
    """Before M71: glance 0.2 s, 3 s without frames, glance 0.6 s -> off_road_duration 3.8 s, L2 off_road."""
    t1 = WARM_S + 0.2 + 3.0
    frames = span(0, WARM_S) + span(WARM_S, 0.2, yaw=50.0) + span(t1, 0.6, yaw=50.0) + span(t1 + 0.6, 5)
    alerts, results = drive(frames)
    assert alerts == []
    assert max(r.distraction.off_road_duration for r in results) < 1.0  # 0.6 s + on_road_confirm_s


def test_still_looking_away_after_a_freeze_is_l2_on_what_is_seen():
    back = WARM_S + 0.2 + 3.0
    frames = span(0, WARM_S) + span(WARM_S, 0.2, yaw=50.0) + span(back, 4.0, yaw=50.0)
    alerts, _ = drive(frames)
    assert [(lv, reasons) for _, lv, reasons in alerts] == [(2, ("off_road",))]
    assert alerts[0][0] == pytest.approx(back + 2.5, abs=0.1)  # off_road_s + rise_confirm_s[2]


def test_no_face_on_each_side_of_a_freeze_is_not_a_long_absence():
    """The freeze itself is told to the driver by the loop's own health checks, not as "face not seen"."""
    t1 = WARM_S + 0.2 + 6.0
    frames = span(0, WARM_S) + span(WARM_S, 0.2, face=False) + span(t1, 0.2, face=False) + span(t1 + 0.2, 2)
    _, results = drive(frames)
    assert max(r.distraction.no_face_duration for r in results) < 0.3
    assert not any(r.risk.unavailable for r in results)


def test_the_road_baseline_and_the_phone_window_survive_a_freeze():
    a = DistractionAnalyzer(DistractionConfig())
    for i, (t, signals) in enumerate(span(0, 20, yaw=12.0)):
        a.update(features(i, t, **signals), True, True)
    before = a.baseline_yaw
    s = a.update(features(0, 21.0, yaw=12.0), True, True)
    assert s.baseline_yaw == pytest.approx(before, abs=0.5) and before > 5.0
    assert s.phone_ratio_2s == 1.0  # samples of the last 2 s were really seen


# ---------------------------------------------------------------- block 12

ALERTS = AlertConfig(rise_confirm_s={1: 1.0, 2: 0.5, 3: 0.0}, fall_hold_s=3.0, cooldown_s={1: 120, 2: 30, 3: 0})


def risk(t, level, reasons=("x",)):
    hits = tuple(RuleHit(level, k, 1.0) for k in reasons) if level > 0 else ()
    return RiskAssessment(t, level, hits, 0.0, 0.0, (0, 0, 0, 0))


def test_two_frames_around_a_freeze_do_not_confirm_a_level():
    """Before M71 the second frame raised L2: the confirmation compared timestamps only (audit A3 L5)."""
    m = AlertManager(ALERTS)
    assert m.update(risk(10.0, 2)).new_alert is None
    assert m.update(risk(12.0, 2)).new_alert is None
    out = [m.update(risk(12.0 + i * 0.1, 2)) for i in range(1, 7)]
    assert [round(o.t, 1) for o in out if o.new_alert is not None] == [12.5]


def test_a_new_reason_is_not_confirmed_across_a_freeze_either():
    m = AlertManager(ALERTS)
    for i in range(10):
        m.update(risk(i * 0.1, 2, ("off_road",)))
    assert m.active_level == 2
    assert m.update(risk(1.0, 2, ("off_road", "phone"))).new_alert is None
    assert m.update(risk(3.0, 2, ("off_road", "phone"))).new_alert is None
    out = [m.update(risk(3.0 + i * 0.1, 2, ("off_road", "phone"))) for i in range(1, 7)]
    assert [o.new_alert.reasons[0] for o in out if o.new_alert is not None] == ["phone"]


def test_a_freeze_leaves_an_active_level_alone_and_l3_stays_immediate():
    m = AlertManager(ALERTS)
    for i in range(10):
        m.update(risk(i * 0.1, 2))
    assert m.update(risk(5.0, 2)).active_level == 2  # still held after the gap: no new alert, no drop
    assert m.update(risk(9.0, 3)).new_alert.level == 3
