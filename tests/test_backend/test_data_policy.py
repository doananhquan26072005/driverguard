"""Data policy (M37, docs/data-policy.md): retention purge, deleting one driver's data, and the texts
that state the retention period. Fake rows with old timestamps, no device."""

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

from backend import db, manage
from backend.settings import BackendSettings
from tests.test_backend.conftest import OTHER_DEVICE_KEY, login, make_event, post_events

ROOT = Path(__file__).resolve().parents[2]


def ago(**kw):
    return (datetime.now(UTC) - timedelta(**kw)).isoformat()


def sample(ts):
    return {"sample_id": None, "ts": ts, "trip_id": "trip-1", "drowsy_score": 10.0, "perclos_60s": 0.02, "max_level": 0}


def summary(started):
    return {"trip_id": f"trip-{started[:10]}", "started_at": started, "rating": "good"}


def seed(settings, driver="drv-001", device="cam-001"):
    """Old and recent rows of every kind, written straight to the database."""
    import uuid

    with db.closing(settings.db_path) as conn:
        for days in (1, 59, 61, 400):
            e = make_event(ts=ago(days=days), event_id=str(uuid.uuid4()))
            db.insert_event(conn, device, driver, e)
            db.insert_sample(conn, device, driver, {**sample(ago(days=days)), "sample_id": str(uuid.uuid4())})
            db.upsert_summary(conn, device, driver, summary(ago(days=days)))
        db.touch_device(conn, device, driver)


def counts(settings, where="1=1", args=()):
    with db.closing(settings.db_path) as conn:
        return {
            t: conn.execute(f"SELECT COUNT(*) FROM {t} WHERE {where}", args).fetchone()[0]
            for t in ("events", "fatigue_samples", "trip_summaries")
        }


def test_purge_deletes_only_what_is_past_its_period(settings):
    db.init_db(settings.db_path)
    seed(settings)
    with db.closing(settings.db_path) as conn:
        deleted = db.purge_expired(conn, datetime.now(UTC), events_days=60, summaries_days=365)
    assert deleted == {"events": 2, "fatigue_samples": 2, "trip_summaries": 1}
    assert counts(settings) == {"events": 2, "fatigue_samples": 2, "trip_summaries": 3}


def test_zero_days_keeps_everything(settings):
    db.init_db(settings.db_path)
    seed(settings)
    with db.closing(settings.db_path) as conn:
        assert not any(db.purge_expired(conn, datetime.now(UTC), 0, 0).values())
    assert counts(settings) == {"events": 4, "fatigue_samples": 4, "trip_summaries": 4}


def test_backend_purges_at_start_up(settings):
    from backend.app import create_app

    db.init_db(settings.db_path)
    seed(settings)
    create_app(settings)
    assert counts(settings) == {"events": 2, "fatigue_samples": 2, "trip_summaries": 3}


def test_backend_purges_again_once_a_day_when_devices_post(client, settings):
    seed(settings)  # after start-up: the old rows are there
    post_events(client, [make_event()])
    assert counts(settings)["events"] == 5  # purged less than a day ago: not yet
    client.app.state.next_purge = 0.0  # a day later
    post_events(client, [make_event()])
    assert counts(settings) == {"events": 4, "fatigue_samples": 2, "trip_summaries": 3}


def test_policy_endpoint_gives_the_configured_periods(client, settings):
    assert client.get("/api/v1/policy").json() == {"retention_events_days": 60, "retention_summaries_days": 365}
    settings.retention_events_days = 30
    assert client.get("/api/v1/policy").json()["retention_events_days"] == 30


def test_delete_driver_data_removes_one_driver_only(client, settings):
    seed(settings)
    seed(settings, driver="drv-002", device="cam-002")
    with db.closing(settings.db_path) as conn:
        deleted = db.delete_driver_data(conn, "drv-001")
    assert deleted == {"events": 4, "fatigue_samples": 4, "trip_summaries": 4, "device_status": 1}
    assert counts(settings, "driver_id = ?", ("drv-001",)) == {"events": 0, "fatigue_samples": 0, "trip_summaries": 0}
    assert counts(settings, "driver_id = ?", ("drv-002",))["events"] == 4
    assert client.post("/auth/login", json={"username": "an", "password": "correct-horse-1"}).status_code == 200


def test_manage_delete_driver_data_needs_yes(client, settings, capsys):
    seed(settings)
    assert manage.main(["--db", settings.db_path, "delete-driver-data", "drv-001"]) == 1
    assert counts(settings)["events"] == 4
    assert manage.main(["--db", settings.db_path, "delete-driver-data", "drv-001", "--yes"]) == 0
    assert counts(settings)["events"] == 0 and "drv-001" in capsys.readouterr().out


def test_manage_purge_uses_the_configured_periods(settings, capsys):
    db.init_db(settings.db_path)
    seed(settings)
    assert manage.main(["--db", settings.db_path, "purge"]) == 0
    assert counts(settings) == {"events": 2, "fatigue_samples": 2, "trip_summaries": 3}


def test_driver_can_read_everything_stored_about_them(client):
    """Right of access: the driver's own events, timeline, trips and reports, nobody else's."""
    post_events(client, [make_event()])
    post_events(client, [make_event()], device_id="cam-002", key=OTHER_DEVICE_KEY)
    an = login(client, "an")
    for path in ("/api/v1/events", "/api/v1/trips", "/api/v1/trip-reports", "/api/v1/fleet"):
        rows = client.get(path, headers=an).json()
        assert all(r["driver_id"] == "drv-001" for r in rows), path
    assert len(client.get("/api/v1/events", headers=an).json()) == 1


def test_consent_screen_and_policy_state_the_backend_defaults():
    """The driver is told a period: it must be the one the backend applies by default."""
    s = BackendSettings()
    labels = (ROOT / "frontend/src/lib/labels.ts").read_text(encoding="utf-8")
    m = re.search(r"RETENTION_DAYS = \{ events: (\d+), summaries: (\d+) \}", labels)
    assert m and (int(m[1]), int(m[2])) == (s.retention_events_days, s.retention_summaries_days)
    assert "${RETENTION_DAYS.events}" in labels and "${RETENTION_DAYS.summaries}" in labels
    policy = (ROOT / "docs/data-policy.md").read_text(encoding="utf-8")
    assert f"**{s.retention_events_days} ngày**" in policy and f"**{s.retention_summaries_days} ngày**" in policy
