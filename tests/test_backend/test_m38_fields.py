"""M38: the backend takes the new block 8 fields (phone_kind, off_road_ratio, glances, ...) and still
takes agents older than them."""

from datetime import UTC, datetime, timedelta

from backend.schemas import EventBatch
from edge_agent.io.publisher import batch_body, build_event, build_sample
from tests.test_backend.conftest import DEVICE_KEY, login, make_event
from tests.test_edge_agent.test_m38_distraction import pipeline_run

HEADERS = {"X-Device-Key": DEVICE_KEY}


def test_backend_accepts_the_new_fields_and_still_takes_old_agents(client):
    _, results, pipeline = pipeline_run(30, lambda t: {}, phone_at_t=lambda t: t >= 5.0, kind_at=lambda t: "text")
    r = next(r for r in results if r.alert.new_alert is not None)
    event = build_event(r.alert.new_alert, r, "trip-m38")
    sample = build_sample(12.0, 0.03, 2, "trip-m38", off_road_ratio=0.41)
    start = datetime(2026, 10, 5, 8, 0, tzinfo=UTC)
    summary = pipeline.trip_log.summary("trip-m38", start, start + timedelta(seconds=30)).to_dict()
    records = [{"kind": k, "data": d} for k, d in (("event", event), ("sample", sample), ("summary", summary))]
    body = batch_body("cam-001", records)
    EventBatch.model_validate(body)
    out = client.post("/api/v1/events", json=body, headers=HEADERS)
    assert out.status_code == 200, out.text
    assert out.json()["accepted"] == 1 and out.json()["samples_accepted"] == 1

    boss = login(client, "boss")
    stored = client.get("/api/v1/events?trip_id=trip-m38", headers=boss).json()[0]
    assert stored["reasons"] == ["phone"] and stored["metrics"]["phone_kind"] == "text"
    timeline = client.get("/api/v1/timeline?trip_id=trip-m38", headers=boss).json()
    assert timeline["samples"][0]["off_road_ratio"] == 0.41
    report = client.get("/api/v1/trip-reports/cam-001/trip-m38", headers=boss).json()["summary"]
    assert report["phone_text_s"] > 0 and report["phone_call_s"] == 0 and "glances" in report

    old = make_event()  # an agent older than M38: no phone_kind, no off_road_ratio
    old_sample = build_sample(10.0, None, 0, "trip-old")
    out = client.post(
        "/api/v1/events", json={"device_id": "cam-001", "events": [old], "samples": [old_sample]}, headers=HEADERS
    )
    assert out.json()["accepted"] == 1 and out.json()["samples_accepted"] == 1


def test_old_summary_without_the_new_fields_is_stored_with_zeros(client):
    _, _, pipeline = pipeline_run(10, lambda t: {})
    start = datetime(2026, 10, 5, 8, 0, tzinfo=UTC)
    summary = pipeline.trip_log.summary("trip-old", start, start + timedelta(seconds=10)).to_dict()
    for key in ("phone_call_s", "phone_text_s", "glances", "off_road_ratio_max", "turned_away_s"):
        del summary[key]
    out = client.post("/api/v1/events", json={"device_id": "cam-001", "summaries": [summary]}, headers=HEADERS)
    assert out.status_code == 200 and out.json()["summaries_accepted"] == 1
    stored = client.get("/api/v1/trip-reports/cam-001/trip-old", headers=login(client, "boss")).json()["summary"]
    assert stored["glances"] == 0 and stored["turned_away_s"] == 0


def test_backend_refuses_a_made_up_phone_kind(client):
    bad = make_event(metrics={"phone_ratio_2s": 0.7, "phone_kind": "selfie"})
    out = client.post("/api/v1/events", json={"device_id": "cam-001", "events": [bad]}, headers=HEADERS)
    assert out.status_code == 422
