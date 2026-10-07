"""M43: the backend takes why monitoring is unavailable (event metric `cause`, seconds per cause in the
trip summary) and still takes agents older than it."""

from datetime import UTC, datetime, timedelta

from edge_agent.config import load_thresholds
from edge_agent.context.can_sim import CanSimulator, scenario_from_dict
from edge_agent.decision.pipeline import DecisionPipeline
from edge_agent.io.publisher import build_system_event
from tests.test_backend.conftest import DEVICE_KEY, login
from tests.test_edge_agent.test_quality import face, seq

HEADERS = {"X-Device-Key": DEVICE_KEY}


def post(client, **body):
    return client.post("/api/v1/events", json={"device_id": "cam-001", **body}, headers=HEADERS)


def test_cause_is_stored_and_an_unknown_one_refused(client):
    event = build_system_event("monitoring_unavailable", "trip-m43", 60.0, metrics={"cause": "camera_blocked"})
    assert post(client, events=[event]).json()["accepted"] == 1
    stored = client.get("/api/v1/events?trip_id=trip-m43", headers=login(client, "boss")).json()[0]
    assert stored["metrics"]["cause"] == "camera_blocked"
    old = build_system_event("monitoring_unavailable", "trip-m43", 60.0)  # an agent older than M43
    assert post(client, events=[old]).json()["accepted"] == 1
    bad = build_system_event("monitoring_unavailable", "trip-m43", 60.0, metrics={"cause": "driver_asleep"})
    assert post(client, events=[bad]).status_code == 422


def test_summary_seconds_per_cause_and_old_summaries(client):
    frames = seq(6, lambda t: face(t, face_brightness=120)) + seq(10, lambda t: face(t, face_brightness=8), t0=6)
    th = load_thresholds()
    th["enrollment"] = {**th["enrollment"], "enabled": False}
    pipeline = DecisionPipeline(th)
    can = CanSimulator(scenario_from_dict({"start_clock": "12:00", "timeline": [{"t": 0, "speed_kmh": 60}]}))
    for f in frames:
        pipeline.step(f, False, can.sample(f.timestamp))
    start = datetime(2026, 10, 6, 8, 0, tzinfo=UTC)
    summary = pipeline.trip_log.summary("trip-m43s", start, start + timedelta(seconds=16)).to_dict()
    assert summary["unavailable_by_cause"]["low_light"] > 3
    assert post(client, summaries=[summary]).json()["summaries_accepted"] == 1
    boss = login(client, "boss")
    stored = client.get("/api/v1/trip-reports/cam-001/trip-m43s", headers=boss).json()["summary"]
    assert stored["unavailable_by_cause"] == summary["unavailable_by_cause"]

    old = {**summary, "trip_id": "trip-m43old"}
    del old["unavailable_by_cause"]
    assert post(client, summaries=[old]).json()["summaries_accepted"] == 1
    bad = {**summary, "trip_id": "trip-m43bad", "unavailable_by_cause": {"asleep": 3.0}}
    assert post(client, summaries=[bad]).status_code == 422
