"""M76: lids droop, then shut. The L3 rule times the shut part, however long the drooping was.

Block 7 only counts a closure that is deep on `microsleep_deep.min_frac` of its frames, from the
frame the eyes went under the close threshold. Drooping lids are inside that closure, so the rule
came late by about the length of the drooping, or never. Now the running stretch of deep frames
counts from its own start. Fake sequences, the real config/thresholds.yaml, no video.
"""

import pytest

from edge_agent.analysis.drowsiness import DrowsinessConfig
from edge_agent.config import load_thresholds
from edge_agent.context.can_sim import CanSimulator, scenario_from_dict
from edge_agent.decision.pipeline import DecisionPipeline
from edge_agent.perception.features import FrameFeatures

OPEN, SHUT = 0.30, 0.05
DROOP = 0.18  # 0.6 x the open-eye EAR: closed for block 7 (< 0.65 x), not deep (> 0.5 x)
WARM_S = 30.0  # eyes open, looking ahead: the baselines settle
OFF = {"run_gap_s": -1}  # the rule before M76


def span(t0, seconds, fps=30.0, **signals):
    """Frames from t0 for `seconds`, every 1 / fps: [(t, signals)]."""
    return [(t0 + i / fps, signals) for i in range(round(seconds * fps))]


def features(i, t, ear=OPEN, mar=0.05, yaw=0.0, pitch=0.0, blink=None):
    return FrameFeatures(i, t, True, 1.0, ear=ear, mar=mar, pitch=pitch, yaw=yaw, roll=0.0, eye_blink=blink)


def drive(frames, **deep):
    """The decision chain at a constant 60 km/h by day. deep: drowsiness.microsleep_deep overrides.
    Returns (alerts, results)."""
    th = load_thresholds()
    th["enrollment"] = {**th["enrollment"], "enabled": False}
    th["drowsiness"]["microsleep_deep"].update(deep)
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


def microsleeps(results):
    """`microsleep` events of block 7. (Drooping also counts for PERCLOS, which is not what is tested here.)"""
    return sum(e == "microsleep" for r in results for e in r.drowsiness.events)


def l3(alerts):
    return [t for t, level, reasons in alerts if level == 3 and "microsleep" in reasons]


def droop_then_shut(droop_s, shut_s, fps=30.0, **shut_signals):
    shut = WARM_S + droop_s
    frames = span(0, WARM_S, fps) + span(WARM_S, droop_s, fps, ear=DROOP)
    return frames + span(shut, shut_s, fps, ear=SHUT, **shut_signals), shut


# ---------------------------------------------------------------- the missed case


@pytest.mark.parametrize("droop_s", [0.0, 2.0, 4.0, 10.0])
def test_l3_comes_microsleep_l3_s_after_the_eyes_shut_whatever_the_drooping(droop_s):
    """Before M76 (audit 08/10): 1.50 s after shutting with no drooping, 1.97 / 3.97 / 9.97 s after 2 / 4 / 10 s."""
    frames, shut = droop_then_shut(droop_s, 3.0)
    alerts, results = drive(frames)
    assert l3(alerts) == [pytest.approx(shut + 1.5, abs=0.1)]
    assert microsleeps(results) == 1


@pytest.mark.parametrize("droop_s, shut_s", [(4.0, 3.0), (10.0, 6.0)])
def test_the_rule_before_m76_missed_it(droop_s, shut_s):
    """Control, `run_gap_s: -1`: the shut part is under half of the closure until it is as long as the drooping."""
    frames, _ = droop_then_shut(droop_s, shut_s)
    alerts, results = drive(frames, **OFF)
    assert l3(alerts) == [] and microsleeps(results) == 0
    assert max(r.drowsiness.closed_duration for r in results) == 0.0


def test_once_the_whole_closure_is_deep_it_counts_from_its_start_as_before():
    """Drooping 0.6 s, shut 2.4 s: deep on over half of its frames, so the 0.6 s is counted too (unchanged)."""
    frames, shut = droop_then_shut(0.6, 2.4)
    _, results = drive(frames)
    _, before = drive(frames, **OFF)
    assert max(r.drowsiness.closed_duration for r in results) == pytest.approx(3.0, abs=0.1)
    assert results[-1].drowsiness.closed_duration == before[-1].drowsiness.closed_duration


@pytest.mark.parametrize("fps", [10.0, 12.0, 15.0])
def test_a_slow_loop_times_the_shut_part_too(fps):
    frames, shut = droop_then_shut(6.0, 3.0, fps)
    alerts, _ = drive(frames)
    assert l3(alerts) == [pytest.approx(shut + 1.5, abs=1.5 / fps + 0.05)]


def test_eyes_shut_after_drooping_then_the_head_drops_keeps_counting():
    """Drooping 4 s, shut 0.8 s, then the head drops and the eyes cannot be judged: the closure is carried."""
    frames, shut = droop_then_shut(4.0, 0.8)
    frames += span(shut + 0.8, 2.0, ear=SHUT, pitch=40.0)
    alerts, results = drive(frames)
    assert results[-1].drowsiness.head_drop
    assert l3(alerts) == [pytest.approx(shut + 1.5, abs=0.1)]
    alerts, results = drive(frames, **OFF)
    assert l3(alerts) == [] and not results[-1].drowsiness.head_drop


# ---------------------------------------------------------------- what must stay quiet


def test_drooping_alone_is_not_a_microsleep():
    """Narrowed eyes for 20 s (sun, smiling): no deep frame, no stretch."""
    alerts, results = drive(span(0, WARM_S) + span(WARM_S, 20.0, ear=DROOP))
    assert l3(alerts) == [] and microsleeps(results) == 0
    assert max(r.drowsiness.closed_duration for r in results) == 0.0


def test_a_shut_stretch_shorter_than_a_microsleep_after_drooping_is_not_one():
    frames, shut = droop_then_shut(4.0, 0.8)
    alerts, results = drive(frames + span(shut + 0.8, 3.0, ear=DROOP) + span(shut + 3.8, 2.0))
    assert l3(alerts) == [] and microsleeps(results) == 0
    assert max(r.drowsiness.closed_duration for r in results) < 0.9


def test_lids_going_up_and_down_are_not_one_stretch():
    """Drooping 6 s, then 0.5 s shut / 0.2 s narrowed, over and over: each stretch starts from 0."""
    frames = span(0, WARM_S) + span(WARM_S, 6.0, ear=DROOP)
    t = WARM_S + 6.0
    for _ in range(4):
        frames += span(t, 0.5, ear=SHUT) + span(t + 0.5, 0.2, ear=DROOP)
        t += 0.7
    alerts, results = drive(frames)
    assert l3(alerts) == [] and microsleeps(results) == 0
    assert max(r.drowsiness.closed_duration for r in results) < 0.6


def test_single_deep_frames_among_narrowed_ones_are_not_a_stretch():
    """EAR dipping under the deep threshold one frame in three (under min_frac of the closure): nothing to count."""
    frames = span(0, WARM_S)
    frames += [(WARM_S + i / 30.0, {"ear": DROOP if i % 3 else 0.14}) for i in range(round(10 * 30))]
    alerts, results = drive(frames)
    assert l3(alerts) == [] and microsleeps(results) == 0
    assert max(r.drowsiness.closed_duration for r in results) < 0.2  # the first frames, while the closure is young


def test_the_yawn_mask_restarts_the_stretch():
    """Eyes squeezed shut in a yawn after narrowing: masked, as before M76."""
    frames, shut = droop_then_shut(3.0, 3.0, mar=0.8)
    alerts, results = drive(frames)
    assert l3(alerts) == [] and microsleeps(results) == 0
    assert max(r.drowsiness.closed_duration for r in results) < 0.1


def test_lowered_lids_with_the_head_bowed_are_still_looking_down():
    """Head bowed 15 degrees, lids at 0.45 x: not deep with the head bowed (bowed_ear_ratio), so no stretch."""
    frames = span(0, WARM_S) + span(WARM_S, 3.0, ear=DROOP) + span(WARM_S + 3.0, 6.0, ear=0.135, pitch=15.0)
    alerts, results = drive(frames)
    assert l3(alerts) == [] and microsleeps(results) == 0
    assert results[-1].drowsiness.gaze_down


def test_ear_shut_without_the_blendshape_vote_is_not_a_stretch():
    """EAR collapsed while eyeBlink says the lids are up (glare on glasses): not deep, with or without drooping."""
    frames, _ = droop_then_shut(4.0, 3.0, blink=0.2)
    alerts, results = drive(frames)
    assert l3(alerts) == [] and microsleeps(results) == 0


# ---------------------------------------------------------------- configuration


def test_the_default_matches_thresholds_yaml():
    th = load_thresholds()
    assert (
        DrowsinessConfig.from_dict(th["drowsiness"]).microsleep_deep_run_gap_s
        == DrowsinessConfig().microsleep_deep_run_gap_s
    )
    assert th["drowsiness"]["microsleep_deep"]["run_gap_s"] == 0
