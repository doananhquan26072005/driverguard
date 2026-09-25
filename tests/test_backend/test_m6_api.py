"""M6 backend: engineer role, false-alarm feedback, fatigue timeline, stats, thresholds, migration."""

import sqlite3
import uuid

import pytest

from backend import db
from backend.security import hash_password
from tests.test_backend.conftest import DEVICE_KEY, OTHER_DEVICE_KEY, PASSWORD, login, make_event


@pytest.fixture
def engineer(client, settings):
    with db.closing(settings.db_path) as conn:
        db.create_user(conn, "kysu", hash_password(PASSWORD), "engineer", None)
    return login(client, "kysu")


def batch(client, key=DEVICE_KEY, device_id="cam-001", **parts):
    body = {"device_id": device_id, **parts}
    return client.post("/api/v1/events", json=body, headers={"X-Device-Key": key})


def sample(minute, score, trip="trip-a", level=0):
    return {
        "sample_id": str(uuid.uuid4()),
        "ts": f"2026-09-24T08:{minute:02d}:00+00:00",
        "trip_id": trip,
        "drowsy_score": score,
        "perclos_60s": 0.05,
        "max_level": level,
    }


def feedback(event_id):
    return {"event_id": event_id, "verdict": "false_alarm", "ts": "2026-09-24T08:05:00+00:00"}


# ---------------------------------------------------------------- engineer role


def test_engineer_logs_in_and_reads_everything(client, engineer):
    assert client.get("/auth/me", headers=engineer).json()["role"] == "engineer"
    batch(client, events=[make_event()])
    batch(client, OTHER_DEVICE_KEY, "cam-002", events=[make_event()])
    assert len(client.get("/api/v1/events", headers=engineer).json()) == 2
    assert client.get("/api/v1/users", headers=engineer).status_code == 403  # accounts stay admin-only


def test_admin_can_create_engineer(client):
    body = {"username": "kysu2", "password": "long-enough-1", "role": "engineer"}
    assert client.post("/api/v1/users", json=body, headers=login(client, "admin")).status_code == 201


# ---------------------------------------------------------------- false-alarm feedback


def test_false_alarm_feedback_marks_the_event(client):
    e = make_event()
    batch(client, events=[e])
    r = batch(client, feedback=[feedback(e["event_id"])])
    assert r.status_code == 200 and r.json()["feedback_applied"] == 1
    stored = client.get("/api/v1/events", headers=login(client, "boss")).json()[0]
    assert stored["feedback"] == "false_alarm" and stored["feedback_at"].startswith("2026-09-24T08:05")


def test_event_and_its_feedback_in_the_same_batch(client):
    e = make_event()
    assert batch(client, events=[e], feedback=[feedback(e["event_id"])]).json()["feedback_applied"] == 1


def test_device_cannot_flag_another_devices_event(client):
    e = make_event()
    batch(client, OTHER_DEVICE_KEY, "cam-002", events=[e])
    assert batch(client, feedback=[feedback(e["event_id"])]).json()["feedback_applied"] == 0


def test_false_alarm_filter_and_stats(client):
    events = [make_event(reasons=["phone"]), make_event(reasons=["phone"]), make_event(level=3, reasons=["microsleep"])]
    batch(client, events=events, feedback=[feedback(events[0]["event_id"])])
    boss = login(client, "boss")
    flagged = client.get("/api/v1/events?false_alarm_only=true", headers=boss).json()
    assert [e["event_id"] for e in flagged] == [events[0]["event_id"]]
    stats = client.get("/api/v1/stats", headers=boss).json()
    assert stats["total"] == 3 and stats["false_alarms"] == 1
    assert stats["by_level"] == {"0": 0, "1": 0, "2": 2, "3": 1}
    assert stats["by_reason"]["phone"] == {"total": 2, "false_alarms": 1}


def test_feedback_payload_is_strict(client):
    bad = {"event_id": str(uuid.uuid4()), "verdict": "annoying", "ts": "2026-09-24T08:05:00+00:00"}
    assert batch(client, feedback=[bad]).status_code == 422
    bad = {**feedback(str(uuid.uuid4())), "note": "the camera was covered"}
    assert batch(client, feedback=[bad]).status_code == 422


# ---------------------------------------------------------------- fatigue timeline


def test_samples_build_the_timeline(client):
    e = make_event(ts="2026-09-24T08:02:30+00:00", trip_id="trip-a")
    r = batch(client, samples=[sample(m, 10.0 * m) for m in range(1, 5)], events=[e])
    assert r.json()["samples_accepted"] == 4
    tl = client.get("/api/v1/timeline?trip_id=trip-a", headers=login(client, "boss")).json()
    assert [s["drowsy_score"] for s in tl["samples"]] == [10.0, 20.0, 30.0, 40.0]  # oldest first
    assert [x["event_id"] for x in tl["events"]] == [e["event_id"]]
    assert tl["samples"][0]["driver_id"] == "drv-001"


def test_samples_are_idempotent(client):
    s = [sample(1, 5.0)]
    batch(client, samples=s)
    assert batch(client, samples=s).json()["samples_accepted"] == 0


def test_timeline_time_window(client):
    batch(client, samples=[sample(m, float(m)) for m in range(10)])
    url = "/api/v1/timeline?since=2026-09-24T08:03:00Z&until=2026-09-24T08:05:00Z"
    tl = client.get(url, headers=login(client, "boss")).json()
    assert [s["drowsy_score"] for s in tl["samples"]] == [3.0, 4.0, 5.0]


def test_trips_list(client):
    batch(client, samples=[sample(1, 5.0, "trip-a"), sample(9, 5.0, "trip-a")], events=[make_event(trip_id="trip-a")])
    batch(client, OTHER_DEVICE_KEY, "cam-002", samples=[sample(3, 5.0, "trip-b", level=3)])
    trips = {t["trip_id"]: t for t in client.get("/api/v1/trips", headers=login(client, "boss")).json()}
    assert set(trips) == {"trip-a", "trip-b"}
    assert trips["trip-a"]["events"] == 1 and trips["trip-b"]["max_level"] == 3


def test_driver_sees_only_own_timeline_trips_and_stats(client):
    batch(client, samples=[sample(1, 5.0, "trip-a")], events=[make_event(trip_id="trip-a")])
    batch(
        client, OTHER_DEVICE_KEY, "cam-002", samples=[sample(1, 90.0, "trip-b")], events=[make_event(trip_id="trip-b")]
    )
    an = login(client, "an")
    assert {t["trip_id"] for t in client.get("/api/v1/trips?driver_id=drv-002", headers=an).json()} == {"trip-a"}
    tl = client.get("/api/v1/timeline?trip_id=trip-b", headers=an).json()
    assert tl == {"samples": [], "events": []}
    assert client.get("/api/v1/stats", headers=an).json()["total"] == 1


def test_image_data_in_samples_or_feedback_rejected(client):
    jpeg = "/9j/4AAQSkZJRgABAQAAAQABAAD" + "A" * 80
    assert batch(client, samples=[{**sample(1, 5.0), "trip_id": jpeg}]).status_code == 422
    assert batch(client, samples=[{**sample(1, 5.0), "frame": "x"}]).status_code == 422
    assert batch(client, feedback=[{**feedback(str(uuid.uuid4())), "snapshot": "x"}]).status_code == 422


def test_empty_batch_rejected(client):
    assert batch(client).status_code == 422


# ---------------------------------------------------------------- thresholds


def test_thresholds_start_empty_with_specs(client, engineer):
    t = client.get("/api/v1/thresholds", headers=engineer).json()
    assert t["version"] == 0 and t["values"] == {}
    assert t["specs"]["risk.drowsy.l1"] == {"min": 5.0, "max": 100.0, "unit": "score"}


def test_engineer_saves_versions(client, engineer):
    r = client.put("/api/v1/thresholds", json={"values": {"risk.drowsy.l1": 45}}, headers=engineer)
    assert r.status_code == 200 and r.json()["version"] == 1 and r.json()["updated_by"] == "kysu"
    r = client.put("/api/v1/thresholds", json={"values": {"alert.cooldown_s.2": 60}}, headers=engineer)
    assert r.json()["version"] == 2
    assert r.json()["values"] == {"risk.drowsy.l1": 45.0, "alert.cooldown_s.2": 60.0}  # merged


@pytest.mark.parametrize(
    "values",
    [
        {"risk.drowsy.l1": 150},  # out of bounds
        {"risk.drowsy.l1": 80, "risk.drowsy.l2": 70},  # l1 must stay below l2
        {"risk.distraction.off_road_s": 1.0, "risk.distraction.off_road_high_speed_s": 2.0},
        {"drowsiness.microsleep_min_s": 5.0, "risk.microsleep_l3_s": 0.5},  # event after the L3 rule
        {"risk.drowsy.l1": 75},  # above the YAML l2 of 70 (not overridden)
        {"capture.camera_fps": 5},  # not a tunable key
        {},
    ],
)
def test_invalid_thresholds_rejected(client, engineer, values):
    assert client.put("/api/v1/thresholds", json={"values": values}, headers=engineer).status_code == 422


def test_who_may_tune(client, engineer):
    body = {"values": {"risk.drowsy.l1": 45}}
    assert client.put("/api/v1/thresholds", json=body, headers=login(client, "boss")).status_code == 403
    assert client.put("/api/v1/thresholds", json=body, headers=login(client, "an")).status_code == 403
    assert client.get("/api/v1/thresholds", headers=login(client, "boss")).status_code == 200
    assert client.get("/api/v1/thresholds", headers=login(client, "an")).status_code == 403
    assert client.put("/api/v1/thresholds", json=body, headers=login(client, "admin")).status_code == 200


def test_device_fetches_thresholds(client, engineer):
    client.put("/api/v1/thresholds", json={"values": {"risk.distraction.phone_ratio": 0.7}}, headers=engineer)
    r = client.get("/api/v1/device/thresholds", headers={"X-Device-Key": DEVICE_KEY})
    assert r.status_code == 200 and r.json()["values"] == {"risk.distraction.phone_ratio": 0.7}
    assert client.get("/api/v1/device/thresholds").status_code == 401


# ---------------------------------------------------------------- migration from an M5 database


def test_m5_database_is_migrated_without_data_loss(tmp_path):
    path = str(tmp_path / "m5.db")
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('admin', 'manager', 'driver')), driver_id TEXT, created_at TEXT NOT NULL);
        CREATE TABLE events (id INTEGER PRIMARY KEY, event_id TEXT NOT NULL UNIQUE, device_id TEXT NOT NULL,
            driver_id TEXT, trip_id TEXT NOT NULL, ts TEXT NOT NULL, type TEXT NOT NULL, level INTEGER NOT NULL,
            reasons TEXT NOT NULL, drowsy_score REAL NOT NULL, distraction_score REAL NOT NULL, speed_kmh REAL,
            metrics TEXT NOT NULL, received_at TEXT NOT NULL);
        INSERT INTO users VALUES (1, 'admin', 'h', 'admin', NULL, '2026-09-24');
        INSERT INTO events VALUES (1, 'e1', 'cam-001', 'drv-001', 't', '2026-09-24', 'distraction', 2, '["phone"]',
            0, 100, 50, '{}', '2026-09-24');
        """
    )
    conn.close()
    db.init_db(path)
    db.init_db(path)  # idempotent
    with db.closing(path) as conn:
        assert db.get_user(conn, "admin")["role"] == "admin"
        db.create_user(conn, "kysu", "h", "engineer", None)
        assert db.apply_feedback(conn, "cam-001", "e1", "false_alarm", "2026-09-24T09:00:00+00:00")
        assert db.query_events(conn)[0]["feedback"] == "false_alarm"


def test_manage_cli_creates_engineer(tmp_path):
    from backend import manage

    path = str(tmp_path / "cli.db")
    assert manage.main(["--db", path, "create-user", "kysu", "--role", "engineer", "--password", "long-enough-1"]) == 0
    with db.closing(path) as conn:
        assert db.get_user(conn, "kysu")["role"] == "engineer"


def test_camera_lost_event_is_listed_but_not_counted_as_an_alert(client, engineer):
    from edge_agent.io.publisher import build_system_event

    lost = build_system_event("camera_lost", "trip-20260924-150000", 52.0)
    assert batch(client, events=[make_event(), lost]).status_code == 200
    events = client.get("/api/v1/events", headers=engineer).json()
    assert {e["type"] for e in events} == {"distraction", "system"}
    assert next(e for e in events if e["type"] == "system")["reasons"] == ["camera_lost"]
    stats = client.get("/api/v1/stats", headers=engineer).json()
    assert stats["total"] == 1 and "camera_lost" not in stats["by_reason"]
