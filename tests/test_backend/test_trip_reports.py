"""Trip reports: the end-of-trip summary reaches the driver and the higher roles."""

from datetime import UTC, datetime, timedelta

from edge_agent.decision.trip_summary import TripCollector
from tests.test_backend.conftest import DEVICE_KEY, OTHER_DEVICE_KEY, login


def summary(trip_id="trip-20261001-080000", rating="attention"):
    start = datetime(2026, 10, 1, 8, 0, tzinfo=UTC)
    s = TripCollector().summary(trip_id, start, start + timedelta(minutes=30)).to_dict()
    s["rating"] = rating
    return s


def send(client, s, key=DEVICE_KEY, device_id="cam-001"):
    body = {"device_id": device_id, "summaries": [s]}
    return client.post("/api/v1/events", json=body, headers={"X-Device-Key": key})


def test_device_sends_a_summary_once_even_when_retried(client):
    s = summary()
    assert send(client, s).json()["summaries_accepted"] == 1
    send(client, s)  # offline queue retry
    reports = client.get("/api/v1/trip-reports", headers=login(client, "boss")).json()
    assert len(reports) == 1
    r = reports[0]
    assert (r["device_id"], r["driver_id"], r["rating"]) == ("cam-001", "drv-001", "attention")
    assert r["summary"]["trip_id"] == s["trip_id"] and r["reviewed_at"] is None


def test_drivers_see_only_their_own_reports(client):
    send(client, summary("trip-a"))
    send(client, summary("trip-b"), OTHER_DEVICE_KEY, "cam-002")
    an = login(client, "an")
    assert [r["trip_id"] for r in client.get("/api/v1/trip-reports", headers=an).json()] == ["trip-a"]
    assert client.get("/api/v1/trip-reports/cam-002/trip-b", headers=an).status_code == 404
    assert client.get("/api/v1/trip-reports/cam-001/trip-a", headers=an).status_code == 200
    assert len(client.get("/api/v1/trip-reports", headers=login(client, "boss")).json()) == 2


def test_higher_roles_mark_a_report_reviewed(client):
    send(client, summary("trip-a"))
    boss = login(client, "boss")
    assert len(client.get("/api/v1/trip-reports?unreviewed_only=true", headers=boss).json()) == 1
    r = client.post("/api/v1/trip-reports/cam-001/trip-a/review", headers=boss)
    assert r.status_code == 200 and r.json()["reviewed_by"] == "boss"
    assert client.get("/api/v1/trip-reports?unreviewed_only=true", headers=boss).json() == []
    # the driver sees that a manager read it, but cannot mark it themselves
    an = login(client, "an")
    assert client.get("/api/v1/trip-reports/cam-001/trip-a", headers=an).json()["reviewed_by"] == "boss"
    assert client.post("/api/v1/trip-reports/cam-001/trip-a/review", headers=an).status_code == 403


def test_web_user_sends_the_summary_with_their_token(client):
    an = login(client, "an")
    body = {"device_id": "web-an", "summaries": [summary("trip-web-1")]}
    assert client.post("/api/v1/web/events", json=body, headers=an).json()["summaries_accepted"] == 1
    reports = client.get("/api/v1/trip-reports", headers=login(client, "boss")).json()
    assert reports[0]["driver_id"] == "drv-001" and reports[0]["device_id"] == "web-an"


def test_a_summary_with_unknown_fields_is_refused(client):
    s = summary()
    s["face_crop"] = "x"
    assert send(client, s).status_code == 422


def test_vehicle_signal_lost_time_is_kept_and_older_agents_may_omit_it(client):
    s = summary("trip-lost")
    s["vehicle_signal_lost_s"] = 42.5
    assert send(client, s).json()["summaries_accepted"] == 1
    old = summary("trip-old")
    del old["vehicle_signal_lost_s"]  # an agent from before M26
    assert send(client, old).json()["summaries_accepted"] == 1
    boss = login(client, "boss")
    got = {r["trip_id"]: r["summary"] for r in client.get("/api/v1/trip-reports", headers=boss).json()}
    assert got["trip-lost"]["vehicle_signal_lost_s"] == 42.5


def test_the_reviewer_leaves_the_driver_a_note_and_can_change_it(client):
    # M105: the driver's "Lưu ý" column. A note is optional; sent again it replaces the one there.
    send(client, summary("trip-a"))
    boss = login(client, "boss")
    an = login(client, "an")
    path = "/api/v1/trip-reports/cam-001/trip-a/review"
    r = client.post(path, json={"note": "  Nghỉ giữa ca sau 2 giờ lái nhé.  "}, headers=boss)
    assert r.status_code == 200 and r.json()["review_note"] == "Nghỉ giữa ca sau 2 giờ lái nhé."
    assert (
        client.get("/api/v1/trip-reports/cam-001/trip-a", headers=an).json()["review_note"]
        == "Nghỉ giữa ca sau 2 giờ lái nhé."
    )
    client.post(path, headers=boss)  # marked again without a body: the note stays
    assert client.get("/api/v1/trip-reports", headers=an).json()[0]["review_note"] == "Nghỉ giữa ca sau 2 giờ lái nhé."
    send(client, summary("trip-a"))  # the device's offline queue sends the summary again: the note stays
    assert client.get("/api/v1/trip-reports", headers=an).json()[0]["review_note"] == "Nghỉ giữa ca sau 2 giờ lái nhé."
    client.post(path, json={"note": ""}, headers=boss)  # empty text clears it
    assert client.get("/api/v1/trip-reports", headers=an).json()[0]["review_note"] == ""
    assert client.post(path, json={"note": "x" * 501}, headers=boss).status_code == 422
    assert client.post(path, json={"note": "hi", "face": "x"}, headers=boss).status_code == 422


def test_a_database_from_before_the_note_gets_its_column(tmp_path):
    import sqlite3

    from backend import db

    conn = sqlite3.connect(tmp_path / "old.db")
    conn.execute(
        """CREATE TABLE trip_summaries (id INTEGER PRIMARY KEY, trip_id TEXT NOT NULL, device_id TEXT NOT NULL,
           driver_id TEXT, started_at TEXT NOT NULL, received_at TEXT NOT NULL, rating TEXT NOT NULL,
           summary TEXT NOT NULL, reviewed_by TEXT, reviewed_at TEXT, UNIQUE (device_id, trip_id))"""
    )
    for table in ("events", "fatigue_samples", "device_status"):
        conn.execute(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY, ts TEXT)")
    db.migrate(conn)
    assert "review_note" in {r[1] for r in conn.execute("PRAGMA table_info(trip_summaries)")}
