"""Fleet overview (M33): heartbeats, who is online / went quiet / ended, alerts per vehicle.

Fake heartbeat sequences only (arriving, stopping, coming back), no device.
"""

from datetime import UTC, datetime, timedelta

import pytest

from backend import db
from tests.test_backend.conftest import DEVICE_KEY, OTHER_DEVICE_KEY, login, make_event, post_events


def iso(dt=None):
    return (dt or datetime.now(UTC)).isoformat()


def beat(client, state="monitoring", device_id="cam-001", key=DEVICE_KEY, ts=None, **extra):
    heartbeat = {"ts": ts or iso(), "trip_id": "trip-1", "state": state, "moving": True, **extra}
    return client.post(
        "/api/v1/events", json={"device_id": device_id, "heartbeat": heartbeat}, headers={"X-Device-Key": key}
    )


def fleet(client, user="boss", **params):
    r = client.get("/api/v1/fleet", headers=login(client, user), params=params)
    assert r.status_code == 200, r.text
    return {d["device_id"]: d for d in r.json()}


def age_last_seen(settings, device_id, seconds):
    """As if the device was last heard from `seconds` ago."""
    with db.closing(settings.db_path) as conn:
        conn.execute(
            "UPDATE device_status SET last_seen = ? WHERE device_id = ?",
            (iso(datetime.now(UTC) - timedelta(seconds=seconds)), device_id),
        )


def test_registered_device_never_heard_from(client):
    f = fleet(client)
    assert set(f) == {"cam-001", "cam-002"}
    assert f["cam-001"]["status"] == "never" and f["cam-001"]["last_seen"] is None
    assert f["cam-001"]["driver_id"] == "drv-001" and f["cam-001"]["state"] is None


def test_heartbeat_alone_is_a_valid_batch_and_shows_the_device_online(client):
    assert beat(client).status_code == 200
    d = fleet(client)["cam-001"]
    assert (d["status"], d["state"], d["moving"], d["trip_id"]) == ("online", "monitoring", True, "trip-1")
    assert d["last_seen"] is not None


def test_device_goes_quiet_then_comes_back(client, settings):
    beat(client)
    age_last_seen(settings, "cam-001", 89)
    assert fleet(client)["cam-001"]["status"] == "online"
    age_last_seen(settings, "cam-001", 91)  # past DG_DEVICE_OFFLINE_AFTER_S (90)
    d = fleet(client)["cam-001"]
    assert d["status"] == "offline" and d["state"] == "monitoring"  # last known state is kept
    beat(client, "camera_lost")
    d = fleet(client)["cam-001"]
    assert (d["status"], d["state"]) == ("online", "camera_lost")


def test_offline_limit_comes_from_settings(client, settings):
    settings.device_offline_after_s = 10
    beat(client)
    age_last_seen(settings, "cam-001", 11)
    assert fleet(client)["cam-001"]["status"] == "offline"


def test_ended_trip_is_not_a_lost_device(client, settings):
    beat(client)
    beat(client, "ended")
    age_last_seen(settings, "cam-001", 3600)
    assert fleet(client)["cam-001"]["status"] == "ended"
    beat(client, "monitoring", trip_id="trip-2")  # next trip
    d = fleet(client)["cam-001"]
    assert (d["status"], d["trip_id"]) == ("online", "trip-2")


def test_older_heartbeat_arriving_late_does_not_overwrite_the_state(client):
    now = datetime.now(UTC)
    beat(client, "ended", ts=iso(now))
    beat(client, "monitoring", ts=iso(now - timedelta(seconds=30)))
    assert fleet(client)["cam-001"]["state"] == "ended"


def test_any_batch_is_a_sign_of_life_even_without_a_heartbeat(client):
    """An agent older than M33 sends no heartbeat: online while it posts, state unknown."""
    post_events(client, [make_event()])
    d = fleet(client)["cam-001"]
    assert d["status"] == "online" and d["state"] is None


def test_alerts_by_level_and_last_event_in_the_period(client):
    now = datetime.now(UTC)
    post_events(
        client,
        [
            make_event(level=2, ts=iso(now - timedelta(hours=1))),
            make_event(level=3, type="drowsiness", reasons=["microsleep"], ts=iso(now - timedelta(minutes=30))),
            make_event(level=0, type="system", reasons=["camera_lost"], ts=iso(now - timedelta(minutes=5))),
            make_event(level=2, ts=iso(now - timedelta(days=2))),  # outside the asked day
        ],
    )
    d = fleet(client, since=iso(now - timedelta(hours=24)))["cam-001"]
    assert d["alerts_by_level"] == {"1": 0, "2": 1, "3": 1}  # the system event is not an alert
    assert d["last_event"]["reasons"] == ["camera_lost"] and d["last_event"]["type"] == "system"
    other = fleet(client, since=iso(now - timedelta(hours=24)))["cam-002"]
    assert other["alerts_by_level"] == {"1": 0, "2": 0, "3": 0} and other["last_event"] is None
    old = fleet(client, since=iso(now - timedelta(days=3)), until=iso(now - timedelta(days=1)))["cam-001"]
    assert old["alerts_by_level"] == {"1": 0, "2": 1, "3": 0}


def test_driver_sees_only_the_own_vehicle(client):
    beat(client)
    beat(client, device_id="cam-002", key=OTHER_DEVICE_KEY)
    assert set(fleet(client, "an")) == {"cam-001"}
    assert set(fleet(client, "binh")) == {"cam-002"}


def test_fleet_needs_a_login(client):
    assert client.get("/api/v1/fleet").status_code == 401


def test_browser_agent_appears_as_the_users_device(client):
    an = login(client, "an")
    heartbeat = {"ts": iso(), "trip_id": "trip-web-1", "state": "unavailable", "moving": None}
    r = client.post("/api/v1/web/events", json={"device_id": "web-an", "heartbeat": heartbeat}, headers=an)
    assert r.status_code == 200
    d = fleet(client)["web-an"]
    assert (d["status"], d["state"], d["driver_id"], d["moving"]) == ("online", "unavailable", "drv-001", None)


@pytest.mark.parametrize(
    "bad",
    [
        {"state": "sleeping"},  # not a known state
        {"frame": "x"},  # image-like field name
        {"lat": 10.7, "lon": 106.6},  # no position in a heartbeat
        {"ts": "2026-10-05T08:00:00"},  # timezone required
    ],
)
def test_heartbeat_is_strict(client, bad):
    assert beat(client, **bad).status_code == 422
    assert fleet(client)["cam-001"]["status"] == "never"


PERF = {
    "samples": 300,
    "stages_ms": {"total": {"p50": 10.5, "p95": 14.0, "max": 41.0}, "python": {"p50": 0.6, "p95": 0.9, "max": 4.0}},
    "landmarks_delegate": "CPU",
    "gpu": "software",
    "yolo_threads": 1,
    "camera_delivered": 303,
    "camera_dropped": 3,
}


def test_loop_timings_of_the_last_heartbeat_show_in_the_fleet(client):
    """M49: a slow hub says which stage is slow; a later heartbeat without timings keeps the last ones."""
    assert fleet(client)["cam-001"]["perf"] is None
    assert beat(client, perf=PERF).status_code == 200
    assert fleet(client)["cam-001"]["perf"] == PERF
    assert beat(client, state="camera_lost").status_code == 200
    assert fleet(client)["cam-001"]["perf"] == PERF


@pytest.mark.parametrize(
    "bad",
    [
        {**PERF, "stages_ms": {"gpu": {"p50": 1, "p95": 2, "max": 3}}},  # unknown stage
        {**PERF, "stages_ms": {"total": {"p50": -1, "p95": 2, "max": 3}}},  # negative time
        {**PERF, "frame": "x"},  # image-like field name
        {**PERF, "landmarks_delegate": "NPU"},
        {**PERF, "gpu": "fast"},
    ],
)
def test_loop_timings_are_strict(client, bad):
    assert beat(client, perf=bad).status_code == 422


def test_repeated_l1_is_an_accepted_reason(client):
    """M32: an L1 alert raised as L2 because it kept coming back."""
    e = make_event(type="drowsiness", level=2, reasons=["drowsy_score", "repeated_l1"])
    assert post_events(client, [e]).json()["accepted"] == 1
