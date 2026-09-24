"""M4 acceptance: the whole decision chain (blocks 7-12) gives the right L0-L3 per scenario.

Uses the real config/thresholds.yaml and fake 30 FPS feature sequences, no video.
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


def drive(seconds, scenario, ear=None, mar=None, yaw=None, pitch=None, phone=None, face=None):
    """Run the decision pipeline. Each signal is a function of t. Returns (alerts, results)."""
    pipeline = DecisionPipeline(load_thresholds())
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


def test_same_drowsiness_is_l2_at_night_but_l1_by_day():
    # PERCLOS term 1 (40) + 2 yawns (10) = 50 -> L1; at night after a long drive x1.44 = 72 -> L2.
    ear = lambda t: normal_blinks(t) if t < 30 else (0.08 if (t % 4.0) < 0.9 else OPEN_EAR)  # noqa: E731
    yawn = lambda t: 0.8 if any(s <= t < s + 3 for s in (70, 85)) else 0.05  # noqa: E731
    night, rn = drive(110, constant_speed(90, clock="03:00", drive_s=8000), ear=ear, mar=yawn)
    day, rd = drive(110, constant_speed(90, clock="15:00", drive_s=600), ear=ear, mar=yawn)
    assert max(lv for _, lv, _ in night) == 2
    assert max(lv for _, lv, _ in day) == 1
    assert rn[-1].risk.drowsy_score == pytest.approx(rd[-1].risk.drowsy_score * 1.44, abs=0.5)


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


def test_face_lost_while_moving_is_l2():
    alerts, _ = drive(15, constant_speed(60), face=between(5, 10, False, True))
    assert [(lv, r) for _, lv, r in alerts] == [(2, ("no_face",))]
    assert alerts[0][0] == pytest.approx(8.5, abs=0.1)  # 3 s without a face + 0.5 s confirmation


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
