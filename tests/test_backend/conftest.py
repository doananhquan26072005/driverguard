import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from backend import db
from backend.app import create_app
from backend.security import hash_device_key, hash_password
from backend.settings import BackendSettings

PASSWORD = "correct-horse-1"
DEVICE_KEY = "dgk_test_key_cam001"
OTHER_DEVICE_KEY = "dgk_test_key_cam002"


@pytest.fixture
def settings(tmp_path):
    return BackendSettings(db_path=str(tmp_path / "test.db"), jwt_secret="t" * 48, token_ttl_min=5)


@pytest.fixture
def client(settings):
    app = create_app(settings)
    with db.closing(settings.db_path) as conn:
        db.create_user(conn, "admin", hash_password(PASSWORD), "admin", None)
        db.create_user(conn, "boss", hash_password(PASSWORD), "manager", None)
        db.create_user(conn, "an", hash_password(PASSWORD), "driver", "drv-001")
        db.create_user(conn, "binh", hash_password(PASSWORD), "driver", "drv-002")
        db.create_device(conn, "cam-001", hash_device_key(DEVICE_KEY), "drv-001")
        db.create_device(conn, "cam-002", hash_device_key(OTHER_DEVICE_KEY), "drv-002")
    with TestClient(app) as c:
        yield c


def login(client, username):
    r = client.post("/auth/login", json={"username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def make_event(**overrides):
    event = {
        "event_id": str(uuid.uuid4()),
        "ts": datetime.now(UTC).isoformat(),
        "trip_id": "trip-20260924-150000",
        "type": "distraction",
        "level": 2,
        "reasons": ["phone"],
        "drowsy_score": 12.5,
        "distraction_score": 100.0,
        "speed_kmh": 52.0,
        "metrics": {"phone_ratio_2s": 0.72, "off_road_duration": 0.0, "perclos_60s": 0.04},
    }
    event.update(overrides)
    return event


def post_events(client, events, device_id="cam-001", key=DEVICE_KEY):
    return client.post("/api/v1/events", json={"device_id": device_id, "events": events}, headers={"X-Device-Key": key})
