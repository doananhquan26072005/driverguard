"""M6 edge side: local HUD server, false-alarm path, remote thresholds, per-minute samples."""

import json
import time
import urllib.error
import urllib.request

import pytest

from edge_agent.config import load_thresholds
from edge_agent.context.can_sim import CanSimulator, scenario_from_dict
from edge_agent.decision.pipeline import DecisionPipeline
from edge_agent.decision.trip_memory import TripMemory
from edge_agent.hud.server import HudConfig, HudServer, HudState
from edge_agent.io.remote_config import apply_overrides
from edge_agent.perception.features import FrameFeatures

ORIGIN = "http://localhost:5173"


def a_result():
    pipeline = DecisionPipeline(load_thresholds())
    can = CanSimulator(scenario_from_dict({"start_clock": "02:00", "timeline": [{"t": 0, "speed_kmh": 72}]}))
    f = FrameFeatures(0, 0.0, True, 1.0, ear=0.3, mar=0.05, pitch=0.0, yaw=0.0, roll=0.0)
    return pipeline.step(f, False, can.sample(0.0))


@pytest.fixture
def hud():
    flagged = []
    state = HudState()
    server = HudServer(state, flagged.append, port=0).start()  # port 0: any free port
    yield state, f"http://127.0.0.1:{server.port}", flagged
    server.stop()


def call(url, body=None, origin=ORIGIN):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers={"Origin": origin, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status, json.loads(resp.read()), resp.headers
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read()), e.headers


def test_state_endpoint(hud):
    state, url, _ = hud
    code, body, headers = call(f"{url}/state")
    assert code == 200 and body["connected"] is False  # nothing from the main loop yet
    state.update(a_result(), fps=29.7)
    code, body, headers = call(f"{url}/state")
    assert body["connected"] and body["level"] == 0 and body["speed_kmh"] == 72.0 and body["night"] is True
    assert headers["Access-Control-Allow-Origin"] == ORIGIN
    assert "Access-Control-Allow-Origin" not in call(f"{url}/state", origin="http://evil.example")[2]


def test_extra_origin_and_private_network_preflight():
    hosted = "https://driveguard.example"
    server = HudServer(HudState(), lambda _: None, port=0, allowed_origins=(ORIGIN, hosted)).start()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{server.port}/state",
            method="OPTIONS",
            headers={"Origin": hosted, "Access-Control-Request-Private-Network": "true"},
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            assert resp.headers["Access-Control-Allow-Origin"] == hosted
            assert resp.headers["Access-Control-Allow-Private-Network"] == "true"
        req.add_header("Origin", "http://evil.example")
        with urllib.request.urlopen(req, timeout=3) as resp:
            assert resp.headers["Access-Control-Allow-Private-Network"] is None
    finally:
        server.stop()


def test_false_alarm_flow(hud):
    state, url, flagged = hud
    state.add_alert("ev-1", 2, ("phone",))
    assert call(f"{url}/state")[1]["alerts"][0]["event_id"] == "ev-1"
    code, body, _ = call(f"{url}/feedback", {"event_id": "ev-1"})
    assert code == 200 and flagged == ["ev-1"]
    assert call(f"{url}/state")[1]["alerts"][0]["feedback"] == "false_alarm"
    assert call(f"{url}/feedback", {"event_id": "ev-1"})[0] == 409  # only once
    assert call(f"{url}/feedback", {"event_id": "nope"})[0] == 404
    assert call(f"{url}/feedback", {"wrong": 1})[0] == 400
    assert flagged == ["ev-1"]


def test_feedback_window_expires():
    state = HudState(HudConfig(feedback_window_s=30.0))
    state.add_alert("ev-1", 1, ("drowsy_score",))
    assert state.to_json()["feedback_window_s"] == 30.0  # the HUD screen reads it from /state
    assert state.mark_false_alarm("ev-1", now=time.time() + 31) == "expired"
    state.add_alert("ev-2", 1, ("drowsy_score",))
    assert state.mark_false_alarm("ev-2", now=time.time() + 29) == "ok"


def test_server_only_listens_on_localhost(hud):
    _, url, _ = hud
    assert url.startswith("http://127.0.0.1:")


# ---------------------------------------------------------------- remote thresholds


def test_overrides_applied_including_int_keys():
    th = load_thresholds()
    merged, problems = apply_overrides(th, {"risk.drowsy.l1": 45.0, "alert.cooldown_s.2": 60.0})
    assert problems == []
    assert merged["risk"]["drowsy"]["l1"] == 45.0 and merged["alert"]["cooldown_s"][2] == 60.0
    assert th["risk"]["drowsy"]["l1"] == 40  # original untouched


@pytest.mark.parametrize(
    "values",
    [
        {"risk.drowsy.l1": 80.0},  # above the YAML l2 of 70
        {"risk.distraction.off_road_high_speed_s": 3.0},  # above the YAML off_road_s of 2
        {"drowsiness.microsleep_min_s": 5.0, "risk.microsleep_l3_s": 0.5},  # event after the L3 rule
        {"drowsiness.nod.max_s": 0.1},  # below nod.min_s
        {"risk.nope": 1.0},
        {"capture": 1.0},
    ],
)
def test_inconsistent_overrides_are_ignored(values):
    th = load_thresholds()
    merged, problems = apply_overrides(th, values)
    assert problems and merged is th


# ---------------------------------------------------------------- per-minute samples


def test_bins_completed_counts_closed_minutes():
    mem = TripMemory()
    states = [mem.update(t, 10.0) for t in range(0, 185, 5)]
    assert [s.bins_completed for s in states if s.t in (55, 60, 125, 180)] == [0, 1, 2, 3]


def test_hud_reports_camera_lost():
    state = HudState()
    assert state.to_json()["camera_lost"] is False
    state.set_camera_lost(True)
    assert state.to_json()["camera_lost"] is True
