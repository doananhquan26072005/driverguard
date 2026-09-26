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


def test_closure_carried_through_head_drop():
    # Eyes closed 0.8 s, then the head drops (eye state unknown): the closure keeps counting.
    a, _ = simulate(20)
    ear = lambda t: 0.08  # noqa: E731
    pitch = lambda t: 40.0 if t >= 20.8 else 0.0  # noqa: E731
    _, s = simulate(3.0, ear=ear, pitch=pitch, analyzer=a, t0=20.0)
    assert s[-1].head_drop and s[-1].eye_closed is None
    assert s[-1].closed_duration == pytest.approx(3.0 - DT, abs=2 * DT)
    assert events(s, "microsleep")
    # Head drop, then the face is lost (slumped out of view): still counting.
    _, s = simulate(1.0, face=const(False), analyzer=a, t0=23.0)
    assert s[-1].closed_duration == pytest.approx(4.0 - DT, abs=2 * DT)
    # Head back up with the eyes open: the episode ends, no blink.
    _, s = simulate(1.0, analyzer=a, t0=24.0)
    assert s[-1].closed_duration == 0.0 and not s[-1].head_drop
    assert not events(s, "blink")


def test_blink_then_head_down_is_not_carried():
    # 0.2 s closure (blink / lids lowering), then looking down at the dashboard.
    a, _ = simulate(20)
    pitch = lambda t: 35.0 if t >= 20.2 else 0.0  # noqa: E731
    _, s = simulate(3.0, ear=const(0.08), pitch=pitch, analyzer=a, t0=20.0)
    assert not any(x.head_drop for x in s)
    assert s[-1].closed_duration == 0.0 and not events(s, "microsleep")


def test_carried_closure_ends_when_head_comes_up_unjudged():
    # Head drop carried, then head up but turned far (eyes still unknown): stop counting.
    a, _ = simulate(20)
    pitch = lambda t: 40.0 if 20.8 <= t < 22.0 else 0.0  # noqa: E731
    yaw = lambda t: 60.0 if t >= 22.0 else 0.0  # noqa: E731
    _, s = simulate(3.0, ear=const(0.08), pitch=pitch, yaw=yaw, analyzer=a, t0=20.0)
    assert any(x.head_drop for x in s)
    assert s[-1].closed_duration == 0.0 and not s[-1].head_drop


def test_head_drop_config_from_yaml_dict():
    cfg = DrowsinessConfig.from_dict({"head_drop": {"carry_min_closed_s": 0.8}})
    assert cfg.head_drop_carry_min_closed_s == 0.8


# ---------------------------------------------------------------- microsleep mask (yawn / talking)

CLOSED = 0.08
WIDE = 0.8  # mouth wide open (yawn)


def test_eyes_shut_during_yawn_is_not_a_microsleep():
    # Yawn 3-7 s with the eyes squeezed shut 3.5-7.5 s (reopen inside the hold time).
    a, _ = simulate(20)
    _, s = simulate(
        12,
        ear=lambda t: CLOSED if 23.5 <= t < 27.5 else OPEN,
        mar=lambda t: WIDE if 23.0 <= t < 27.0 else 0.05,
        analyzer=a,
        t0=20.0,
    )
    assert not events(s, "microsleep")
    assert max(x.closed_duration for x in s) < 0.5
    assert any(x.closure_masked for x in s)
    assert len(events(s, "yawn")) == 1  # the yawn itself still counts
    assert s[-1].perclos_60s == 0.0  # squeezing the eyes while yawning is not fatigue


def test_perclos_mask_can_be_turned_off():
    a, _ = simulate(20, analyzer=DrowsinessAnalyzer(DrowsinessConfig(perclos_use_mask=False)))
    _, s = simulate(
        12,
        ear=lambda t: CLOSED if 23.5 <= t < 27.5 else OPEN,
        mar=lambda t: WIDE if 23.0 <= t < 27.0 else 0.05,
        analyzer=a,
        t0=20.0,
    )
    assert s[-1].perclos_60s > 0.1


def test_eyes_stay_closed_after_yawn_counts_from_end_of_hold():
    # Yawn 23-26 s, eyes closed from 24 s and never reopen: counting starts after the
    # 1.5 s hold (27.5 s), microsleep at 28.5 s.
    a, _ = simulate(20)
    _, s = simulate(
        12,
        ear=lambda t: CLOSED if t >= 24.0 else OPEN,
        mar=lambda t: WIDE if 23.0 <= t < 26.0 else 0.05,
        analyzer=a,
        t0=20.0,
    )
    assert events(s, "microsleep")[0] == pytest.approx(28.5, abs=3 * DT)
    assert s[-1].closed_duration == pytest.approx(32.0 - 27.5, abs=3 * DT)
    assert not events(s, "blink")


def test_slack_jaw_in_sleep_is_not_masked_forever():
    # Mouth hangs open (no yawn end) with the eyes closed: the mask stops after
    # max_open_s (8 s) + hold (1.5 s), then the microsleep fires.
    a, _ = simulate(20)
    _, s = simulate(15, ear=const(CLOSED), mar=const(WIDE), analyzer=a, t0=20.0)
    ms = events(s, "microsleep")
    assert len(ms) == 1
    assert ms[0] == pytest.approx(20.0 + 8.0 + 1.5 + 1.0, abs=3 * DT)


def test_talking_with_short_eye_closures_is_masked():
    # Talking: MAR keeps moving; the eyes close 2 s while talking.
    talk = pulses(0.4, 0.2, 0.35, 0.05)
    a, _ = simulate(20, mar=talk)
    _, s = simulate(6, ear=lambda t: CLOSED if 22.0 <= t < 24.0 else OPEN, mar=talk, analyzer=a, t0=20.0)
    assert not events(s, "microsleep")
    assert all(x.closed_duration == 0.0 for x in s)


def test_still_mouth_microsleep_is_not_masked():
    # Asleep: mouth still (tiny MAR noise), eyes closed 2 s -> microsleep as usual.
    a, _ = simulate(20)
    _, s = simulate(
        5,
        ear=lambda t: CLOSED if 21.0 <= t < 23.0 else OPEN,
        mar=lambda t: 0.05 + 0.01 * ((t * FPS) % 2),
        analyzer=a,
        t0=20.0,
    )
    assert len(events(s, "microsleep")) == 1
    assert not any(x.closure_masked for x in s)


def test_talking_mask_can_be_turned_off():
    cfg = DrowsinessConfig.from_dict({"microsleep_mask": {"talk_min_swings": 0}})
    talk = pulses(0.4, 0.2, 0.35, 0.05)
    a, _ = simulate(20, mar=talk, analyzer=DrowsinessAnalyzer(cfg))
    _, s = simulate(6, ear=lambda t: CLOSED if 22.0 <= t < 24.0 else OPEN, mar=talk, analyzer=a, t0=20.0)
    assert len(events(s, "microsleep")) == 1


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


def test_pitch_baseline_not_dragged_by_frequent_nods():
    # Very drowsy: head 18 deg down with the eyes closed 60 % of the time. The usual pitch
    # must stay at the eyes-open pose (a plain median would move to 18 deg).
    a, _ = simulate(10)
    down = lambda t: (t % 2.5) < 1.5  # noqa: E731
    _, s = simulate(
        60,
        ear=lambda t: 0.08 if down(t) else OPEN,
        pitch=lambda t: 18.0 if down(t) else 0.0,
        analyzer=a,
        t0=10.0,
    )
    assert abs(s[-1].pitch_baseline) < 1.0


def test_pose_baseline_bootstraps_and_follows_posture_with_open_eyes():
    # Starts learning at once, then follows a lasting posture change made with the eyes open.
    a, s = simulate(1.0, pitch=const(8.0))
    assert s[-1].pitch_baseline == pytest.approx(8.0)
    _, s = simulate(80, pitch=const(-5.0), analyzer=a, t0=1.0)
    assert s[-1].pitch_baseline == pytest.approx(-5.0)


def test_config_from_yaml_dict():
    cfg = DrowsinessConfig.from_dict({"microsleep_min_s": 1.5, "eye": {"close_ratio": 0.6}, "nod": {"max_s": 3}})
    assert cfg.microsleep_min_s == 1.5
    assert cfg.eye_close_ratio == 0.6
    assert cfg.nod_max_s == 3


def test_describe_events():
    _, states = simulate(20, ear=lambda t: 0.08 if 10.0 <= t < 11.5 else OPEN)
    fired = next(s for s in states if "microsleep" in s.events)
    assert describe_events(fired) == ["[DROWSY] microsleep: eyes closed 1.0 s"]


def test_sleep_right_after_yawn_with_head_drop_reaches_microsleep():
    # Yawn 22-25 s, eyes shut from 24 s, head drops at 26 s (inside the 1.5 s hold) and stays
    # down: the closure is carried and counted from the drop, not hidden by the yawn mask.
    a, _ = simulate(20)
    _, s = simulate(
        10,
        ear=lambda t: CLOSED if t >= 24.0 else OPEN,
        mar=lambda t: WIDE if 22.0 <= t < 25.0 else 0.05,
        pitch=lambda t: 40.0 if t >= 26.0 else 0.0,
        analyzer=a,
        t0=20.0,
    )
    assert any(x.head_drop for x in s)
    assert events(s, "microsleep")[0] == pytest.approx(27.0, abs=3 * DT)
    assert s[-1].closed_duration >= 1.5  # risk engine: L3


def test_sleep_while_talking_with_head_drop_reaches_microsleep():
    talk = pulses(0.4, 0.2, 0.35, 0.05)
    a, _ = simulate(22, mar=talk)
    _, s = simulate(
        5,
        ear=const(CLOSED),
        mar=lambda t: talk(t) if t < 22.2 else 0.05,
        pitch=lambda t: 40.0 if t >= 23.0 else 0.0,
        analyzer=a,
        t0=22.0,
    )
    assert any(x.head_drop for x in s)
    assert events(s, "microsleep")
    assert s[-1].closed_duration >= 1.5


def test_face_lost_mid_sentence_is_no_microsleep():
    # PR review: the talking mask is not extended while the face is lost (MAR unknown).
    # That cannot fake a microsleep: with the eyes unknown and no head drop seen, the
    # closure ends after max_gap_s instead of counting.
    talk = pulses(0.4, 0.2, 0.35, 0.05)
    a, _ = simulate(22, mar=talk)
    _, s = simulate(4, ear=const(CLOSED), mar=talk, face=lambda t: t < 22.3, analyzer=a, t0=22.0)
    assert not events(s, "microsleep")
    assert all(x.closed_duration == 0.0 for x in s)


# ---------------------------------------------------------------- PERCLOS mask, deep closure, face_conf


def talking_mar(t):
    return 0.1 + 0.2 * ((t * 3) % 1.0 < 0.5)  # mouth opens / closes 3x per second


def test_perclos_skips_squinting_while_talking():
    a, _ = simulate(15)
    _, s = simulate(40, ear=pulses(2.0, 0.6, CLOSED, OPEN), mar=talking_mar, analyzer=a, t0=15.0)
    assert all(x.closure_masked for x in s[60:])
    assert s[-1].perclos_60s < 0.05 and not events(s, "perclos_high")


def test_perclos_still_counts_closures_with_a_still_mouth():
    a, _ = simulate(15)
    _, s = simulate(40, ear=pulses(2.0, 0.6, CLOSED, OPEN), analyzer=a, t0=15.0)
    assert s[-1].perclos_60s > 0.2 and events(s, "perclos_high")


def test_narrowed_eyes_are_not_a_microsleep():
    # Baseline 0.30: close below 0.195, reopen above 0.225. Looking down / squinting: one dip
    # to 0.19, then EAR stays at 0.21 (0.7 x baseline) for 4 s, inside the hysteresis band.
    a, _ = simulate(15)
    _, s = simulate(6, ear=lambda t: 0.19 if 16 <= t < 16.2 else (0.21 if 16 <= t < 20 else OPEN), analyzer=a, t0=15.0)
    assert any(x.eye_closed for x in s)  # the hysteresis still holds the closure episode
    assert not events(s, "microsleep") and max(x.closed_duration for x in s) == 0.0


def test_narrowed_eyes_after_blinks_are_not_perclos():
    # Squinting into the sun: EAR 0.74 x baseline (never below close_ratio 0.65) with normal
    # blinks. After each blink the hysteresis holds "closed" (0.74 < open_ratio 0.75), but
    # PERCLOS judges each frame on its own: only the blinks count.
    a, _ = simulate(15)
    _, s = simulate(60, ear=pulses(4.0, 0.15, CLOSED, 0.74 * OPEN), analyzer=a, t0=15.0)
    assert sum(1 for x in s if x.eye_closed) > 0.8 * len(s)
    assert s[-1].perclos_60s == pytest.approx(0.15 / 4.0, abs=0.01)
    assert not events(s, "perclos_high")


def test_cnn_unsure_after_blinks_is_not_perclos():
    # CNN p_closed 0.5 (between cnn_open 0.4 and cnn_closed 0.6) after each blink.
    a = DrowsinessAnalyzer()
    for i in range(round(60 * FPS)):
        t = i * DT
        p = 0.95 if (t % 4.0) < 0.15 else 0.5
        f = FrameFeatures(i, t, True, 1.0, ear=OPEN, mar=0.05, pitch=0.0, yaw=0.0, roll=0.0, p_closed=p)
        s = a.update(f)
    assert s.perclos_60s == pytest.approx(0.15 / 4.0, abs=0.01)


def test_forget_since_drops_the_rest_and_keeps_what_came_before():
    a, _ = simulate(60, mar=lambda t: WIDE if 10 <= t < 13 else 0.05)  # driving: one yawn
    rest_yawn = lambda t: WIDE if 100 <= t < 103 else 0.05  # noqa: E731
    _, s = simulate(150, ear=const(CLOSED), mar=rest_yawn, analyzer=a, t0=60.0)  # parked, eyes closed
    assert s[-1].perclos_60s > 0.9 and s[-1].closed_duration > 60 and s[-1].yawn_count_10min == 2
    a.forget_since(60.0)
    _, s = simulate(2, analyzer=a, t0=210.0)
    assert s[-1].perclos_60s == 0.0 and s[-1].closed_duration == 0.0
    assert s[-1].yawn_count_10min == 1  # the yawn while driving stays
    assert s[-1].ear_open_baseline == pytest.approx(0.28)  # closed-eye EAR of the rest is gone


def test_deep_closure_after_narrowing_counts_from_its_start():
    # Eyes narrow for 0.6 s, then shut: once deep enough, the whole closure counts.
    a, _ = simulate(15)
    ear = lambda t: 0.19 if 16 <= t < 16.6 else (CLOSED if 16.6 <= t < 19 else OPEN)  # noqa: E731
    _, s = simulate(5, ear=ear, analyzer=a, t0=15.0)
    ms = events(s, "microsleep")
    assert len(ms) == 1 and ms[0] == pytest.approx(17.2, abs=0.1)  # 16 + 1.0 s, shallow half included
    assert max(x.closed_duration for x in s) == pytest.approx(3.0, abs=0.1)


def test_cnn_uncertain_closure_is_not_a_microsleep():
    def run(p):
        a = DrowsinessAnalyzer()
        for i in range(round(4 * FPS)):
            t = i * DT
            closed = 1.0 <= t < 3.5
            f = FrameFeatures(i, t, True, 1.0, ear=0.1 if closed else OPEN, mar=0.05, pitch=0.0, yaw=0.0, roll=0.0)
            if closed:
                f = FrameFeatures(**{**f.__dict__, "p_closed": p})
            s = a.update(f)
            if s.events and "microsleep" in s.events:
                return True
        return False

    assert run(0.95)  # sure: microsleep
    assert not run(0.65)  # above cnn_closed (0.6) but not firmly shut


def test_partial_face_is_not_measured():
    a, _ = simulate(15)
    before = a.ear_baseline(15.0)
    for i in range(round(40 * FPS)):  # 40 s of "closed" eyes on a face half out of frame
        t = 15.0 + i * DT
        s = a.update(
            FrameFeatures(i, t, True, 0.6, face_reliable=False, ear=CLOSED, mar=WIDE, pitch=0.0, yaw=0.0, roll=0.0)
        )
    assert s.eye_closed is None and not s.events and s.perclos_60s == 0.0
    assert s.yawn_count_10min == 0 and a.ear_baseline(t) == pytest.approx(before)


def test_head_drop_carry_goes_on_when_the_face_slides_out_of_frame():
    a, _ = simulate(10)
    s = None
    for i in range(round(3 * FPS)):
        t = 10.0 + i * DT
        if t < 11.0:  # eyes shut, head still up
            f = FrameFeatures(i, t, True, 1.0, ear=CLOSED, mar=0.05, pitch=0.0, yaw=0.0, roll=0.0)
        else:  # slumps: face partly out of frame
            f = FrameFeatures(i, t, True, 0.5, face_reliable=False, ear=0.3, mar=0.05, pitch=40.0, yaw=0.0, roll=0.0)
        s = a.update(f)
    assert s.head_drop and s.closed_duration >= 1.9


def test_blink_rate_min_span_from_config():
    # One blink in the first 2 s: divided by the configured minimum span, not by 2 s.
    ear = lambda t: CLOSED if 1.0 <= t < 1.2 else OPEN  # noqa: E731
    _, s = simulate(2, ear=ear)
    assert s[-1].blink_rate == pytest.approx(6.0)  # 1 / 10 s * 60
    _, s = simulate(2, ear=ear, analyzer=DrowsinessAnalyzer(DrowsinessConfig(blink_rate_min_span_s=20.0)))
    assert s[-1].blink_rate == pytest.approx(3.0)


# ---------------------------------------------------------------- 26/09: blendshape vote for deep closure


def closure_with_blink(blink, deep_blink):
    """15 s open, then EAR firmly shut (0.08) for 2 s with MediaPipe eyeBlink = `blink`."""
    a = DrowsinessAnalyzer(DrowsinessConfig(microsleep_deep_blink=deep_blink))
    states = []
    for i in range(round(18 * FPS)):
        t = i * DT
        shut = 15.0 <= t < 17.0
        f = FrameFeatures(i, t, True, 1.0, ear=0.08 if shut else OPEN, mar=0.05, pitch=0.0, yaw=0.0, roll=0.0,
                          eye_blink=blink if shut else 0.05)  # fmt: skip
        states.append(a.update(f))
    return states


def test_blendshape_vote_off_by_default():
    assert events(closure_with_blink(0.1, 0.0), "microsleep")  # EAR alone decides


def test_blendshape_vote_confirms_a_real_closure():
    s = closure_with_blink(0.9, 0.5)
    assert len(events(s, "microsleep")) == 1
    assert max(x.closed_duration for x in s) == pytest.approx(2.0, abs=2 * DT)


def test_blendshape_vote_rejects_ear_collapse_with_open_eyes():
    # Glare on glasses / head tilted down: EAR looks shut, the blendshape sees open eyes.
    s = closure_with_blink(0.1, 0.5)
    assert not events(s, "microsleep") and max(x.closed_duration for x in s) == 0.0
    assert any(x.eye_closed for x in s)  # still a closure for blinks / PERCLOS: only microsleep is gated


def test_blendshape_vote_ignored_when_blendshapes_are_off():
    a = DrowsinessAnalyzer(DrowsinessConfig(microsleep_deep_blink=0.5))
    _, states = simulate(20, ear=lambda t: 0.08 if 10.0 <= t < 11.5 else OPEN, analyzer=a)  # eye_blink None
    assert len(events(states, "microsleep")) == 1


def talking_closure(ear_closed, talk_spares_deep, blink=None, deep_blink=0.0):
    """Lips keep moving (talking mask on) while the eyes close for 2 s."""
    cfg = DrowsinessConfig(microsleep_mask_talk_spares_deep=talk_spares_deep, microsleep_deep_blink=deep_blink)
    a = DrowsinessAnalyzer(cfg)
    talk = pulses(0.4, 0.2, 0.35, 0.05)
    states = []
    for i in range(round(26 * FPS)):
        t = i * DT
        shut = 22.0 <= t < 24.0
        f = FrameFeatures(i, t, True, 1.0, ear=ear_closed if shut else OPEN, mar=talk(t), pitch=0.0, yaw=0.0,
                          roll=0.0, eye_blink=None if blink is None else (blink if shut else 0.05))  # fmt: skip
        states.append(a.update(f))
    return states


def test_talk_spares_deep_closure_confirmed_by_the_blendshape():
    assert not events(talking_closure(0.08, False, blink=0.9, deep_blink=0.5), "microsleep")  # off: masked
    assert len(events(talking_closure(0.08, True, blink=0.9, deep_blink=0.5), "microsleep")) == 1  # shut: counted


def test_talk_spares_deep_still_masks_squinting():
    # Narrowed eyes while talking (0.6 x baseline: closed, not deep) stay masked.
    assert not events(talking_closure(0.6 * OPEN, True, blink=0.9, deep_blink=0.5), "microsleep")


def test_talk_spares_deep_needs_the_blendshape():
    # EAR shut but eyeBlink says open (glare while talking): still masked.
    assert not events(talking_closure(0.08, True, blink=0.1, deep_blink=0.5), "microsleep")
    # Blendshapes off: EAR alone does not lift the mask (it let talking fake microsleeps on YawDD).
    assert not events(talking_closure(0.08, True, blink=None, deep_blink=0.5), "microsleep")
