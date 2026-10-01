"""Default mode: manual vehicle driven by the HUD buttons, and "Đổi tài xế". Fake sequences."""

import http.client
import json

import pytest

from edge_agent.config import PROJECT_ROOT, load_thresholds
from edge_agent.context.can_sim import ManualVehicle, is_manual, load_manual
from edge_agent.decision.pipeline import DecisionPipeline
from edge_agent.hud.server import HudServer, HudState
from edge_agent.perception.features import FrameFeatures
from edge_agent.web.bridge import WebAgent
from tests.test_edge_agent.test_web_bridge import H, W, synthetic_face

MANUAL_YAML = PROJECT_ROOT / "config" / "scenarios" / "manual.yaml"


def test_manual_vehicle_starts_parked_and_follows_the_buttons():
    v = load_manual(MANUAL_YAML)
    assert is_manual(MANUAL_YAML) and v.cruise_kmh == 50
    assert v.sample(0.0).speed_kmh == 0.0
    v.drive()
    assert v.sample(1.0).speed_kmh == 50
    assert v.sample(11.0).drive_time_s == pytest.approx(10.0)
    v.park()
    assert v.sample(12.0).speed_kmh == 0.0


def test_manual_vehicle_drives_once_the_driver_is_enrolled():
    v = ManualVehicle()
    v.on_enrollment(("step_done",))
    assert not v.driving
    v.on_enrollment(("enrolled",))
    assert v.driving
    v.park()
    v.on_enrollment(("enrolled",))  # a later enrollment (no driver change) does not drive off
    assert not v.driving
    v.change_driver()
    assert not v.driving and v.drive_after_enrollment
    v.on_enrollment(("enrolled",))
    assert v.driving


def test_change_driver_drops_the_previous_drivers_baselines_but_not_the_trip():
    from edge_agent.context.can_sim import VehicleSignals

    th = load_thresholds()
    p = DecisionPipeline(th)
    signals = lambda t, v: VehicleSignals(t, v, None, 0.0, 12.0)  # noqa: E731
    for i in range(int(40 * 15)):  # 40 s driving, eyes half shut: PERCLOS builds up
        t = i / 15
        f = FrameFeatures(i, t, True, 1.0, ear=0.12 if i % 3 else 0.30, mar=0.05, pitch=0.0, yaw=0.0, roll=0.0)
        r = p.step(f, False, signals(t, 50.0))
    assert r.drowsiness.perclos_60s > 0.3
    p.change_driver()
    f = FrameFeatures(600, 40.1, True, 1.0, ear=0.30, mar=0.05, pitch=0.0, yaw=0.0, roll=0.0)
    r = p.step(f, False, signals(40.1, 0.0))
    assert r.drowsiness.perclos_60s == 0.0 and r.drowsiness.perclos_coverage_s == 0.0
    assert r.enrollment.status == "look_camera"  # parked: the new driver enrolls
    s = p.trip_log.summary("t", *_times())
    assert s.driver_changes == 1 and s.duration_s == pytest.approx(40.1, abs=0.2)


def _times():
    from datetime import UTC, datetime, timedelta

    start = datetime(2026, 10, 1, 8, tzinfo=UTC)
    return start, start + timedelta(seconds=41)


# ---------------------------------------------------------------- in the browser (#/live)


def frames(agent, seconds, t0=0.0):
    face = synthetic_face().ravel()
    state = None
    for i in range(int(seconds * 30)):
        state = json.loads(agent.frame(t0 + i / 30, int((t0 + i / 30) * 30), W, H, face, 1, (0.05, 0.05), 12.0, 140.0))
    return state


def test_web_default_is_the_manual_vehicle_starting_parked():
    agent = WebAgent("web-an", "trip-m")
    state = frames(agent, 1)
    assert state["vehicle"] == {"manual": True, "driving": False}
    assert state["speed_kmh"] == 0.0
    assert state["enrollment"]["status"] == "look_camera"  # parked: enrollment runs at once


def test_web_buttons_park_drive_and_change_driver():
    agent = WebAgent("web-an", "trip-m")
    frames(agent, 1)
    assert agent.vehicle("drive") == "ok"
    state = frames(agent, 1, t0=1.0)
    assert state["vehicle"]["driving"] and state["speed_kmh"] == 50
    assert agent.vehicle("park") == "ok"
    assert frames(agent, 1, t0=2.0)["speed_kmh"] == 0.0
    assert agent.vehicle("change_driver") == "ok"
    body = json.loads(agent.take_batch())
    assert [e["reasons"] for e in body["events"]] == [["driver_changed"]]
    assert json.loads(agent.end_trip())["driver_changes"] == 1


def test_scripted_scenario_has_no_park_button_but_can_change_driver():
    agent = WebAgent("web-an", "trip-s", scenario="highway_night")
    frames(agent, 1)
    assert agent.vehicle("park") == "unsupported"
    assert agent.vehicle("change_driver") == "ok"


# ---------------------------------------------------------------- on the device (HUD server)


def post(port, path, body):
    """Plain http.client: urllib's macOS proxy lookup is not needed for 127.0.0.1."""
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        conn.request("POST", path, json.dumps(body), {"Content-Type": "application/json"})
        resp = conn.getresponse()
        return resp.status, json.loads(resp.read())
    finally:
        conn.close()


def test_hud_server_queues_vehicle_buttons_for_the_main_loop():
    state = HudState()
    server = HudServer(state, lambda _: None, port=0).start()
    try:
        assert post(server.port, "/vehicle", {"action": "park"}) == (409, {"status": "unsupported"})
        assert post(server.port, "/vehicle", {"action": "change_driver"})[0] == 202
        state.set_vehicle({"manual": True, "driving": True})
        assert post(server.port, "/vehicle", {"action": "park"})[0] == 202
        assert post(server.port, "/vehicle", {"action": "fly"})[0] == 409
        assert state.take_actions() == ["change_driver", "park"]
        assert state.take_actions() == []
        assert state.to_json()["vehicle"] == {"manual": True, "driving": True}
    finally:
        server.stop()
