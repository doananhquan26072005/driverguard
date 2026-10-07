"""M44: the fleet overview says which vehicle needs attention now (L3, unresponsive, repeated_l3,
no_answer), from fake event sequences."""

from datetime import UTC, datetime, timedelta

from edge_agent.io.publisher import build_system_event
from tests.test_backend.conftest import DEVICE_KEY, make_event
from tests.test_backend.test_fleet import age_last_seen, beat, fleet, iso

HEADERS = {"X-Device-Key": DEVICE_KEY}


def post(client, *events):
    r = client.post("/api/v1/events", json={"device_id": "cam-001", "events": list(events)}, headers=HEADERS)
    assert r.status_code == 200, r.text


def l3(reasons=("microsleep",), trip="trip-1", ts=None, **over):
    return make_event(type="drowsiness", level=3, reasons=list(reasons), trip_id=trip, ts=ts or iso(), **over)


def test_nothing_urgent_on_a_quiet_trip_or_for_l2(client):
    beat(client)
    post(client, make_event(trip_id="trip-1", ts=iso()))  # L2 phone
    assert fleet(client)["cam-001"]["urgent"] is None


def test_l3_and_the_new_reasons_are_urgent_newest_first(client):
    beat(client)
    old = l3(ts=iso(datetime.now(UTC) - timedelta(seconds=60)))
    post(client, old)
    got = fleet(client)["cam-001"]["urgent"]
    assert got["reasons"] == ["microsleep"] and got["event_id"] == old["event_id"]
    post(client, l3(("unresponsive", "microsleep")))
    assert fleet(client)["cam-001"]["urgent"]["reasons"] == ["unresponsive", "microsleep"]
    silent = build_system_event("no_answer", "trip-1", 60.0)
    post(client, silent)
    got = fleet(client)["cam-001"]["urgent"]
    assert got["reasons"] == ["no_answer"] and got["type"] == "system" and got["event_id"] == silent["event_id"]


def test_old_alerts_other_trips_and_forced_states_are_not_urgent(client):
    beat(client)
    post(client, l3(ts=iso(datetime.now(UTC) - timedelta(seconds=900))))  # older than the 300 s window
    post(client, l3(trip="trip-0"))  # an earlier trip of the same device
    post(client, l3(tags=["forced"]))  # set by hand: never a real alert
    assert fleet(client)["cam-001"]["urgent"] is None


def test_a_vehicle_that_went_quiet_or_ended_shows_its_status_instead(client, settings):
    beat(client)
    post(client, l3())
    assert fleet(client)["cam-001"]["urgent"] is not None
    age_last_seen(settings, "cam-001", 600)
    lost = fleet(client)["cam-001"]
    assert lost["status"] == "offline" and lost["urgent"] is None
    beat(client, state="ended")
    assert fleet(client)["cam-001"]["urgent"] is None


def test_a_driver_only_sees_urgent_of_their_own_vehicle(client):
    beat(client)
    post(client, l3())
    assert set(fleet(client, "binh")) == {"cam-002"}
    assert fleet(client, "an")["cam-001"]["urgent"]["level"] == 3


def test_made_up_reason_is_still_refused(client):
    bad = make_event(reasons=["asleep_for_sure"])
    r = client.post("/api/v1/events", json={"device_id": "cam-001", "events": [bad]}, headers=HEADERS)
    assert r.status_code == 422
