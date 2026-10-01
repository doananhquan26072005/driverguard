"""Login with 3 roles, device authentication, event storage and role-based reading."""

import pytest

from backend import security
from tests.test_backend.conftest import OTHER_DEVICE_KEY, PASSWORD, login, make_event, post_events


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


# ---------------------------------------------------------------- login


@pytest.mark.parametrize(("user", "role"), [("admin", "admin"), ("boss", "manager"), ("an", "driver")])
def test_login_each_role(client, user, role):
    r = client.post("/auth/login", json={"username": user, "password": PASSWORD})
    assert r.status_code == 200 and r.json()["role"] == role
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"})
    assert me.json()["username"] == user and me.json()["role"] == role


@pytest.mark.parametrize(("user", "password"), [("an", "wrong-password"), ("nobody", PASSWORD)])
def test_login_failure_is_401_without_detail(client, user, password):
    r = client.post("/auth/login", json={"username": user, "password": password})
    assert r.status_code == 401 and r.json()["detail"] == "wrong username or password"


def test_bad_or_missing_token(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer abc.def.ghi"}).status_code == 401


def test_expired_token(client):
    token = security.create_token("t" * 48, "admin", "admin", None, ttl_min=-1)
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_token_signed_with_other_secret_rejected(client):
    token = security.create_token("x" * 48, "admin", "admin", None, ttl_min=5)
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_password_hash_roundtrip():
    h = security.hash_password("s3cret-pass")
    assert h.startswith("scrypt$") and "s3cret-pass" not in h
    assert security.verify_password("s3cret-pass", h)
    assert not security.verify_password("other", h)
    assert not security.verify_password("x", "garbage")


# ---------------------------------------------------------------- receiving events


def test_device_posts_batch(client):
    events = [make_event(), make_event(level=3, reasons=["microsleep"], type="drowsiness")]
    r = post_events(client, events)
    assert r.status_code == 200
    assert r.json() == {
        "accepted": 2,
        "duplicates": 0,
        "feedback_applied": 0,
        "samples_accepted": 0,
        "summaries_accepted": 0,
    }


def test_retry_is_idempotent(client):
    events = [make_event(), make_event()]
    post_events(client, events)
    r = post_events(client, events)
    assert (r.json()["accepted"], r.json()["duplicates"]) == (0, 2)
    assert len(client.get("/api/v1/events", headers=login(client, "admin")).json()) == 2


def test_device_key_required_and_checked(client):
    r = client.post("/api/v1/events", json={"device_id": "cam-001", "events": [make_event()]})
    assert r.status_code == 401
    assert post_events(client, [make_event()], key="dgk_wrong").status_code == 401


def test_device_cannot_post_as_another_device(client):
    assert post_events(client, [make_event()], device_id="cam-001", key=OTHER_DEVICE_KEY).status_code == 403


def test_user_token_cannot_post_events(client):
    r = client.post(
        "/api/v1/events", json={"device_id": "cam-001", "events": [make_event()]}, headers=login(client, "admin")
    )
    assert r.status_code == 401


def test_batch_limits(client):
    assert post_events(client, []).status_code == 422
    assert post_events(client, [make_event() for _ in range(101)]).status_code == 422


def test_driver_id_comes_from_device_registration(client):
    post_events(client, [make_event()])
    stored = client.get("/api/v1/events", headers=login(client, "admin")).json()[0]
    assert stored["device_id"] == "cam-001" and stored["driver_id"] == "drv-001"


# ---------------------------------------------------------------- reading events per role


@pytest.fixture
def two_drivers(client):
    post_events(client, [make_event(level=2), make_event(level=1, reasons=["drowsy_score"], type="drowsiness")])
    post_events(client, [make_event(level=3, reasons=["microsleep"], type="drowsiness")], "cam-002", OTHER_DEVICE_KEY)
    return client


@pytest.mark.parametrize("user", ["admin", "boss"])
def test_admin_and_manager_see_all(two_drivers, user):
    events = two_drivers.get("/api/v1/events", headers=login(two_drivers, user)).json()
    assert {e["driver_id"] for e in events} == {"drv-001", "drv-002"} and len(events) == 3


def test_driver_sees_only_own_events(two_drivers):
    headers = login(two_drivers, "an")
    events = two_drivers.get("/api/v1/events", headers=headers).json()
    assert len(events) == 2 and {e["driver_id"] for e in events} == {"drv-001"}
    # asking for someone else's events is silently scoped back to their own
    events = two_drivers.get("/api/v1/events?driver_id=drv-002", headers=headers).json()
    assert {e["driver_id"] for e in events} == {"drv-001"}
    events = two_drivers.get("/api/v1/events?device_id=cam-002", headers=headers).json()
    assert {e["driver_id"] for e in events} == {"drv-001"}


def test_filters(two_drivers):
    headers = login(two_drivers, "boss")
    assert [e["level"] for e in two_drivers.get("/api/v1/events?min_level=3", headers=headers).json()] == [3]
    assert len(two_drivers.get("/api/v1/events?driver_id=drv-001", headers=headers).json()) == 2
    assert len(two_drivers.get("/api/v1/events?limit=1", headers=headers).json()) == 1
    assert two_drivers.get("/api/v1/events?since=2100-01-01T00:00:00Z", headers=headers).json() == []


def test_events_newest_first_with_reasons_and_metrics(client):
    post_events(client, [make_event(ts="2026-09-24T08:00:00Z"), make_event(ts="2026-09-24T10:00:00+02:00")])
    events = client.get("/api/v1/events", headers=login(client, "admin")).json()
    assert [e["ts"][:19] for e in events] == ["2026-09-24T08:00:00", "2026-09-24T08:00:00"]
    events = client.get("/api/v1/events?since=2026-09-24T09:00:00Z", headers=login(client, "admin")).json()
    assert events == []
    post_events(client, [make_event(ts="2026-09-24T09:30:00Z")])
    events = client.get("/api/v1/events?since=2026-09-24T09:00:00Z", headers=login(client, "admin")).json()
    assert len(events) == 1 and events[0]["reasons"] == ["phone"] and events[0]["metrics"]["phone_ratio_2s"] == 0.72


# ---------------------------------------------------------------- admin functions


def test_only_admin_manages_users_and_devices(client):
    new_user = {"username": "chi", "password": "long-enough-1", "role": "manager"}
    for who in ("boss", "an"):
        headers = login(client, who)
        assert client.post("/api/v1/users", json=new_user, headers=headers).status_code == 403
        assert client.get("/api/v1/users", headers=headers).status_code == 403
        assert client.post("/api/v1/devices", json={"device_id": "cam-009"}, headers=headers).status_code == 403
    headers = login(client, "admin")
    assert client.post("/api/v1/users", json=new_user, headers=headers).status_code == 201
    assert client.post("/api/v1/users", json=new_user, headers=headers).status_code == 409
    assert "chi" in {u["username"] for u in client.get("/api/v1/users", headers=headers).json()}
    assert login(client, "an")  # other accounts unaffected


def test_driver_account_needs_driver_id(client):
    body = {"username": "dung", "password": "long-enough-1", "role": "driver"}
    assert client.post("/api/v1/users", json=body, headers=login(client, "admin")).status_code == 422


def test_new_device_key_works_once_created(client):
    r = client.post(
        "/api/v1/devices", json={"device_id": "cam-009", "driver_id": "drv-009"}, headers=login(client, "admin")
    )
    assert r.status_code == 201
    key = r.json()["device_key"]
    assert key.startswith("dgk_")
    assert post_events(client, [make_event()], device_id="cam-009", key=key).json()["accepted"] == 1


def test_user_list_never_exposes_password_hashes(client):
    text = client.get("/api/v1/users", headers=login(client, "admin")).text
    assert "scrypt" not in text and "password" not in text
