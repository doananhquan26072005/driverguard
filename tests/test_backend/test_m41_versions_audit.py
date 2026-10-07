"""M41: versions on heartbeats and events, simulated / forced tags, and the access log."""

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from backend import db, manage
from backend.app import create_app
from backend.settings import BackendSettings
from tests.test_backend.conftest import OTHER_DEVICE_KEY, PASSWORD, login, make_event, post_events
from tests.test_backend.test_fleet import beat, fleet

VERSIONS = {
    "app": "3.0.0",
    "thresholds_version": 0,
    "thresholds_ignored": False,
    "models": {"landmarks": "0123456789ab", "phone": "ba9876543210"},
}


def log(client, user="admin", **params):
    r = client.get("/api/v1/access-log", headers=login(client, user), params=params)
    assert r.status_code == 200, r.text
    return r.json()


def actions(rows):
    return [(r["username"], r["action"], r["driver_id"]) for r in rows]


# ---------------------------------------------------------------- versions


def test_fleet_shows_what_each_device_runs_and_who_is_behind(client):
    beat(client, versions=VERSIONS)
    beat(client, device_id="cam-002", key=OTHER_DEVICE_KEY)  # an agent older than M41: no versions
    f = fleet(client)
    assert f["cam-001"]["versions"] == VERSIONS
    assert f["cam-001"]["thresholds_current"] is True and f["cam-001"]["thresholds_latest"] == 0
    assert f["cam-002"]["versions"] is None and f["cam-002"]["thresholds_current"] is None

    engineer = login(client, "admin")
    r = client.put("/api/v1/thresholds", json={"values": {"risk.drowsy.l1": 45}}, headers=engineer)
    assert r.status_code == 200 and r.json()["version"] == 1
    f = fleet(client)
    assert f["cam-001"]["thresholds_current"] is False and f["cam-001"]["thresholds_latest"] == 1  # behind
    beat(client, versions={**VERSIONS, "thresholds_version": 1})  # restarted: fetched version 1
    assert fleet(client)["cam-001"]["thresholds_current"] is True
    beat(client, versions={**VERSIONS, "thresholds_version": 0, "thresholds_ignored": True})
    assert fleet(client)["cam-001"]["thresholds_current"] is False  # it refused the tuned set


def test_a_heartbeat_without_versions_keeps_the_last_known_ones(client):
    beat(client, versions=VERSIONS)
    beat(client)
    assert fleet(client)["cam-001"]["versions"] == VERSIONS


def test_event_keeps_the_versions_and_tags_it_was_raised_under(client):
    e = make_event(tags=["simulated"], versions={**VERSIONS, "thresholds_version": 3})
    assert post_events(client, [e, make_event()]).json()["accepted"] == 2
    stored = {x["event_id"]: x for x in client.get("/api/v1/events", headers=login(client, "boss")).json()}
    assert stored[e["event_id"]]["tags"] == ["simulated"]
    assert stored[e["event_id"]]["versions"]["thresholds_version"] == 3
    other = next(x for k, x in stored.items() if k != e["event_id"])
    assert other["tags"] == [] and other["versions"] is None  # an older agent


@pytest.mark.parametrize(
    "bad",
    [
        {**VERSIONS, "models": {"phone": "not-hex-at-all"}},
        {**VERSIONS, "models": {"phone": "0123456789abcdef0123456789abcdef"}},  # a whole digest, not a short one
        {**VERSIONS, "models": {"Phone Model": "0123456789ab"}},
        {**VERSIONS, "app": "3.0.0 with a long free text that says anything at all"},
        {**VERSIONS, "notes": "free text"},
    ],
)
def test_versions_hold_no_free_text(client, bad):
    assert post_events(client, [make_event(versions=bad)]).status_code == 422
    assert beat(client, versions=bad).status_code == 422


def test_unknown_tag_is_refused(client):
    assert post_events(client, [make_event(tags=["real"])]).status_code == 422


# ---------------------------------------------------------------- forced states never reach a number


def test_forced_events_are_listed_but_never_counted(client):
    real = make_event(tags=["simulated"])
    forced = make_event(level=3, type="drowsiness", reasons=["microsleep"], tags=["simulated", "forced"])
    assert post_events(client, [real, forced]).json()["accepted"] == 2
    boss = login(client, "boss")
    listed = client.get("/api/v1/events", headers=boss).json()
    assert {e["event_id"] for e in listed} == {real["event_id"], forced["event_id"]}
    stats = client.get("/api/v1/stats", headers=boss).json()
    assert stats["total"] == 1 and stats["by_level"]["3"] == 0 and "microsleep" not in stats["by_reason"]
    assert fleet(client)["cam-001"]["alerts_by_level"] == {"1": 0, "2": 1, "3": 0}
    trips = client.get("/api/v1/trips", headers=boss).json()
    assert trips[0]["events"] == 1 and trips[0]["max_level"] == 2


# ---------------------------------------------------------------- access log


def test_reads_of_driver_data_are_logged_with_who_and_whose(client):
    boss = login(client, "boss")
    client.get("/api/v1/events?driver_id=drv-001", headers=boss)
    client.get("/api/v1/stats", headers=boss)
    client.get("/api/v1/fleet", headers=boss)
    rows = log(client)
    assert ("boss", "read_events", "drv-001") in actions(rows)
    assert ("boss", "read_stats", None) in actions(rows) and ("boss", "read_fleet", None) in actions(rows)
    assert all(r["role"] == "manager" for r in rows if r["username"] == "boss")
    assert [r["username"] for r in log(client, driver_id="drv-001")] == ["boss"]
    assert actions(log(client))[0] == ("admin", "read_access_log", "drv-001")  # reading the log is logged too


def test_the_same_read_is_logged_once_per_window_and_changes_always(client):
    boss = login(client, "boss")
    for _ in range(5):  # the dashboard polls
        client.get("/api/v1/fleet", headers=boss)
        client.get("/api/v1/events?driver_id=drv-001", headers=boss)
    client.get("/api/v1/events?driver_id=drv-002", headers=boss)  # another driver: a new row
    rows = [a for a in actions(log(client)) if a[0] == "boss"]
    assert sorted(rows, key=str) == sorted(
        [("boss", "read_fleet", None), ("boss", "read_events", "drv-001"), ("boss", "read_events", "drv-002")], key=str
    )
    admin = login(client, "admin")
    for value in (45, 46):
        client.put("/api/v1/thresholds", json={"values": {"risk.drowsy.l1": value}}, headers=admin)
    changes = [r for r in log(client) if r["action"] == "update_thresholds"]
    assert [r["detail"] for r in changes] == ["version 2: risk.drowsy.l1", "version 1: risk.drowsy.l1"]


def test_drivers_reading_their_own_data_are_not_logged(client):
    an = login(client, "an")
    client.get("/api/v1/events", headers=an)
    client.get("/api/v1/stats", headers=an)
    assert [r for r in log(client) if r["username"] == "an"] == []


def test_a_driver_sees_who_looked_at_their_data(client):
    boss = login(client, "boss")
    client.get("/api/v1/events?driver_id=drv-001", headers=boss)  # names an
    client.get("/api/v1/trips?driver_id=drv-002", headers=boss)  # names binh only
    client.get("/api/v1/stats", headers=boss)  # the whole fleet: includes both
    mine = client.get("/api/v1/access-log/mine", headers=login(client, "an"))
    assert mine.status_code == 200
    assert sorted(actions(mine.json()), key=str) == sorted(
        [("boss", "read_events", "drv-001"), ("boss", "read_stats", None)], key=str
    )
    binh = client.get("/api/v1/access-log/mine", headers=login(client, "binh")).json()
    assert ("boss", "read_trips", "drv-002") in actions(binh) and ("boss", "read_events", "drv-001") not in actions(
        binh
    )


def test_only_admins_read_the_whole_log(client):
    for user in ("boss", "an"):
        assert client.get("/api/v1/access-log", headers=login(client, user)).status_code == 403
    assert client.get("/api/v1/access-log/mine", headers=login(client, "boss")).status_code == 403
    assert client.get("/api/v1/access-log").status_code == 401


def test_trip_report_reads_name_the_driver_of_the_report(client):
    from tests.test_backend.test_trip_reports import send, summary

    send(client, summary("trip-a"))
    boss = login(client, "boss")
    client.get("/api/v1/trip-reports/cam-001/trip-a", headers=boss)
    client.post("/api/v1/trip-reports/cam-001/trip-a/review", headers=boss)
    rows = {r["action"]: r for r in log(client) if r["username"] == "boss"}
    assert rows["read_trip_report"]["driver_id"] == "drv-001" and rows["read_trip_report"]["device_id"] == "cam-001"
    assert rows["review_trip_report"]["detail"] == "trip trip-a"


def test_account_and_device_creation_are_logged(client):
    admin = login(client, "admin")
    user = {"username": "chi", "password": PASSWORD, "role": "driver", "driver_id": "drv-003"}
    assert client.post("/api/v1/users", json=user, headers=admin).status_code == 201
    assert (
        client.post("/api/v1/devices", json={"device_id": "cam-003", "driver_id": "drv-003"}, headers=admin).status_code
        == 201
    )
    rows = {r["action"]: r for r in log(client)}
    assert rows["create_user"]["detail"] == "driver chi" and rows["create_user"]["driver_id"] == "drv-003"
    assert rows["create_device"]["device_id"] == "cam-003"
    assert PASSWORD not in str(log(client))


def test_the_log_cannot_be_rewritten(client, settings):
    client.get("/api/v1/stats", headers=login(client, "boss"))
    with db.closing(settings.db_path) as conn, pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("UPDATE access_log SET username = 'nobody'")
    methods = {(m, r.path) for r in client.app.routes for m in getattr(r, "methods", ())}
    assert [m for m, path in methods if path.startswith("/api/v1/access-log")] == ["GET", "GET"]


def test_the_log_has_its_own_retention_period(tmp_path):
    settings = BackendSettings(db_path=str(tmp_path / "t.db"), jwt_secret="t" * 48, retention_access_log_days=30)
    create_app(settings)
    now = datetime.now(UTC)
    with db.closing(settings.db_path) as conn:
        db.log_access(conn, "boss", "manager", "read_stats")
        db.log_access(conn, "boss", "manager", "read_fleet")
        conn.execute("DROP TRIGGER access_log_append_only")  # only to age a row for this test
        conn.execute(
            "UPDATE access_log SET ts = ? WHERE action = 'read_stats'", ((now - timedelta(days=31)).isoformat(),)
        )
        deleted = db.purge_expired(conn, now, 60, 365, settings.retention_access_log_days)
        assert deleted["access_log"] == 1
        assert [r["action"] for r in db.query_access_log(conn)] == ["read_fleet"]
        assert "access_log" not in db.purge_expired(conn, now, 60, 365)  # 0 days: kept


def test_cli_deletion_is_logged(tmp_path, monkeypatch, capsys):
    path = str(tmp_path / "t.db")
    monkeypatch.setenv("DG_DB_PATH", path)
    assert manage.main(["--db", path, "delete-driver-data", "drv-001", "--yes"]) == 0
    assert manage.main(["--db", path, "purge"]) == 0
    with db.closing(path) as conn:
        rows = db.query_access_log(conn)
    assert [(r["username"], r["action"], r["driver_id"]) for r in rows] == [
        ("cli", "purge_expired", None),
        ("cli", "delete_driver_data", "drv-001"),
    ]


def test_old_database_gets_the_new_columns(tmp_path):
    path = str(tmp_path / "old.db")
    conn = sqlite3.connect(path)
    conn.executescript(db.SCHEMA)
    conn.executescript(
        "ALTER TABLE events DROP COLUMN tags; ALTER TABLE events DROP COLUMN versions;"
        "ALTER TABLE device_status DROP COLUMN versions; DROP TABLE access_log;"
    )
    conn.commit()
    conn.close()
    db.init_db(path)
    with db.closing(path) as conn:
        assert {"tags", "versions"} <= {r[1] for r in conn.execute("PRAGMA table_info(events)")}
        assert "versions" in {r[1] for r in conn.execute("PRAGMA table_info(device_status)")}
        db.log_access(conn, "boss", "manager", "read_stats")
