"""Driver enrollment (block 6 stage) with fake feature sequences, no video.

The fake driver follows the HUD: what it does on a frame depends on the step the previous
frame asked for, like a real driver reacting to the prompt.
"""

import json

import numpy as np
import pytest

from edge_agent.config import load_thresholds
from edge_agent.context.can_sim import CanSimulator, scenario_from_dict
from edge_agent.decision.pipeline import DecisionPipeline
from edge_agent.io.publisher import build_enrolled_event, build_event
from edge_agent.perception.enrollment import DriverEnrollment, EnrollmentConfig
from edge_agent.perception.features import FrameFeatures
from edge_agent.perception.landmarks import DriverAnchor, DriverSelector, LandmarkConfig, face_center_size, face_shape

FPS = 15  # the minimum frame rate: enrollment must work there
OPEN_EAR, SHUT_EAR = 0.30, 0.07
ROAD_YAW, ROAD_PITCH = 12.0, 6.0  # camera mounted off to the side
SHAPE = (0.3, 0.3, 0.4, 0.6, 1.5, 0.3, 0.35)


def frame(i, t, ear=OPEN_EAR, mar=0.05, yaw=0.0, pitch=0.0, blink=0.05, **kw):
    return FrameFeatures(
        i,
        t,
        True,
        1.0,
        ear=ear,
        mar=mar,
        yaw=yaw,
        pitch=pitch,
        roll=0.0,
        eye_blink=blink,
        face_shape=SHAPE,
        face_center=(0.4, 0.45),
        face_size=0.1,
        **kw,
    )


def obedient(i, t, status, **over):
    """What a driver does when the HUD shows `status`."""
    if status == "look_road":
        kw = {"yaw": ROAD_YAW, "pitch": ROAD_PITCH}
    elif status == "close_eyes":
        kw = {"ear": SHUT_EAR, "blink": 0.9, "yaw": 2.0}
    else:
        kw = {}
    return frame(i, t, **{**kw, **over})


def enroll(seconds, stationary=lambda t: True, driver=obedient, config=None, agree=True):
    """Run DriverEnrollment alone. Returns the states. agree: the driver taps "Đồng ý" on the
    consent screen as soon as it shows (False: "Để sau"; None: taps nothing)."""
    e = DriverEnrollment(config or EnrollmentConfig(), ear_min=0.18, ear_max=0.42, road_max_deg=45)
    states, status = [], "waiting"
    for i in range(round(seconds * FPS)):
        t = i / FPS
        s = e.update(driver(i, t, status), stationary(t))
        status = s.status
        states.append(s)
        if status == "consent" and agree is not None:
            e.consent(agree)
    return states


def test_road_step_keeps_where_the_iris_sits():
    def driver(i, t, status):
        if status == "look_road":  # a blink in the middle of the step must not move the value
            return obedient(i, t, status, iris_y=0.3, blink=0.9) if i % 7 == 0 else obedient(i, t, status, iris_y=-0.06)
        return obedient(i, t, status, iris_y=0.02)

    profile = enroll(20, driver=driver)[-1].profile
    assert profile.road_iris_y == pytest.approx(-0.06)
    assert enroll(20)[-1].profile.road_iris_y is None  # no iris landmarks: block 8 learns it at start-up


def events(states):
    return [(round(i / FPS, 1), ev, s.status) for i, s in enumerate(states) for ev in s.events]


# ---------------------------------------------------------------- the three steps


def test_obedient_driver_enrolls_in_about_ten_seconds():
    states = enroll(20)
    done = [i for i, s in enumerate(states) if "enrolled" in s.events]
    assert len(done) == 1
    s = states[done[0]]
    # 2 s + (1 s settle + 3 s) + 2 s of good frames, plus one frame per step to start
    assert 8.0 <= s.duration_s <= 10.0
    p = s.profile
    assert p.ear_open == pytest.approx(OPEN_EAR) and p.ear_closed == pytest.approx(SHUT_EAR)
    assert p.blink_closed == pytest.approx(0.9)  # eyeBlink of the close-eyes step
    assert p.mar_closed == pytest.approx(0.05)
    assert (p.road_yaw, p.road_pitch) == pytest.approx((ROAD_YAW, ROAD_PITCH))
    assert p.anchor == DriverAnchor(SHAPE, (0.4, 0.45), 0.1)
    assert s.attempts == 0
    assert all(st.status == "done" and st.enrolled for st in states[done[0] :])
    assert [ev for _, ev, _ in events(states)] == ["step_done", "step_done", "step_done", "enrolled"]


def test_progress_goes_from_zero_to_one_per_step():
    states = enroll(20)
    cam = [s.progress for s in states if s.status == "look_camera"]
    assert cam[0] == 0.0 and cam == sorted(cam) and cam[-1] > 0.9


def test_blinks_pause_the_step_but_do_not_change_the_open_eye_value():
    def blinker(i, t, status):
        if status == "look_camera" and int(t * 10) % 7 == 0:  # a blink every 0.7 s
            return frame(i, t, ear=0.08, blink=0.9)
        return obedient(i, t, status)

    s = enroll(20, driver=blinker)[-1]
    assert s.enrolled and s.profile.ear_open == pytest.approx(OPEN_EAR)


def test_looking_away_pauses_step_one_with_a_hint():
    def away(i, t, status):
        return frame(i, t, yaw=40.0) if status == "look_camera" else obedient(i, t, status)

    states = enroll(5, driver=away)
    assert states[-1].status == "look_camera" and states[-1].progress == 0.0
    assert states[-1].hint == "look_camera"


def test_too_dark_for_ear_does_not_learn():
    def dark(i, t, status):
        return obedient(i, t, status, eye_cnn_reason="low_light", p_closed=0.1)

    states = enroll(8, driver=dark)
    assert states[-1].status == "look_camera" and states[-1].hint == "too_dark"


def test_unsteady_head_redoes_the_road_step():
    def shaky(i, t, status):
        if status == "look_road":
            return frame(i, t, yaw=ROAD_YAW + (15.0 if i % 2 else -15.0), pitch=ROAD_PITCH)
        return obedient(i, t, status)

    states = enroll(8, driver=shaky)
    assert states[-1].status == "look_road" and states[-1].attempts >= 1
    assert states[-1].hint == "hold_still"


def test_open_mouth_redoes_step_one():
    def talking(i, t, status):
        return frame(i, t, mar=0.5) if status == "look_camera" else obedient(i, t, status)

    states = enroll(3, driver=talking)
    assert states[-1].status == "look_camera" and states[-1].attempts == 1 and states[-1].hint == "close_mouth"


def test_eyes_that_never_read_shut_give_up_instead_of_learning_a_bad_value():
    """Glare on glasses: EAR stays high with the eyes shut. The step times out, then enrollment fails."""

    def glare(i, t, status):
        if status == "close_eyes":
            return frame(i, t, ear=0.26, blink=0.9)
        return obedient(i, t, status)

    states = enroll(60, driver=glare)
    assert states[-1].status == "failed" and not states[-1].enrolled
    assert [ev for _, ev, _ in events(states)][-1] == "failed"
    assert states[-1].attempts == EnrollmentConfig().max_attempts


def test_failed_enrollment_retries_at_the_next_stop():
    def glare_first(i, t, status):
        if status == "close_eyes" and t < 50:
            return frame(i, t, ear=0.26, blink=0.9)
        return obedient(i, t, status)

    states = enroll(80, stationary=lambda t: not 50 <= t < 55, driver=glare_first)
    assert any(s.status == "failed" for s in states)
    assert states[-1].enrolled


# ---------------------------------------------------------------- vehicle moving


def test_only_at_a_stop():
    states = enroll(10, stationary=lambda t: False)
    assert {s.status for s in states} == {"waiting"} and states[-1].hint == "stop_vehicle"


def test_driving_off_mid_way_starts_over_at_the_next_stop():
    states = enroll(30, stationary=lambda t: not 4 <= t < 10)
    statuses = [s.status for s in states]
    assert statuses[int(5 * FPS)] == "waiting"
    assert states[-1].enrolled
    assert states[-1].duration_s < 12  # timed from the restart, not from t = 0


def test_disabled_is_off():
    states = enroll(10, config=EnrollmentConfig(enabled=False))
    assert {s.status for s in states} == {"off"} and not states[-1].enrolled


# ---------------------------------------------------------------- whole decision chain


def scenario(speeds):
    """speeds: [(t, km/h), ...]"""
    timeline = [{"t": t, "speed_kmh": v} for t, v in speeds] + [{"t": 100000, "speed_kmh": speeds[-1][1]}]
    return scenario_from_dict({"name": "t", "start_clock": "15:00", "initial_drive_time_s": 600, "timeline": timeline})


DRIVE_OFF_AT_12 = [(0, 0), (12, 0), (12.1, 60)]  # the simulator interpolates between points


def run_pipeline(seconds, speeds, driver, enroll_on=True):
    th = load_thresholds()
    th["enrollment"] = {**th["enrollment"], "enabled": enroll_on}
    pipeline = DecisionPipeline(th)
    can = CanSimulator(scenario(speeds))
    results, alerts, status = [], [], "waiting"
    for i in range(round(seconds * FPS)):
        t = i / FPS
        r = pipeline.step(driver(i, t, status), False, can.sample(t))
        status = r.enrollment.status
        results.append(r)
        if r.alert.new_alert is not None:
            alerts.append((round(t, 1), r.alert.new_alert.level, r.alert.new_alert.reasons))
        if status == "consent":  # the driver taps "Đồng ý" on the HUD
            pipeline.enrollment_answer(True)
    return results, alerts


def test_closing_the_eyes_for_enrollment_raises_no_alert():
    results, alerts = run_pipeline(15, [(0, 0)], obedient)
    assert results[-1].enrollment.enrolled
    assert alerts == []


ENROLL_THEN_DRIVE = [(0, 0), (15, 0), (15.1, 60)]  # enrolls while parked, drives off at 15 s


def test_a_real_microsleep_after_enrollment_is_still_l3():
    def sleepy(i, t, status):
        return obedient(i, t, status, ear=SHUT_EAR, blink=0.9) if 20 <= t < 24 else obedient(i, t, status)

    results, alerts = run_pipeline(30, ENROLL_THEN_DRIVE, sleepy)
    _, without = run_pipeline(30, ENROLL_THEN_DRIVE, sleepy, enroll_on=False)
    assert results[-1].enrollment.enrolled
    assert [(level, reasons) for _, level, reasons in alerts] == [(3, ("microsleep",))]
    assert [a[1:] for a in alerts] == [a[1:] for a in without]  # as before enrollment existed


def test_enrolled_eye_baseline_does_not_follow_drowsy_narrowing():
    """Eyes narrow to 0.21 over the drive: the self-learnt baseline sinks, the enrolled one holds."""

    def narrowing(i, t, status):
        if t >= 12:
            return frame(i, t, ear=0.21, yaw=ROAD_YAW, pitch=ROAD_PITCH)
        return obedient(i, t, status)

    speeds = DRIVE_OFF_AT_12
    enrolled, _ = run_pipeline(200, speeds, narrowing)
    learnt, _ = run_pipeline(200, speeds, narrowing, enroll_on=False)
    assert enrolled[-1].enrollment.enrolled
    assert enrolled[-1].drowsiness.ear_open_baseline == pytest.approx(OPEN_EAR * 0.9)
    assert learnt[-1].drowsiness.ear_open_baseline == pytest.approx(0.21)


def test_lips_resting_apart_are_not_a_yawn_once_enrolled():
    def lips_apart(i, t, status):
        mar = 0.5 if 30 <= t < 33 else 0.15
        return obedient(i, t, status, mar=mar if status != "look_camera" else 0.15)

    speeds = DRIVE_OFF_AT_12
    enrolled, _ = run_pipeline(40, speeds, lips_apart)
    learnt, _ = run_pipeline(40, speeds, lips_apart, enroll_on=False)
    assert enrolled[-1].enrollment.profile.mar_closed == pytest.approx(0.15)
    assert enrolled[-1].drowsiness.yawn_count_10min == 0  # 0.5 < 0.15 + 0.40
    assert learnt[-1].drowsiness.yawn_count_10min == 1  # 0.5 > 0.45


def test_enrolled_road_pose_replaces_the_start_up_calibration():
    def at_road(i, t, status):
        return obedient(i, t, status) if t < 12 else frame(i, t, yaw=ROAD_YAW, pitch=ROAD_PITCH)

    results, _ = run_pipeline(14, DRIVE_OFF_AT_12, at_road)
    first_moving = next(r for r in results if r.distraction.active)
    assert not first_moving.distraction.calibrating
    assert (first_moving.distraction.baseline_yaw, first_moving.distraction.baseline_pitch) == pytest.approx(
        (ROAD_YAW, ROAD_PITCH)
    )


def test_not_enrolled_keeps_monitoring_and_asks_to_stop():
    """Driving off without enrolling: everything runs as before, the HUD asks for a stop."""

    def asleep_later(i, t, status):
        return frame(i, t, ear=SHUT_EAR, blink=0.9) if 20 <= t < 23 else frame(i, t)

    results, alerts = run_pipeline(25, [(0, 60)], asleep_later)
    assert results[-1].enrollment.status == "waiting" and results[-1].enrollment.hint == "stop_vehicle"
    assert any(level == 3 and "microsleep" in reasons for _, level, reasons in alerts)


# ---------------------------------------------------------------- metadata: status only, never the profile


def test_backend_gets_the_status_not_the_profile():
    results, _ = run_pipeline(15, [(0, 0)], obedient)
    r = next(r for r in results if "enrolled" in r.enrollment.events)
    event = build_enrolled_event(r, "trip-1")
    assert event["type"] == "system" and event["reasons"] == ["driver_enrolled"]
    assert set(event["metrics"]) == {"enroll_s", "enroll_redo"}
    text = json.dumps(event)
    for secret in ("shape", "ear", "anchor", "center", str(SHAPE[4])):
        assert secret not in text


def test_alert_metrics_say_whether_the_driver_was_enrolled():
    def sleepy(i, t, status):
        return obedient(i, t, status, ear=SHUT_EAR, blink=0.9) if 20 <= t < 24 else obedient(i, t, status)

    results, _ = run_pipeline(30, ENROLL_THEN_DRIVE, sleepy)
    r = next(r for r in results if r.alert.new_alert is not None)
    assert build_event(r.alert.new_alert, r, "trip-1")["metrics"]["enrolled"] == 1


# ---------------------------------------------------------------- block 3: who the driver is


def synthetic_mesh(seed, cheek_scale=1.0):
    """A face-like 478-point mesh; cheek_scale changes the face proportions (another person)."""
    rng = np.random.default_rng(seed)
    pts = rng.uniform(-1, 1, (478, 3)).astype(np.float32) * (60, 80, 20)
    pts[33], pts[263] = (-30, -20, 5), (30, -20, 5)  # eye outer corners
    pts[133], pts[362] = (-12, -20, 2), (12, -20, 2)
    pts[168], pts[1], pts[10] = (0, -22, 0), (0, 10, -10), (0, -60, 5)
    pts[234], pts[454] = (-55 * cheek_scale, 0, 20), (55 * cheek_scale, 0, 20)
    pts[129], pts[358] = (-10, 8, -2), (10, 8, -2)
    return pts


def place(pts, scale, cx, cy):
    out = pts * scale
    out[:, 0] += cx
    out[:, 1] += cy
    return out


def test_face_shape_does_not_depend_on_size_or_position():
    a = synthetic_mesh(1)
    assert face_shape(place(a, 1.0, 200, 200)) == pytest.approx(face_shape(place(a, 1.6, 450, 260)), rel=1e-5)


def test_enrolled_driver_is_chosen_over_a_bigger_passenger():
    w = 640
    driver = place(synthetic_mesh(1), 1.0, 220, 240)
    passenger = place(synthetic_mesh(2, cheek_scale=1.4), 1.3, 450, 240)  # leans in: bigger
    selector = DriverSelector(LandmarkConfig())
    assert selector.choose([driver, passenger], w) == 1  # not enrolled: largest face
    center, size = face_center_size(driver, w)
    selector.set_anchor(DriverAnchor(face_shape(driver), center, size))
    assert selector.choose([driver, passenger], w) == 0
    assert selector.choose([passenger, driver], w) == 1


def test_a_single_face_is_always_taken():
    selector = DriverSelector(LandmarkConfig())
    driver = place(synthetic_mesh(1), 1.0, 220, 240)
    center, size = face_center_size(driver, 640)
    selector.set_anchor(DriverAnchor(face_shape(driver), center, size))
    assert selector.choose([place(synthetic_mesh(2), 1.0, 400, 240)], 640) == 0
    assert selector.choose([], 640) == -1


# ---------------------------------------------------------------- consent before the steps


def test_steps_wait_for_the_driver_to_agree():
    states = enroll(20, agree=None)
    assert {st.status for st in states} == {"consent"}  # never starts on its own
    assert not any(st.events for st in states)
    assert states[0].progress == 0.0 and states[0].hint is None


def test_agreeing_starts_step_one_at_once():
    states = enroll(20)
    assert states[0].status == "consent"
    assert states[1].status == "look_camera"
    assert any("enrolled" in st.events for st in states)


def test_later_asks_again_at_the_next_stop():
    stopped = lambda t: t < 3 or t >= 6  # noqa: E731  stop, drive 3 s, stop again
    states = enroll(10, stationary=stopped, agree=False)
    statuses = [st.status for st in states]
    assert statuses[0] == "consent" and statuses[1] == "later"
    assert set(statuses[1 : 3 * FPS]) == {"later"}  # not asked again while parked
    assert statuses[4 * FPS] == "waiting"  # driving
    assert statuses[6 * FPS] == "consent"  # next stop: asked again
    assert not any(s in statuses for s in ("look_camera", "look_road", "close_eyes"))


def test_agreed_once_per_driver_steps_restart_without_asking():
    stopped = lambda t: t < 3 or t >= 6  # noqa: E731  drives off in the middle of the steps
    states = enroll(20, stationary=stopped)
    assert [st.status for st in states].count("consent") == 1
    assert states[6 * FPS].status == "look_camera"
    assert any("enrolled" in st.events for st in states)


def test_consent_screen_closes_when_driving_off():
    states = enroll(6, stationary=lambda t: t < 2, agree=None)
    assert states[2 * FPS + 1].status == "waiting" and states[2 * FPS + 1].hint == "stop_vehicle"


def test_consent_answer_only_counts_on_the_consent_screen():
    e = DriverEnrollment(EnrollmentConfig(), ear_min=0.18, ear_max=0.42, road_max_deg=45)
    assert e.consent(True) is False  # nothing asked yet (driving)
    assert e.update(frame(0, 0.0), stationary=True).status == "consent"
    assert e.consent(True) is True
    assert e.consent(True) is False  # already answered


def test_no_consent_needed_when_turned_off():
    states = enroll(20, config=EnrollmentConfig(require_consent=False), agree=None)
    assert states[0].status == "look_camera"
    assert any("enrolled" in st.events for st in states)
