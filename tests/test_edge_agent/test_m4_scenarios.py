"""M4 acceptance: the whole decision chain (blocks 7-12) gives the right L0-L3 per scenario.

Uses the real config/thresholds.yaml and fake 30 FPS feature sequences, no video. Driver
enrollment is off by default (self-learnt baselines, as in the evaluation tools); its own
scenarios are in test_enrollment.py.
"""

import pytest

from edge_agent.config import load_thresholds
from edge_agent.context.can_sim import CanSimulator, scenario_from_dict
from edge_agent.decision.pipeline import DecisionPipeline
from edge_agent.perception.features import FrameFeatures

FPS = 30
OPEN_EAR = 0.30


def constant_speed(kmh, clock="15:00", drive_s=600, turn=None):
    timeline = [{"t": 0, "speed_kmh": kmh}]
    if turn is not None:  # (start, end) of the turn signal
        timeline += [
            {"t": turn[0], "speed_kmh": kmh, "turn_signal": "left"},
            {"t": turn[1], "speed_kmh": kmh, "turn_signal": "off"},
        ]
    timeline.append({"t": 100000, "speed_kmh": kmh})
    return scenario_from_dict(
        {"name": "t", "start_clock": clock, "initial_drive_time_s": drive_s, "timeline": timeline}
    )


def drive(seconds, scenario, ear=None, mar=None, yaw=None, pitch=None, phone=None, face=None, enroll=False):
    """Run the decision pipeline. Each signal is a function of t. Returns (alerts, results)."""
    th = load_thresholds()
    th["enrollment"] = {**th["enrollment"], "enabled": enroll}
    pipeline = DecisionPipeline(th)
    can = CanSimulator(scenario)
    alerts, results = [], []
    for i in range(round(seconds * FPS)):
        t = i / FPS
        if face is not None and not face(t):
            f = FrameFeatures(i, t, False, 0.0)
        else:
            f = FrameFeatures(
                i,
                t,
                True,
                1.0,
                ear=ear(t) if ear else OPEN_EAR,
                mar=mar(t) if mar else 0.05,
                pitch=pitch(t) if pitch else 0.0,
                yaw=yaw(t) if yaw else 0.0,
                roll=0.0,
            )
        r = pipeline.step(f, phone(t) if phone else False, can.sample(t))
        results.append(r)
        if r.alert.new_alert is not None:
            a = r.alert.new_alert
            alerts.append((round(a.t, 1), a.level, a.reasons))
    return alerts, results


def between(a, b, value, other):
    return lambda t: value if a <= t < b else other


def normal_blinks(t):
    return 0.08 if (t % 4.0) < 0.15 else OPEN_EAR  # 15 blinks / min


# ---------------------------------------------------------------- no alert (false positive checks)


def test_alert_driver_three_minutes_no_alert():
    alerts, results = drive(180, constant_speed(50), ear=normal_blinks)
    assert alerts == []
    assert max(r.risk.level for r in results) == 0


def test_mirror_glances_no_alert():
    glance = lambda t: 45.0 if (t % 6.0) < 0.8 else 0.0  # noqa: E731
    alerts, _ = drive(60, constant_speed(60), ear=normal_blinks, yaw=glance)
    assert alerts == []


def test_lane_change_with_turn_signal_no_alert():
    alerts, _ = drive(20, constant_speed(60, turn=(8, 12)), yaw=between(9, 12, 50.0, 0.0))
    assert alerts == []


def test_parked_phone_and_looking_around_no_alert():
    alerts, _ = drive(30, constant_speed(0), phone=between(5, 20, True, False), yaw=between(5, 15, 60.0, 0.0))
    assert alerts == []


def test_talking_no_alert():
    talking = lambda t: 0.7 if (t % 0.6) < 0.3 else 0.2  # noqa: E731
    alerts, _ = drive(60, constant_speed(50), ear=normal_blinks, mar=talking)
    assert alerts == []


# ---------------------------------------------------------------- distraction


def test_phone_use_while_driving_is_one_l2_alert():
    alerts, _ = drive(20, constant_speed(50), phone=between(5, 12, True, False))
    assert len(alerts) == 1
    t, level, reasons = alerts[0]
    assert level == 2 and reasons == ("phone",)
    assert 5.5 < t < 7.0  # ratio reaches 60 % after ~1.2 s, then 0.5 s confirmation


def test_looking_away_2s_city_is_l2():
    alerts, _ = drive(15, constant_speed(50), yaw=between(5, 8, 50.0, 0.0))
    assert [(lv, r) for _, lv, r in alerts] == [(2, ("off_road",))]


@pytest.mark.parametrize(("speed", "expected"), [(100, [(2, ("off_road",))]), (50, [])])
def test_looking_away_1_7s_only_alerts_at_high_speed(speed, expected):
    alerts, _ = drive(15, constant_speed(speed), yaw=between(5, 6.7, 50.0, 0.0))
    assert [(lv, r) for _, lv, r in alerts] == expected


# ---------------------------------------------------------------- drowsiness


def test_microsleep_is_immediate_l3():
    alerts, results = drive(20, constant_speed(80), ear=between(10, 12, 0.08, OPEN_EAR))
    assert alerts[0][1:] == (3, ("microsleep",))
    assert alerts[0][0] == pytest.approx(11.5, abs=0.1)  # 1.5 s after the eyes closed
    assert max(r.alert.active_level for r in results) == 3


def test_growing_drowsiness_raises_l1_then_l2_at_night():
    # Slow long blinks (PERCLOS ~20-25 %) from t=30 s, yawns and nods later.
    def ear(t):
        if t < 30:
            return normal_blinks(t)
        if 100 <= t < 100.8 or 120 <= t < 120.8:  # eyes closed during the nods
            return 0.08
        return 0.08 if (t % 4.0) < 0.9 else OPEN_EAR

    yawn = lambda t: 0.8 if any(s <= t < s + 3 for s in (60, 80)) else 0.05  # noqa: E731
    nod = lambda t: 25.0 if (100 <= t < 100.8 or 120 <= t < 120.8) else 0.0  # noqa: E731
    alerts, results = drive(150, constant_speed(90, clock="03:00", drive_s=8000), ear=ear, mar=yawn, pitch=nod)
    levels = [lv for _, lv, _ in alerts]
    assert levels[:2] == [1, 2]
    assert all(r == ("drowsy_score",) for _, lv, r in alerts if lv < 3)
    assert results[-1].risk.drowsy_score >= 70


def test_same_drowsiness_scores_higher_at_night_but_no_more_than_the_cap():
    # PERCLOS term 1 (40) + 2 yawns (10) = 50 -> L1; at night after a long drive x1.2 = 60, still L1.
    # Before M92 the two factors stacked: x1.44 = 72 -> L2.
    ear = lambda t: normal_blinks(t) if t < 30 else (0.08 if (t % 4.0) < 0.9 else OPEN_EAR)  # noqa: E731
    yawn = lambda t: 0.8 if any(s <= t < s + 3 for s in (70, 85)) else 0.05  # noqa: E731
    night, rn = drive(110, constant_speed(90, clock="03:00", drive_s=8000), ear=ear, mar=yawn)
    day, rd = drive(110, constant_speed(90, clock="15:00", drive_s=600), ear=ear, mar=yawn)
    assert max(lv for _, lv, _ in night) == 1
    assert max(lv for _, lv, _ in day) == 1
    cap = load_thresholds()["risk"]["drowsy"]["context_factor_cap"]
    assert rn[-1].risk.drowsy_score == pytest.approx(rd[-1].risk.drowsy_score * cap, abs=0.5)


def test_narrowed_eyes_in_the_sun_no_alert():
    # Squinting into the sun (0.74 x the open EAR, above the 0.65 close ratio) with normal
    # blinks for 2 min: the eye hysteresis holds "closed" after each blink, PERCLOS must not.
    ear = lambda t: normal_blinks(t) if t < 30 else (0.08 if (t % 4.0) < 0.15 else 0.74 * OPEN_EAR)  # noqa: E731
    alerts, _ = drive(150, constant_speed(60), ear=ear)
    assert alerts == []


# ---------------------------------------------------------------- standing still (red light, rest)


def parked_until(drive_off, kmh=40, clock="15:00"):
    """Standing still from t=0, then driving off at `drive_off` s."""
    timeline = [
        {"t": 0, "speed_kmh": 0},
        {"t": drive_off, "speed_kmh": 0},
        {"t": drive_off + 2, "speed_kmh": kmh},
        {"t": 100000, "speed_kmh": kmh},
    ]
    return scenario_from_dict({"name": "t", "start_clock": clock, "timeline": timeline})


def test_standing_still_raises_no_alert_at_all():
    """M30 (02/10): speed 0 = no alert. Before, a microsleep at a red light still got an L1 chime."""
    alerts, results = drive(30, constant_speed(0), ear=between(10, 14, 0.08, OPEN_EAR))
    assert alerts == [] and all(r.alert.active_level == 0 for r in results)
    assert any("microsleep" in r.drowsiness.events for r in results)  # still seen (trip summary)


def test_standing_still_looking_away_with_a_phone_raises_nothing():
    alerts, _ = drive(20, constant_speed(0), yaw=between(5, 15, 60.0, 0.0), phone=between(5, 15, True, False))
    assert alerts == []


def test_resting_the_eyes_after_parking_is_never_l3_and_goes_silent():
    # Parks, closes the eyes 20 s later for 5 min: no alert at all (M30).
    alerts, results = drive(360, constant_speed(0), ear=between(20, 320, 0.08, OPEN_EAR))
    assert alerts == [] and results[-1].alert.active_level == 0


def test_the_same_closure_while_driving_is_l3():
    alerts, _ = drive(30, constant_speed(60), ear=between(10, 14, 0.08, OPEN_EAR))
    assert alerts[0][1:] == (3, ("microsleep",))


@pytest.mark.parametrize("clock", ["15:00", "02:00"])
def test_driving_off_after_a_rest_raises_nothing(clock):
    # Nap 20-170 s while parked, awake from 170 s, drives off at 190 s. Without dropping the
    # rest, PERCLOS and the microsleep memory gave L1 by day / L2 at night on driving off.
    alerts, _ = drive(300, parked_until(190, clock=clock), ear=between(20, 170, 0.08, OPEN_EAR))
    assert all(t < 120 for t, _, _ in alerts)


def test_microsleep_after_a_rest_is_still_l3():
    ear = lambda t: 0.08 if (20 <= t < 170 or 220 <= t < 223) else OPEN_EAR  # noqa: E731
    alerts, _ = drive(240, parked_until(190), ear=ear)
    assert [(lv, r) for t, lv, r in alerts if t > 190] == [(3, ("microsleep",))]


def test_a_rest_restarts_the_repeated_l1_count():
    """M32: L1 alerts before a rest do not count towards the L1 -> L2 escalation after it."""
    pipeline = DecisionPipeline(load_thresholds())
    pipeline.alerts._l1_emits["drowsy_score"] = [0.0, 1.0]  # two L1 alerts before parking
    can = CanSimulator(parked_until(130))
    for i in range(140 * FPS):
        t = i / FPS
        f = FrameFeatures(i, t, True, 1.0, ear=OPEN_EAR, mar=0.05, pitch=0.0, yaw=0.0, roll=0.0)
        pipeline.step(f, False, can.sample(t))
        if t < 125:
            assert pipeline.alerts._l1_emits  # a stop shorter than a rest keeps them
    assert pipeline.alerts._l1_emits == {}


# ---------------------------------------------------------------- safety gaps (head drop, no face, new reason)


def test_eyes_close_then_head_drops_is_l3():
    # Eyes close at 10 s, the head drops 0.7 s later (eye state unknown from then on).
    alerts, results = drive(
        20, constant_speed(80), ear=between(10, 16, 0.08, OPEN_EAR), pitch=between(10.7, 16, 40.0, 0.0)
    )
    assert alerts[0][1:] == (3, ("microsleep",))
    assert alerts[0][0] == pytest.approx(11.5, abs=0.1)
    assert any(r.drowsiness.head_drop for r in results)


def test_glance_at_dashboard_after_blink_is_not_l3():
    # A blink, then looking down at the dashboard for 3 s with lids low: not a microsleep.
    alerts, _ = drive(
        20, constant_speed(50), ear=between(10, 13.2, 0.08, OPEN_EAR), pitch=between(10.2, 13.2, 32.0, 0.0)
    )
    assert all(level < 3 for _, level, _ in alerts)


def ramp(start, end, rise_s, peak):
    """0 before `start`, rises to `peak` over `rise_s`, holds until `end`, then 0."""
    return lambda t: 0.0 if not start <= t < end else peak * min(1.0, (t - start) / rise_s)


LOOK_DOWN_EAR = 0.15  # lids follow the gaze down: ~0.5 x the open-eye EAR, not shut


def test_looking_down_at_the_phone_with_the_head_partly_bowed_is_distraction_not_sleep():
    # Head bowed 18 deg (under eye.max_pitch_down_deg: eyes still judged), lids lowered, 4 s.
    alerts, results = drive(
        24, constant_speed(60), ear=between(20, 24, LOOK_DOWN_EAR, OPEN_EAR), pitch=ramp(20, 24, 0.8, 18.0)
    )
    assert all(level < 3 for _, level, _ in alerts) and not any(r.drowsiness.microsleep for r in results)
    assert [(lv, r) for _, lv, r in alerts] == [(2, ("off_road",))]  # "Nhìn về phía trước"
    assert any(r.drowsiness.gaze_down for r in results)


def test_slowly_bowing_to_the_lap_with_lids_lowered_is_not_carried():
    # Head goes down to 40 deg over 1.5 s: the lids were lowered > 0.5 s before it passed 25 deg.
    alerts, results = drive(
        26, constant_speed(60), ear=between(20, 25, LOOK_DOWN_EAR, OPEN_EAR), pitch=ramp(20, 25, 1.5, 40.0)
    )
    assert not any(r.drowsiness.head_drop for r in results)
    assert all(level < 3 for _, level, _ in alerts)
    assert ("off_road",) in [r for _, _, r in alerts]


def test_eyes_shut_with_the_head_bowed_is_still_a_microsleep():
    # Falling asleep with the head sagging 18 deg: the eyes are really shut (0.27 x).
    alerts, _ = drive(24, constant_speed(60), ear=between(20, 24, 0.08, OPEN_EAR), pitch=ramp(20, 24, 0.8, 18.0))
    assert alerts[0][1:] == (3, ("microsleep",))


def test_eyes_shut_then_a_slow_head_drop_is_still_carried():
    alerts, results = drive(26, constant_speed(60), ear=between(20, 25, 0.08, OPEN_EAR), pitch=ramp(20, 25, 1.5, 40.0))
    assert any(r.drowsiness.head_drop for r in results)
    assert alerts[0][1:] == (3, ("microsleep",))


def test_face_lost_while_moving_is_unavailable_without_alert():
    alerts, results = drive(15, constant_speed(60), face=between(5, 10, False, True))
    assert alerts == []
    off = [r.risk.t for r in results if r.risk.unavailable]
    assert off[0] == pytest.approx(8.0, abs=0.05) and off[-1] < 10.0  # after 3 s without a face, until it is back


def test_face_lost_short_or_parked_no_alert():
    alerts, _ = drive(15, constant_speed(60), face=between(5, 7, False, True))
    assert alerts == []
    alerts, _ = drive(15, constant_speed(0), face=between(5, 12, False, True))
    assert alerts == []


def test_off_road_then_phone_gives_second_l2_alert():
    alerts, _ = drive(20, constant_speed(50), yaw=between(5, 14, 50.0, 0.0), phone=between(9, 14, True, False))
    assert [(lv, r[0]) for _, lv, r in alerts] == [(2, "off_road"), (2, "phone")]


def test_camera_mounted_35_deg_to_the_side():
    # The driver looks at the road, which is 35 deg off the camera axis: no alert.
    alerts, _ = drive(60, constant_speed(60), ear=normal_blinks, yaw=lambda t: 35.0)
    assert alerts == []
    # Looking a further 50 deg away for 3 s is still an L2.
    alerts, _ = drive(20, constant_speed(60), yaw=lambda t: 85.0 if 10 <= t < 13 else 35.0)
    assert [(lv, r) for _, lv, r in alerts] == [(2, ("off_road",))]
