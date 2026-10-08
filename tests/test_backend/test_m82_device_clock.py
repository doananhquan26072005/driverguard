"""M82: the backend does not rely on the device's clock (audit 08/10, A4 M2 / X7).

Fake heartbeat and event sequences from a device whose clock is fast, slow or at 1970: the order of
heartbeats, "needs attention now" and the retention purge run on the server's clock; the skew is
stored and shown. Trip ids carry a random part (A4 L1). No device.
"""

import re
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from backend import db
from edge_agent.runtime import new_trip_id
from tests.test_backend.conftest import DEVICE_KEY, make_event
from tests.test_backend.test_fleet import beat, fleet, iso
from tests.test_backend.test_trip_reports import summary as trip_summary

HEADERS = {"X-Device-Key": DEVICE_KEY}


def device_now(**off):
    """What a device whose clock is off by `off` (timedelta arguments) calls now."""
    return iso(datetime.now(UTC) + timedelta(**off))


def l3(ts, trip="trip-1", **over):
    return make_event(type="drowsiness", level=3, reasons=["unresponsive", "microsleep"], trip_id=trip, ts=ts, **over)


def post(client, *events, **extra):
    r = client.post("/api/v1/events", json={"device_id": "cam-001", "events": list(events), **extra}, headers=HEADERS)
    assert r.status_code == 200, r.text


def rows(settings, table):
    with db.closing(settings.db_path) as conn:
        return [dict(r) for r in conn.execute(f"SELECT * FROM {table}")]


def age_rows(settings, days):
    """As if everything stored arrived `days` ago."""
    at = iso(datetime.now(UTC) - timedelta(days=days))
    with db.closing(settings.db_path) as conn:
        for table in ("events", "fatigue_samples", "trip_summaries"):
            conn.execute(f"UPDATE {table} SET received_at = ?", (at,))


# --------------------------------------------------------------------------- heartbeat order


def test_a_trip_ended_on_a_fast_clock_does_not_hide_the_next_trip(client):
    """Audit: `ended` with the clock a day ahead, the clock is then set right, a new trip starts."""
    beat(client, "ended", ts=device_now(days=1))
    assert fleet(client)["cam-001"]["status"] == "ended"
    beat(client, "monitoring", trip_id="trip-2")  # the right time: a day "older" for the device
    d = fleet(client)["cam-001"]
    assert (d["status"], d["state"], d["trip_id"]) == ("online", "monitoring", "trip-2")


@pytest.mark.parametrize("off", [{"days": -20000}, {"minutes": -10}, {"hours": 7}])
def test_every_heartbeat_is_taken_in_the_order_it_arrives(client, off):
    for state in ("monitoring", "camera_lost", "monitoring", "ended"):
        beat(client, state, ts=device_now(**off))
        assert fleet(client)["cam-001"]["state"] == state


# --------------------------------------------------------------------------- clock skew, stored and shown


def test_a_right_clock_is_not_marked(client):
    beat(client)
    d = fleet(client)["cam-001"]
    assert d["clock_wrong"] is False and abs(d["clock_skew_s"]) < 5


def test_no_heartbeat_yet_means_nothing_is_known_about_the_clock(client):
    post(client, make_event())
    d = fleet(client)["cam-001"]
    assert d["clock_skew_s"] is None and d["clock_wrong"] is None
    assert fleet(client)["cam-002"]["clock_wrong"] is None  # never heard from


@pytest.mark.parametrize(("off", "skew_s"), [({"minutes": -10}, 600), ({"days": 1}, -86400), ({"seconds": -60}, 60)])
def test_the_skew_of_the_last_heartbeat_is_stored_and_marked_past_the_limit(client, off, skew_s):
    beat(client, ts=device_now(**off))
    d = fleet(client)["cam-001"]
    assert d["clock_skew_s"] == pytest.approx(skew_s, abs=5)
    assert d["clock_wrong"] is (abs(skew_s) > 120)  # DG_CLOCK_SKEW_WARN_S


def test_the_limit_comes_from_settings_and_the_mark_goes_when_the_clock_is_set(client, settings):
    settings.clock_skew_warn_s = 30
    beat(client, ts=device_now(seconds=-60))
    assert fleet(client)["cam-001"]["clock_wrong"] is True
    beat(client)
    assert fleet(client)["cam-001"]["clock_wrong"] is False


def test_the_device_time_of_an_event_is_kept_as_sent(client, settings):
    """`ts` is what the device said (for display); the arrival is stored next to it."""
    beat(client, ts=device_now(minutes=-10))
    event = l3(device_now(minutes=-10))
    post(client, event)
    (row,) = rows(settings, "events")
    assert datetime.fromisoformat(row["ts"]) == datetime.fromisoformat(event["ts"])
    late_s = (datetime.fromisoformat(row["received_at"]) - datetime.fromisoformat(row["ts"])).total_seconds()
    assert late_s == pytest.approx(600, abs=5) and row["delay_s"] == pytest.approx(0, abs=5)


# --------------------------------------------------------------------------- "needs attention now"


@pytest.mark.parametrize("off", [{"minutes": -10}, {"days": -20000}, {"minutes": 10}, {"days": 1}])
def test_an_l3_just_received_is_urgent_whatever_the_device_clock_says(client, off):
    """Audit: a clock 10 minutes behind, and the L3 `unresponsive` just received was not shown."""
    beat(client, ts=device_now(**off))
    event = l3(device_now(**off))
    post(client, event)
    assert fleet(client)["cam-001"]["urgent"]["event_id"] == event["event_id"]


def test_an_l3_before_any_heartbeat_is_urgent_on_arrival_alone(client):
    """Nothing known about the clock yet: the arrival decides (rather show it than hide it)."""
    event = l3(device_now(minutes=-10))
    post(client, event)
    beat(client, ts=device_now(minutes=-10))
    assert fleet(client)["cam-001"]["urgent"]["event_id"] == event["event_id"]


@pytest.mark.parametrize("off", [{}, {"minutes": -10}, {"days": 1}])
def test_an_old_l3_from_the_offline_queue_is_not_urgent(client, settings, off):
    """Held on the device for 15 minutes (no network), then delivered: history, on any clock."""
    beat(client, ts=device_now(**off))
    post(client, l3(iso(datetime.now(UTC) + timedelta(**off) - timedelta(minutes=15))))
    assert fleet(client)["cam-001"]["urgent"] is None
    (row,) = rows(settings, "events")
    assert row["delay_s"] == pytest.approx(900, abs=5)


def test_urgent_ends_with_the_window_on_the_server_clock(client, settings):
    beat(client, ts=device_now(days=1))
    post(client, l3(device_now(days=1)))  # the device says: tomorrow
    assert fleet(client)["cam-001"]["urgent"] is not None
    with db.closing(settings.db_path) as conn:
        conn.execute("UPDATE events SET received_at = ?", (iso(datetime.now(UTC) - timedelta(seconds=301)),))
    assert fleet(client)["cam-001"]["urgent"] is None


def test_the_newest_urgent_event_is_the_one_that_arrived_last(client):
    beat(client)
    first, second = l3(iso()), l3(iso(datetime.now(UTC) - timedelta(seconds=30)))  # device times reversed
    post(client, first)
    post(client, second)
    assert fleet(client)["cam-001"]["urgent"]["event_id"] == second["event_id"]


# --------------------------------------------------------------------------- retention


def sample(ts):
    return {"sample_id": str(uuid.uuid4()), "ts": ts, "trip_id": "trip-1", "drowsy_score": 10.0, "max_level": 0}


def summary(started):
    return {**trip_summary(), "started_at": started, "ended_at": started}


def counts(settings):
    return {t: len(rows(settings, t)) for t in ("events", "fatigue_samples", "trip_summaries")}


def purge(settings):
    with db.closing(settings.db_path) as conn:
        return db.purge_expired(conn, datetime.now(UTC), events_days=60, summaries_days=365)


def test_rows_dated_1970_by_the_device_are_not_deleted_at_the_first_purge(client, settings):
    """Audit: an event carrying 1970 was deleted the first time the purge ran."""
    at = "1970-01-01T00:05:00+00:00"
    post(client, make_event(ts=at), samples=[sample(at)], summaries=[summary(at)])
    assert not any(purge(settings).values())
    assert counts(settings) == {"events": 1, "fatigue_samples": 1, "trip_summaries": 1}


def test_rows_dated_in_the_future_by_the_device_still_expire(client, settings):
    """Audit: a `ts` in the future outlived the retention period."""
    at = device_now(days=3650)
    post(client, make_event(ts=at), samples=[sample(at)], summaries=[summary(at)])
    age_rows(settings, 61)
    assert purge(settings) == {"events": 1, "fatigue_samples": 1, "trip_summaries": 0}
    age_rows(settings, 366)
    assert purge(settings)["trip_summaries"] == 1
    assert counts(settings) == {"events": 0, "fatigue_samples": 0, "trip_summaries": 0}


def test_the_period_runs_from_the_arrival(client, settings):
    post(client, make_event(), samples=[sample(iso())], summaries=[summary(iso())])
    age_rows(settings, 59)
    assert not any(purge(settings).values())
    age_rows(settings, 61)
    assert purge(settings) == {"events": 1, "fatigue_samples": 1, "trip_summaries": 0}


# --------------------------------------------------------------------------- a database from before M82


def test_an_older_database_gets_the_new_columns_and_its_samples_an_arrival_time(tmp_path):
    path = str(tmp_path / "old.db")
    db.init_db(path)
    past, future = iso(datetime.now(UTC) - timedelta(days=3)), iso(datetime.now(UTC) + timedelta(days=900))
    conn = sqlite3.connect(path)
    for table, col in (("events", "delay_s"), ("device_status", "clock_skew_s"), ("fatigue_samples", "received_at")):
        conn.execute(f"ALTER TABLE {table} DROP COLUMN {col}")
    for ts in (past, future):
        conn.execute(
            "INSERT INTO fatigue_samples (sample_id, device_id, trip_id, ts, drowsy_score, max_level) "
            "VALUES (?, 'cam-001', 'trip-1', ?, 10.0, 0)",
            (str(uuid.uuid4()), ts),
        )
    conn.commit()
    conn.close()
    db.init_db(path)
    with db.closing(path) as conn:
        got = {r["ts"]: r["received_at"] for r in conn.execute("SELECT ts, received_at FROM fatigue_samples")}
        assert got[past] == past  # its own time
        assert datetime.fromisoformat(got[future]) <= datetime.now(UTC)  # never an arrival in the future
        assert db.device_clock_skew(conn, "cam-001") is None
        db.insert_event(conn, "cam-001", None, make_event())  # the new column is there


# --------------------------------------------------------------------------- trip id (A4 L1)


def test_trip_id_keeps_the_readable_time_and_adds_a_random_part():
    trip = new_trip_id(datetime(2026, 10, 8, 7, 5, 9))
    assert re.fullmatch(r"trip-20261008-070509-[0-9a-f]{6}", trip)
    assert re.fullmatch(r"[A-Za-z0-9_.-]{1,48}", trip)  # backend/schemas.py Identifier


def test_two_trips_started_in_the_same_second_have_different_ids():
    at = datetime(2026, 10, 8, 7, 5, 9)
    assert len({new_trip_id(at) for _ in range(200)}) == 200


def test_summaries_of_two_trips_in_the_same_second_do_not_overwrite_each_other(client, settings):
    """The clock went back (or the time zone changed): the same local second, twice."""
    at = datetime(2026, 10, 8, 7, 5, 9)
    for trip in (new_trip_id(at), new_trip_id(at)):
        post(client, summaries=[{**summary(iso()), "trip_id": trip}])
    assert counts(settings)["trip_summaries"] == 2
