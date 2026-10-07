"""v2 drowsiness signals of block 7 with fake sequences: slow blinks, brow raise (nod vs bow is in
test_drowsiness.py). Sources and temporary thresholds: docs/research/2026-10-01-blink-nod-brow.md."""

from dataclasses import replace

import pytest

from edge_agent.analysis.drowsiness import DrowsinessAnalyzer
from edge_agent.decision.risk_engine import RiskEngine
from edge_agent.perception.features import FrameFeatures
from tests.test_edge_agent.test_decision import C0, D0, X0

OPEN, SHUT = 0.30, 0.08


def blinks(period, close_s, hold_s, reopen_s, start=0.0, until=1e9):
    """EAR of periodic blinks: linear close, held shut, linear reopen."""

    def ear(t):
        if t < start or t >= until:
            return OPEN
        x = (t - start) % period
        if x < close_s:
            return OPEN - (OPEN - SHUT) * x / close_s
        if x < close_s + hold_s:
            return SHUT
        if x < close_s + hold_s + reopen_s:
            return SHUT + (OPEN - SHUT) * (x - close_s - hold_s) / reopen_s
        return OPEN

    return ear


ALERT = {"close_s": 0.06, "hold_s": 0.03, "reopen_s": 0.15}  # ~Caffier 2003, alert
DROWSY = {"close_s": 0.08, "hold_s": 0.10, "reopen_s": 0.30}  # reopening ~x2


def run(seconds, ear, fps=30, brow=None, mar=None, analyzer=None, t0=0.0):
    a = analyzer or DrowsinessAnalyzer()
    states = []
    for i in range(round(seconds * fps)):
        t = t0 + i / fps
        f = FrameFeatures(
            i,
            t,
            True,
            1.0,
            ear=ear(t),
            mar=0.05 if mar is None else mar(t),
            pitch=0.0,
            yaw=0.0,
            roll=0.0,
            brow_up=None if brow is None else brow(t),
        )
        states.append(a.update(f))
    return a, states


# ---------------------------------------------------------------- slow blinks


@pytest.mark.parametrize("fps", [30, 15])
def test_reopening_time_is_measured_between_frames(fps):
    # Aperture 0.8 = EAR 0.261 (closed ref 0.35 x 0.30): 82 % of a linear reopening from 0.08.
    _, s = run(80, blinks(4.0, **ALERT, start=1.0), fps=fps)
    assert s[-1].reopen_s == pytest.approx(0.82 * ALERT["reopen_s"], abs=0.04 if fps == 30 else 0.06)
    _, s = run(80, blinks(4.0, **DROWSY, start=1.0), fps=fps)
    assert s[-1].reopen_s == pytest.approx(0.82 * DROWSY["reopen_s"], abs=0.04 if fps == 30 else 0.06)


def test_alert_blinks_give_no_slow_blink_score():
    _, s = run(180, blinks(4.0, **ALERT, start=1.0))
    assert s[-1].reopen_ratio == pytest.approx(1.0, abs=0.1)
    assert s[-1].blink_time_frac < 0.10
    assert s[-1].slow_blink_score == 0.0


@pytest.mark.parametrize("fps", [30, 15])
def test_reopening_slower_than_the_drivers_own_start_raises_the_score(fps):
    alert = blinks(4.0, **ALERT, start=1.0, until=100.0)
    a, _ = run(100, alert, fps=fps)  # 25 alert blinks: the driver's own reopening time
    _, s = run(90, blinks(4.0, **DROWSY, start=100.0), fps=fps, analyzer=a, t0=100.0)
    assert s[-1].reopen_ratio >= 1.7
    assert s[-1].slow_blink_score == pytest.approx(1.0)


def test_blink_time_fraction_reaches_16_percent():
    # 25 slow blinks / min, ~0.48 s each from the start of closing to 80 % open: ~20 % of the time
    slow = {"close_s": 0.10, "hold_s": 0.12, "reopen_s": 0.30}
    _, s = run(90, blinks(2.4, **slow, start=1.0))
    assert s[-1].blink_time_frac >= 0.16
    assert s[-1].slow_blink_score == pytest.approx(1.0)


def test_no_slow_blink_score_before_perclos_coverage():
    _, s = run(20, blinks(2.4, close_s=0.1, hold_s=0.12, reopen_s=0.3, start=1.0))
    assert s[-1].slow_blink_score == 0.0  # 20 s < drowsiness.perclos_min_coverage_s


def test_enrolled_closed_eye_sets_the_aperture_scale():
    a = DrowsinessAnalyzer()
    a.set_profile(OPEN, 0.05, 0.0, 0.0, ear_closed=SHUT)
    _, s = run(80, blinks(4.0, **ALERT, start=1.0), analyzer=a)
    # aperture 0.8 between 0.08 and 0.30 = EAR 0.256: 80 % of the reopening
    assert s[-1].reopen_s == pytest.approx(0.80 * ALERT["reopen_s"], abs=0.04)


def test_rest_forgets_the_blinks_since_the_stop():
    a, _ = run(80, blinks(2.4, close_s=0.1, hold_s=0.12, reopen_s=0.3, start=1.0))
    a.forget_since(0.0)
    _, s = run(1, lambda t: OPEN, analyzer=a, t0=80.0)
    assert s[-1].blink_time_frac == 0.0 and s[-1].reopen_s is None


# ---------------------------------------------------------------- brow raise


def drooping(t):
    return 0.22 if t >= 20.0 else OPEN  # 0.73 x baseline: drooping, not closed (close at 0.65)


def raised_at(start, length, high=0.55, rest=0.15):
    return lambda t: high if start <= t < start + length else rest


def test_brows_raised_while_the_eyes_droop_count():
    _, s = run(30, drooping, brow=raised_at(22.0, 1.5))
    assert [round(x.timestamp) for x in s if "brow_raise" in x.events] == [22]
    assert s[-1].brow_raise_count_5min == 1


def test_brows_raised_with_wide_open_eyes_are_surprise_not_drowsiness():
    _, s = run(30, lambda t: OPEN, brow=raised_at(22.0, 1.5))
    assert s[-1].brow_raise_count_5min == 0


def test_short_brow_flash_does_not_count():
    _, s = run(30, drooping, brow=raised_at(22.0, 0.3))
    assert s[-1].brow_raise_count_5min == 0


def test_brows_raised_while_yawning_do_not_count():
    yawn = lambda t: 0.7 if 21.5 <= t < 25.0 else 0.05  # noqa: E731
    _, s = run(30, drooping, brow=raised_at(22.0, 2.0), mar=yawn)
    assert s[-1].brow_raise_count_5min == 0


def test_enrolled_resting_brow_is_the_reference():
    """A driver whose brows rest high: 0.55 is not raised for them (resting 0.45 + 0.2 = 0.65)."""
    a = DrowsinessAnalyzer()
    a.set_profile(OPEN, 0.05, 0.0, 0.0, ear_closed=SHUT, brow_neutral=0.45)
    _, s = run(30, drooping, brow=raised_at(22.0, 1.5), analyzer=a)
    assert s[-1].brow_raise_count_5min == 0
    b = DrowsinessAnalyzer()
    b.set_profile(OPEN, 0.05, 0.0, 0.0, ear_closed=SHUT, brow_neutral=0.15)
    _, s = run(30, drooping, brow=raised_at(22.0, 1.5), analyzer=b)
    assert s[-1].brow_raise_count_5min == 1


def test_no_blendshapes_no_brow_signal():
    _, s = run(30, drooping)
    assert s[-1].brow_raise_count_5min == 0


# ---------------------------------------------------------------- drowsy_score terms


def test_new_terms_enter_drowsy_score():
    engine = RiskEngine()
    d = replace(D0, slow_blink_score=1.0, brow_raise_count_5min=3)
    score, terms = engine.drowsy_score(d, C0, None)
    assert terms[4:] == (1.0, 1.0)
    assert score == pytest.approx(20.0)  # weight_slow_blink 10 + weight_brow 10 (temporary)
    assert engine.assess(d, X0, C0).level == 0  # alone they stay under L1 (40)


# ---------------------------------------------------------------- per-driver eyeBlink vote


def lowered_lids(seconds, blink, ratio, blink_closed=0.70, fps=30):
    """Lids at 0.3 x the open EAR with this eyeBlink for `seconds`, driver enrolled with blink_closed."""
    a = DrowsinessAnalyzer(replace(DrowsinessAnalyzer().config, microsleep_deep_enrolled_blink_ratio=ratio))
    a.set_profile(OPEN, 0.05, 0.0, 0.0, ear_closed=SHUT, blink_closed=blink_closed)
    states = []
    for i in range(round((5 + seconds) * fps)):
        t = i / fps
        shut = t >= 5.0
        f = FrameFeatures(i, t, True, 1.0, ear=0.3 * OPEN if shut else OPEN, mar=0.05, pitch=0.0, yaw=0.0)
        states.append(a.update(replace(f, eye_blink=blink if shut else 0.05)))
    return states


def test_deep_blink_vote_is_the_fixed_one_unless_the_enrolled_ratio_is_on():
    from edge_agent.analysis.drowsiness.eyes import deep_blink_vote

    cfg = DrowsinessAnalyzer().config
    assert cfg.microsleep_deep_enrolled_blink_ratio == 0.0  # off by default: it lost real microsleeps on FL3D
    assert deep_blink_vote(cfg, 0.70) == cfg.microsleep_deep_blink
    on = replace(cfg, microsleep_deep_enrolled_blink_ratio=0.85)
    assert deep_blink_vote(on, None) == cfg.microsleep_deep_blink  # not enrolled, or no blendshapes
    assert deep_blink_vote(on, 0.70) == pytest.approx(0.595)
    assert deep_blink_vote(on, 0.40) == cfg.microsleep_deep_blink  # never below the fixed vote
    assert deep_blink_vote(replace(on, microsleep_deep_blink=0.0), 0.70) == 0.0  # vote off stays off


def test_enrolled_ratio_keeps_lowered_lids_from_counting_as_a_deep_closure():
    # eyeBlink 0.55 (looking down at a phone) against 0.70 with this driver's eyes shut
    assert max(s.closed_duration for s in lowered_lids(3, blink=0.55, ratio=0.0)) > 2.5
    assert max(s.closed_duration for s in lowered_lids(3, blink=0.55, ratio=0.85)) == 0.0
    off = [ev for s in lowered_lids(3, blink=0.55, ratio=0.85) for ev in s.events]
    assert "microsleep" not in off


def test_enrolled_ratio_still_counts_the_drivers_shut_eyes():
    states = lowered_lids(3, blink=0.68, ratio=0.85)
    assert max(s.closed_duration for s in states) > 2.5
    assert "microsleep" in [ev for s in states for ev in s.events]
