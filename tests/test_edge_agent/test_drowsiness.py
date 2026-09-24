import pytest

from edge_agent.analysis.drowsiness import DrowsinessAnalyzer, DrowsinessConfig, describe_events
from edge_agent.perception.features import FrameFeatures

FPS = 30
DT = 1.0 / FPS
OPEN = 0.30


def const(v):
    return lambda t: v


def pulses(period, width, low, high, start=0.0):
    """high, dropping to `low` for `width` seconds every `period` seconds (after `start`)."""

    def f(t):
        if t < start:
            return high
        return low if (t - start) % period < width else high

    return f


def simulate(
    seconds, ear=const(OPEN), mar=const(0.05), pitch=const(0.0), yaw=const(0.0), face=None, analyzer=None, t0=0.0
):
    """Run fake frames through the analyzer. Returns (analyzer, list of states)."""
    a = analyzer or DrowsinessAnalyzer()
    states = []
    for i in range(round(seconds * FPS)):
        t = t0 + i * DT
        if face is not None and not face(t):
            f = FrameFeatures(i, t, False, 0.0)
        else:
            f = FrameFeatures(i, t, True, 1.0, ear=ear(t), mar=mar(t), pitch=pitch(t), yaw=yaw(t), roll=0.0)
        states.append(a.update(f))
    return a, states


def events(states, name):
    return [s.timestamp for s in states if name in s.events]


# ---------------------------------------------------------------- eyes


def test_alert_driver_has_no_events():
    _, states = simulate(60)
    last = states[-1]
    assert last.perclos_60s == 0.0 and last.closed_duration == 0.0
    assert last.blink_rate == 0.0
    assert all(not s.events for s in states)


def test_blinks_counted_and_rate_per_minute():
    # 15 blinks / min, 0.15 s each
    _, states = simulate(60, ear=pulses(4.0, 0.15, 0.08, OPEN, start=1.0))
    assert len(events(states, "blink")) == 15
    assert states[-1].blink_rate == pytest.approx(15, abs=1)
    assert states[-1].perclos_60s == pytest.approx(15 * 0.15 / 60, abs=0.01)
    assert not events(states, "microsleep")


def test_microsleep_fires_once_and_is_not_a_blink():
    _, states = simulate(20, ear=lambda t: 0.08 if 10.0 <= t < 11.5 else OPEN)
    assert len(events(states, "microsleep")) == 1
    assert not events(states, "blink")
    peak = max(s.closed_duration for s in states)
    assert peak == pytest.approx(1.5, abs=2 * DT)
    assert events(states, "microsleep")[0] == pytest.approx(11.0, abs=2 * DT)


def test_perclos_high_after_coverage_only():
    # Eyes closed 0.8 s every 4 s = 20 % closed.
    _, states = simulate(70, ear=pulses(4.0, 0.8, 0.08, OPEN))
    fired = events(states, "perclos_high")
    assert len(fired) == 1
    assert fired[0] >= 30.0  # needs 30 s of eye data first
    assert states[-1].perclos_60s == pytest.approx(0.2, abs=0.02)


def test_perclos_rearms_after_recovery():
    cfg = DrowsinessConfig(perclos_window_s=20, perclos_min_coverage_s=10)
    drowsy = pulses(4.0, 0.8, 0.08, OPEN)
    a, s1 = simulate(30, ear=drowsy, analyzer=DrowsinessAnalyzer(cfg))
    a, s2 = simulate(30, analyzer=a, t0=30.0)  # alert again, PERCLOS decays
    a, s3 = simulate(30, ear=drowsy, analyzer=a, t0=60.0)
    assert len(events(s1, "perclos_high")) == 1
    assert not events(s2, "perclos_high")
    assert len(events(s3, "perclos_high")) == 1


@pytest.mark.parametrize("open_ear", [0.21, 0.36])
def test_eye_threshold_adapts_to_the_driver(open_ear):
    # Narrow eyes (0.21) must not read as closed; wide eyes (0.36) half-closing to
    # 0.20 must read as closed even though 0.20 is a normal open value for others.
    a, states = simulate(30, ear=const(open_ear))
    assert states[-1].perclos_60s == 0.0
    assert states[-1].ear_open_baseline == pytest.approx(open_ear, abs=0.01)
    _, states = simulate(1.0, ear=const(0.55 * open_ear), analyzer=a, t0=30.0)
    assert states[-1].eye_closed is True


def test_eyes_not_judged_when_head_turned_or_down():
    # Looking at the side mirror / dashboard: EAR drops but must not count as closed.
    a, _ = simulate(20)
    _, states = simulate(5, ear=const(0.1), yaw=const(50.0), analyzer=a, t0=20.0)
    assert all(s.eye_closed is None for s in states[-60:])
    assert states[-1].closed_duration == 0.0
    b, _ = simulate(20)
    _, states = simulate(5, ear=const(0.1), pitch=const(35.0), analyzer=b, t0=20.0)
    assert states[-1].closed_duration == 0.0 and not events(states, "microsleep")


def test_short_face_dropout_keeps_closure_long_dropout_ends_it():
    closed = const(0.08)
    a, _ = simulate(10)
    _, s = simulate(2.0, ear=closed, face=lambda t: not (10.8 <= t < 11.0), analyzer=a, t0=10.0)
    assert s[-1].closed_duration == pytest.approx(2.0 - DT, abs=2 * DT)
    b, _ = simulate(10)
    _, s = simulate(3.0, ear=closed, face=lambda t: not (10.5 <= t < 12.0), analyzer=b, t0=10.0)
    assert s[-1].closed_duration < 1.0  # new episode after the long gap
    assert not events(s, "blink")


# ---------------------------------------------------------------- yawn


def test_yawn_counted_once():
    _, states = simulate(10, mar=lambda t: 0.8 if 3.0 <= t < 7.0 else 0.05)
    assert len(events(states, "yawn")) == 1
    assert events(states, "yawn")[0] == pytest.approx(4.5, abs=2 * DT)
    assert states[-1].yawn_count_10min == 1


def test_talking_is_not_a_yawn():
    _, states = simulate(20, mar=pulses(0.6, 0.3, 0.7, 0.2))
    assert not events(states, "yawn")


def test_yawn_window_is_10_minutes():
    a, _ = simulate(5, mar=lambda t: 0.8 if 1.0 <= t < 4.0 else 0.05)
    _, states = simulate(1, analyzer=a, t0=500.0)
    assert states[-1].yawn_count_10min == 1
    _, states = simulate(1, analyzer=a, t0=605.0)
    assert states[-1].yawn_count_10min == 0


# ---------------------------------------------------------------- nod


def dip(start, length, depth=25.0):
    return lambda t: depth if start <= t < start + length else 0.0


def test_drowsy_nod_with_eyes_closed():
    closed_during_dip = lambda t: 0.08 if 20.0 <= t < 20.8 else OPEN  # noqa: E731
    _, states = simulate(25, pitch=dip(20.0, 0.8), ear=closed_during_dip)
    assert len(events(states, "nod")) == 1
    assert states[-1].nod_count_5min == 1


def test_glance_at_dashboard_with_open_eyes_is_not_a_nod():
    _, states = simulate(25, pitch=dip(20.0, 0.8))
    assert not events(states, "nod")


def test_sustained_head_down_is_not_a_nod():
    _, states = simulate(30, pitch=dip(20.0, 5.0), ear=lambda t: 0.08 if 20.0 <= t < 25.0 else OPEN)
    assert not events(states, "nod")


def test_nod_window_is_5_minutes():
    a, _ = simulate(25, pitch=dip(20.0, 0.8), ear=lambda t: 0.08 if 20.0 <= t < 20.8 else OPEN)
    _, s = simulate(1, analyzer=a, t0=250.0)
    assert s[-1].nod_count_5min == 1
    _, s = simulate(1, analyzer=a, t0=330.0)
    assert s[-1].nod_count_5min == 0


def test_camera_pitch_offset_does_not_fake_nods():
    # Camera mounted low: driver's normal pitch reads as 20 deg.
    _, states = simulate(40, pitch=const(20.0), ear=pulses(4.0, 0.15, 0.08, OPEN))
    assert not events(states, "nod")


# ---------------------------------------------------------------- misc


def test_config_from_yaml_dict():
    cfg = DrowsinessConfig.from_dict({"microsleep_min_s": 1.5, "eye": {"close_ratio": 0.6}, "nod": {"max_s": 3}})
    assert cfg.microsleep_min_s == 1.5
    assert cfg.eye_close_ratio == 0.6
    assert cfg.nod_max_s == 3


def test_describe_events():
    _, states = simulate(20, ear=lambda t: 0.08 if 10.0 <= t < 11.5 else OPEN)
    fired = next(s for s in states if "microsleep" in s.events)
    assert describe_events(fired) == ["[DROWSY] microsleep: eyes closed 1.0 s"]
