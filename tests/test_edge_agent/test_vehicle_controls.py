"""Vehicle state follows the speed (0 km/h = parked) from the driving simulator (tools/drive_sim.py);
the only vehicle button left is "Đổi tài xế". Fake sequences and a fake clock, no video."""

import http.client
import json

import pytest

from edge_agent.config import load_thresholds
from edge_agent.context.can_sim import ExternalVehicle, SignalLink, hud_vehicle
from edge_agent.decision.pipeline import DecisionPipeline
from edge_agent.hud.server import HudServer, HudState
from edge_agent.perception.features import FrameFeatures
from edge_agent.web.bridge import WebAgent
from tests.test_edge_agent.test_web_bridge import H, W, synthetic_face


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_external_vehicle_without_a_signal_stands_still():
    v = ExternalVehicle(clock=FakeClock())
    s = v.sample(0.0)
    assert s.speed_kmh == 0.0 and s.turn_signal is None and not v.connected and not v.signal_lost
    assert not v.link_lost  # never had a signal: nothing was lost


def test_external_vehicle_follows_the_signal_and_is_lost_when_it_goes_stale_while_driving():
    clock = FakeClock()
    v = ExternalVehicle(stale_s=1.0, moving_kmh=5.0, clock=clock)
    v.update(50.0, "left")
    assert v.connected
    s = v.sample(0.0)
    assert s.speed_kmh == 50.0 and s.turn_signal == "left"
    clock.now = 0.9
    v.update(50.0, "sideways")  # unknown side = no signal
    assert v.sample(10.0).turn_signal is None
    assert v.sample(10.0).drive_time_s == pytest.approx(10.0)
    clock.now = 2.0  # link lost while driving: no reading for > 1 s
    s = v.sample(11.0)
    assert not v.connected and v.signal_lost
    assert s.speed_kmh is None and s.turn_signal is None  # speed unknown, not 0 km/h (M26)
    assert v.sample(20.0).drive_time_s == pytest.approx(20.0)  # still driving as far as we know
    v.update(40.0, None)  # back
    assert v.connected and not v.signal_lost and v.sample(21.0).speed_kmh == 40.0


def test_external_vehicle_lost_while_parked_stays_parked():
    clock = FakeClock()
    v = ExternalVehicle(stale_s=1.0, moving_kmh=5.0, clock=clock)
    v.update(0.0, None)  # stopped, then the simulator is closed
    clock.now = 5.0
    s = v.sample(5.0)
    assert not v.connected and not v.signal_lost and s.speed_kmh == 0.0
    assert v.link_lost  # still told: the link went quiet (M26)


def test_hud_vehicle_parked_or_driving_by_speed_alone():
    from edge_agent.context.can_sim import VehicleSignals

    sig = lambda v, turn=None: VehicleSignals(0.0, v, turn, 0.0, 12.0)  # noqa: E731
    assert hud_vehicle("sim", True, sig(0.0), 1.0)["driving"] is False
    assert hud_vehicle("sim", True, sig(0.5), 1.0)["driving"] is False
    d = hud_vehicle("sim", True, sig(32.04, "right"), 1.0)
    assert d == {
        "source": "sim",
        "connected": True,
        "speed_kmh": 32.0,
        "turn_signal": "right",
        "driving": True,
        "signal_lost": False,
    }
    assert hud_vehicle("sim", False, None, 1.0)["speed_kmh"] == 0.0
    lost = hud_vehicle("sim", False, sig(None), 1.0, signal_lost=True)
    assert lost["speed_kmh"] is None and lost["driving"] and lost["signal_lost"]


def test_signal_link_reads_the_simulator_and_survives_it_missing():
    import threading

    from tools.drive_sim import DriveSim, SimServer

    sim = DriveSim()
    sim.cruise(40.0)
    sim.step(10.0)
    sim.signal("right")
    server = SimServer(sim, "keyboard", 0, threading.Lock()).start()
    v = ExternalVehicle()
    try:
        link = SignalLink(v, f"http://127.0.0.1:{server.port}/can", period_s=0.2)
        assert link.poll_once()
        s = v.sample(0.0)
        assert s.speed_kmh == 40.0 and s.turn_signal == "right"
    finally:
        server.stop()
    assert not SignalLink(ExternalVehicle(), f"http://127.0.0.1:{server.port}/can", period_s=0.1).poll_once()


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
    assert r.enrollment.status == "consent"  # parked: the new driver is asked to enroll
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


def test_web_default_has_no_signal_and_is_parked():
    agent = WebAgent("web-an", "trip-m")
    state = frames(agent, 1)
    assert state["vehicle"]["source"] == "sim" and not state["vehicle"]["connected"]
    assert state["vehicle"]["driving"] is False and state["speed_kmh"] == 0.0
    assert state["enrollment"]["status"] == "consent"  # parked: the driver is asked to enroll
    assert agent.vehicle("enroll_start") == "ok" and agent.vehicle("enroll_start") == "ignored"
    state = frames(agent, 0.5, t0=1.0)
    assert state["enrollment"]["status"] == "look_camera"


def test_web_speed_and_turn_signal_come_from_the_simulator():
    agent = WebAgent("web-an", "trip-m")
    agent.vehicle_signal(60.0, "left")
    state = frames(agent, 0.5)
    assert state["vehicle"]["connected"] and state["vehicle"]["driving"]
    assert state["speed_kmh"] == 60.0 and state["vehicle"]["turn_signal"] == "left"
    agent.vehicle_signal(0.0, None)  # stopped at a light = parked
    state = frames(agent, 0.5, t0=0.5)
    assert not state["vehicle"]["driving"] and state["speed_kmh"] == 0.0


def test_web_only_change_driver_is_a_button():
    agent = WebAgent("web-an", "trip-m")
    frames(agent, 1)
    assert agent.vehicle("park") == "unsupported"
    assert agent.vehicle("drive") == "unsupported"
    assert agent.vehicle("change_driver") == "ok"
    body = json.loads(agent.take_batch())
    assert [e["reasons"] for e in body["events"]] == [["driver_changed"]]
    assert json.loads(agent.end_trip())["driver_changes"] == 1


def test_scripted_scenario_ignores_the_simulator_and_can_change_driver():
    agent = WebAgent("web-an", "trip-s", scenario="highway_night")
    agent.vehicle_signal(10.0, None)
    state = frames(agent, 1)
    assert state["vehicle"]["source"] == "highway_night" and state["vehicle"]["connected"]
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


def test_hud_server_only_queues_change_driver():
    state = HudState()
    server = HudServer(state, lambda _: None, port=0).start()
    try:
        assert post(server.port, "/vehicle", {"action": "park"}) == (409, {"status": "unknown"})
        assert post(server.port, "/vehicle", {"action": "drive"})[0] == 409
        assert post(server.port, "/vehicle", {"action": "change_driver"})[0] == 202
        assert state.take_actions() == ["change_driver"]
        assert state.take_actions() == []
        v = hud_vehicle("sim", True, None, 1.0)
        state.set_vehicle(v)
        assert state.to_json()["vehicle"] == v
    finally:
        server.stop()
