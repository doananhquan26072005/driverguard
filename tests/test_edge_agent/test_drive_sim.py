"""tools/drive_sim.py: the simulated car (pure physics on fake time steps) and its GET /can."""

import http.client
import json
import threading

import pytest

from tools.drive_sim import DriveSim, DriveSimConfig, ScenarioDrive, SimServer, apply_key, load_config

CFG = DriveSimConfig(speed_step_kmh=10, max_kmh=120, accel_kmh_per_s=8, brake_kmh_per_s=15)


def run(sim, seconds, dt=0.05):
    for _ in range(round(seconds / dt)):
        sim.step(dt)


def test_config_file_loads():
    assert load_config().port == 8766


def test_accelerates_at_a_cars_pace_and_brakes_to_a_stop():
    sim = DriveSim(CFG)
    for _ in range(5):
        sim.accelerate()
    assert sim.target_kmh == 50
    run(sim, 1.0)
    assert sim.speed_kmh == pytest.approx(8.0)  # not a jump to 50
    run(sim, 10.0)
    assert sim.speed_kmh == pytest.approx(50.0)
    sim.decelerate()
    run(sim, 1.0)
    assert sim.speed_kmh == pytest.approx(40.0)
    sim.stop()
    run(sim, 2.0)
    assert sim.speed_kmh == pytest.approx(10.0)
    run(sim, 1.0)
    assert sim.speed_kmh == 0.0  # parked


def test_speed_target_is_clamped():
    sim = DriveSim(CFG)
    sim.decelerate()
    assert sim.target_kmh == 0
    for _ in range(20):
        sim.accelerate()
    assert sim.target_kmh == 120


def test_turn_signal_stays_on_until_switched_off():
    sim = DriveSim(CFG)
    sim.signal("left")
    assert sim.turn_signal == "left"
    run(sim, 60.0)  # no auto-off: the driver switches it off
    assert sim.turn_signal == "left"
    sim.signal("right")
    assert sim.turn_signal == "right"
    sim.signal("right")  # same side again = off
    assert sim.turn_signal is None


def test_keys():
    sim = DriveSim(CFG)
    assert apply_key(sim, "w") and apply_key(sim, "\x1b[A")
    assert sim.target_kmh == 20
    apply_key(sim, "s")
    assert sim.target_kmh == 10
    apply_key(sim, "c")
    assert sim.target_kmh == 50
    apply_key(sim, " ")
    assert sim.target_kmh == 0
    apply_key(sim, "\x1b[D")
    assert sim.turn_signal == "left"
    apply_key(sim, "d")
    assert sim.turn_signal == "right"
    apply_key(sim, "x")
    assert sim.turn_signal is None
    assert not apply_key(sim, "q")


def test_scenario_replay():
    drive = ScenarioDrive("config/scenarios/city_day.yaml")
    assert drive.reading()["speed_kmh"] == 0.0
    run(drive, 10.0, dt=0.5)
    assert drive.reading()["speed_kmh"] == pytest.approx(40.0)


def get(port, path, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        conn.request("GET" if path else "OPTIONS", path or "/can", headers=headers or {})
        resp = conn.getresponse()
        return resp, resp.read()
    finally:
        conn.close()


def test_http_can_endpoint_serves_numbers_to_any_page():
    sim = DriveSim(CFG)
    sim.cruise(30)
    run(sim, 5.0)
    sim.signal("left")
    server = SimServer(sim, "keyboard", 0, threading.Lock()).start()
    try:
        resp, body = get(server.port, "/can", {"Origin": "https://example.up.railway.app"})
        assert resp.status == 200 and resp.getheader("Access-Control-Allow-Origin") == "*"
        assert json.loads(body) == {"speed_kmh": 30.0, "turn_signal": "left", "t": 5.0, "source": "keyboard"}
        resp, _ = get(server.port, None, {"Access-Control-Request-Private-Network": "true"})
        assert resp.status == 204 and resp.getheader("Access-Control-Allow-Private-Network") == "true"
        assert get(server.port, "/state")[0].status == 404
    finally:
        server.stop()
