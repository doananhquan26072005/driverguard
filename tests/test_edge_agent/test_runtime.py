"""TripRuntime (edge_agent/runtime.py), shared by the device and the browser: fake feature sequences, no video."""

import pytest

from edge_agent.config import load_thresholds
from edge_agent.context.can_sim import CanSimulator, ExternalVehicle, scenario_from_dict
from edge_agent.io.publisher import MetadataPublisher, PublisherConfig, check_metadata_only
from edge_agent.perception.features import FrameFeatures
from edge_agent.runtime import TripRuntime
from tests.test_edge_agent.test_enrollment import obedient

FPS = 15


class Recorder:
    def __init__(self) -> None:
        self.records: list[tuple[str, dict]] = []

    def __call__(self, kind: str, data: dict) -> None:
        check_metadata_only(data)
        self.records.append((kind, data))

    def kinds(self) -> list[str]:
        return [k for k, _ in self.records]

    def reasons(self) -> list[list[str]]:
        return [d["reasons"] for k, d in self.records if k == "event"]


class FakeSelector:
    def __init__(self) -> None:
        self.anchors: list = []

    def set_anchor(self, anchor) -> None:
        self.anchors.append(anchor)


def scenario(speeds):
    """speeds: [(t, km/h), ...]"""
    timeline = [{"t": t, "speed_kmh": v} for t, v in speeds] + [{"t": 100000, "speed_kmh": speeds[-1][1]}]
    return scenario_from_dict({"name": "t", "start_clock": "15:00", "initial_drive_time_s": 600, "timeline": timeline})


def make(speeds=((0, 60),), enroll=False, emit=None):
    th = load_thresholds()
    th["enrollment"] = {**th["enrollment"], "enabled": enroll}
    rec, sel = Recorder(), FakeSelector()
    rt = TripRuntime(th, "trip-1", CanSimulator(scenario(list(speeds))), "t", sel, emit=emit or rec)
    return rt, rec, sel


def run(rt, seconds, t0=0.0, driver=None, **over):
    """Feed `seconds` of frames; the fake driver reacts to the enrollment step like test_enrollment."""
    step, status = None, "waiting"
    for i in range(round(seconds * FPS)):
        t = t0 + i / FPS
        f = (driver or obedient)(i, t, status, **over)
        step = rt.step(f, False, t)
        status = step.result.enrollment.status
        if status == "consent":  # the driver taps "Đồng ý" on the HUD
            rt.enrollment_answer(True)
    return step, t0 + round(seconds * FPS) / FPS


def test_awake_drive_records_nothing_and_fills_the_hud():
    rt, rec, _ = make()
    run(rt, 12)
    assert rec.records == []
    state = rt.hud.to_json()
    assert state["connected"] and state["level"] == 0 and state["vehicle"]["driving"]
    assert rt.fps == pytest.approx(FPS, rel=0.01)


def test_microsleep_is_one_alert_event_on_the_hud():
    rt, rec, _ = make()
    _, t = run(rt, 12)
    step, _ = run(rt, 2.5, t0=t, ear=0.05, blink=0.9)
    assert step.result.alert.active_level == 3
    assert rec.kinds() == ["event"] and rec.reasons() == [["microsleep"]]
    (alert,) = rt.hud.to_json()["alerts"]
    assert alert["level"] == 3 and alert["event_id"] == rec.records[0][1]["event_id"]


def test_face_lost_while_moving_is_unavailable_then_restored():
    rt, rec, _ = make()
    _, t = run(rt, 12)
    lost = [rt.step(FrameFeatures(1000 + i, t + i / FPS, False, 0.0), False, t + i / FPS) for i in range(4 * FPS)]
    assert sum(s.unavailable_changed for s in lost) == 1 and lost[-1].result.risk.unavailable
    run(rt, 1, t0=t + 4)
    assert rec.reasons() == [["monitoring_unavailable"], ["monitoring_restored"]]


def test_a_closed_minute_is_one_fatigue_sample():
    rt, rec, _ = make()
    run(rt, 61)
    assert rec.kinds() == ["sample"]
    assert rec.records[0][1]["trip_id"] == "trip-1"


def test_enrollment_sets_the_drivers_anchor_and_change_driver_clears_it():
    rt, rec, sel = make(speeds=((0, 0),), enroll=True)  # parked: enrollment runs at once
    step, _ = run(rt, 15)
    assert step.result.enrollment.enrolled
    assert len(sel.anchors) == 1 and sel.anchors[0] is not None
    assert rec.kinds() == ["event"] and rec.records[0][1]["reasons"] == ["driver_enrolled"]
    rt.change_driver()
    assert sel.anchors[-1] is None
    assert rec.reasons()[-1] == ["driver_changed"]


def test_enrollment_waits_on_the_consent_screen_and_a_new_driver_is_asked_again():
    rt, _, _ = make(speeds=((0, 0),), enroll=True)
    step = rt.step(obedient(0, 0.0, "waiting"), False, 0.0)
    assert step.result.enrollment.status == "consent"
    assert rt.hud.to_json()["enrollment"]["status"] == "consent"  # the HUD shows the consent screen
    assert rt.enrollment_answer(False) and not rt.enrollment_answer(True)  # "Để sau", then nothing asked
    _, t = run(rt, 15, t0=1.0)
    assert not rt.decisions.enrollment.profile  # said later: not enrolled while still parked
    rt.change_driver()
    assert rt.step(obedient(0, t, "waiting"), False, t).result.enrollment.status == "consent"


def test_false_alarm_marks_the_hud_and_records_feedback_once():
    rt, rec, _ = make()
    _, t = run(rt, 12)
    run(rt, 2.5, t0=t, ear=0.05, blink=0.9)
    event_id = rec.records[0][1]["event_id"]
    assert rt.false_alarm("nope") == "unknown"
    assert rt.false_alarm(event_id) == "ok"
    assert rt.false_alarm(event_id) == "duplicate"
    assert rec.kinds() == ["event", "feedback"] and rec.records[1][1]["event_id"] == event_id
    assert rt.end_trip()["false_alarms"] == 1


def test_camera_lost_is_shown_recorded_and_counted_in_the_summary(monkeypatch):
    import edge_agent.runtime as runtime

    now = [100.0]
    monkeypatch.setattr(runtime.time, "monotonic", lambda: now[0])
    rt, rec, _ = make()
    run(rt, 2)
    rt.camera(True)
    assert rt.hud.to_json()["camera_lost"] is True
    now[0] += 30.0
    rt.camera(False)
    rt.camera(True)
    now[0] += 5.0  # still lost when the trip ends
    summary = rt.end_trip()
    assert rec.reasons() == [["camera_lost"], ["camera_restored"], ["camera_lost"]]
    assert summary["camera_lost_s"] == pytest.approx(35.0, abs=0.1)
    assert rec.kinds()[-1] == "summary" and rec.records[-1][1] is summary


def test_external_vehicle_without_a_signal_is_parked_on_the_hud():
    th = load_thresholds()
    vehicle = ExternalVehicle(stale_s=1.0, moving_kmh=5.0)
    rt = TripRuntime(th, "trip-2", vehicle, "sim", FakeSelector())
    vehicle_state = rt.hud.to_json()["vehicle"]
    assert vehicle_state["source"] == "sim" and not vehicle_state["connected"] and not vehicle_state["driving"]
    assert not rt.started
    run(rt, 0.5)
    assert rt.started  # no emit: nothing recorded, nothing raised


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_vehicle_signal_lost_while_driving_keeps_monitoring_and_tells_driver_and_backend():
    """FMEA row 2: the link goes quiet at 60 km/h for 5 min. Before M26 that read as parked: distraction
    off, drowsiness capped at L1, then off after the rest time. Now: still monitored as moving."""
    clock = FakeClock()
    vehicle = ExternalVehicle(stale_s=1.0, moving_kmh=5.0, stationary_kmh=1.0, clock=clock)
    rec = Recorder()
    rt = TripRuntime(load_thresholds(), "trip-3", vehicle, "sim", FakeSelector(), emit=rec)
    t = 0.0
    for i in range(round(15 * FPS)):  # 15 s at 60 km/h, eyes open (baselines settle)
        t = i / FPS
        clock.now = t
        vehicle.update(60.0, None)
        rt.step(obedient(i, t, "waiting"), False, t)
    assert rec.reasons() == []
    step = None
    for i in range(round(15 * FPS), round(315 * FPS)):  # 5 min with no reading
        t = i / FPS
        clock.now = t
        shut = t >= 312.0  # eyes close for the last 3 s
        step = rt.step(obedient(i, t, "waiting", ear=0.05, blink=0.9) if shut else obedient(i, t, "waiting"), False, t)
    assert rec.reasons()[0] == ["vehicle_signal_lost"]
    hud = rt.hud.to_json()["vehicle"]
    assert hud["signal_lost"] and hud["speed_kmh"] is None and hud["driving"]
    assert step.result.context.moving and not step.result.context.resting
    assert ["microsleep"] in rec.reasons()  # L3 still raised, 5 min after the link went quiet
    vehicle.update(60.0, None)
    rt.step(obedient(0, t + 0.1, "waiting"), False, t + 0.1)
    assert rec.reasons()[-1] == ["vehicle_signal_restored"]
    assert rt.end_trip()["vehicle_signal_lost_s"] == pytest.approx(299.0, abs=1.0)


def test_vehicle_signal_lost_while_parked_tells_the_driver_and_the_speed_coming_back_shows_driving():
    clock = FakeClock()
    vehicle = ExternalVehicle(stale_s=1.0, moving_kmh=5.0, stationary_kmh=1.0, clock=clock)
    rec = Recorder()
    rt = TripRuntime(load_thresholds(), "trip-4", vehicle, "sim", FakeSelector(), emit=rec)
    for i in range(round(5 * FPS)):  # parked, the simulator answers
        t = i / FPS
        clock.now = t
        vehicle.update(0.0, None)
        rt.step(obedient(i, t, "waiting"), False, t)
    for i in range(round(5 * FPS), round(10 * FPS)):  # the link goes quiet while parked
        t = i / FPS
        clock.now = t
        step = rt.step(obedient(i, t, "waiting"), False, t)
    assert rec.reasons() == [["vehicle_signal_lost"]]
    hud = rt.hud.to_json()["vehicle"]
    assert hud["signal_lost"] and not hud["driving"] and hud["speed_kmh"] == 0.0  # told, still parked
    assert not step.result.context.moving
    vehicle.update(40.0, None)  # the speed comes back: the vehicle is driving
    step = rt.step(obedient(0, 10.1, "waiting"), False, 10.1)
    assert rec.reasons()[-1] == ["vehicle_signal_restored"]
    assert step.result.context.moving and rt.hud.to_json()["vehicle"]["driving"]


def test_frames_failing_for_a_while_are_a_processing_error_then_recover():
    """M28 (FMEA row 3): the callers catch a failing frame and call frame_failed; a short glitch is
    ignored, a lasting one tells the HUD (not monitored) and the backend, the next good frame clears it."""
    rt, rec, _ = make()
    _, t = run(rt, 2)
    for i in range(round(0.5 * FPS)):  # 0.5 s of failures: a glitch
        rt.frame_failed(t + i / FPS, "ValueError")
    run(rt, 0.2, t0=t + 0.5)
    assert rec.reasons() == [] and not rt.hud.to_json()["processing_error"]
    t += 1.0
    for i in range(round(2 * FPS)):  # 2 s of failures
        rt.frame_failed(t + i / FPS, "ValueError")
    assert rec.reasons() == [["agent_error"]] and rt.hud.to_json()["processing_error"]
    assert rt.last_error == "ValueError"
    run(rt, 0.2, t0=t + 2.0)
    assert rec.reasons()[-1] == ["agent_recovered"] and not rt.hud.to_json()["processing_error"]
    assert rt.last_error is None


def test_low_fps_for_a_while_warns_and_clears():
    rt, rec, _ = make()
    t = 0.0
    for i in range(round(3 * 30)):  # 3 s at 30 FPS
        t = i / 30
        rt.step(obedient(i, t, "waiting"), False, t, clock=t)
    for i in range(round(8 * 10)):  # 8 s at 10 FPS
        t += 0.1
        rt.step(obedient(0, t, "waiting"), False, t, clock=t)
    lows = [r for r in rec.records if r[1].get("reasons") == ["low_fps"]]
    assert len(lows) == 1 and lows[0][1]["metrics"]["fps"] < 14.5
    assert rt.hud.to_json()["low_fps"]
    for i in range(round(3 * 30)):  # back to 30 FPS
        t += 1 / 30
        rt.step(obedient(0, t, "waiting"), False, t, clock=t)
    assert rec.reasons()[-1] == ["fps_restored"] and not rt.hud.to_json()["low_fps"]


def test_fps_at_the_15_fps_minimum_is_not_low():
    rt, rec, _ = make()
    run(rt, 20)  # exactly 15 FPS (the CLAUDE.md minimum)
    assert rec.reasons() == [] and not rt.hud.to_json()["low_fps"]


def test_fps_follows_the_given_clock_not_the_frame_time():
    rt, _, _ = make()
    for i in range(30):
        rt.step(obedient(i, i / FPS, "waiting"), False, i / FPS, clock=i / 10)
    assert rt.fps == pytest.approx(10.0, rel=0.01)


def test_publisher_takes_runtime_records_and_rejects_unknown_kinds(tmp_path):
    sent = []
    pub = MetadataPublisher(
        "cam-1", lambda body: sent.append(body) or 200, PublisherConfig(outbox_path=str(tmp_path / "o.db"))
    )
    rt, _, _ = make(emit=pub.publish_record)
    _, t = run(rt, 12)
    run(rt, 2.5, t0=t, ear=0.05, blink=0.9)
    rt.end_trip()
    assert pub.queued == 2
    with pytest.raises(ValueError):
        pub.publish_record("image", {})
    pub.stop()
    assert [len(b.get("events", [])) for b in sent] == [1] and len(sent[0]["summaries"]) == 1
