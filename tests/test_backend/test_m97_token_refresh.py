"""M97: a login token that is still valid can be exchanged for a new one (audit 08/10, A4 H2; decision
12A of 09/10).

A trip on #/live lasts longer than DG_TOKEN_TTL_MIN (60 min). Before, every batch after that came back
401 and nothing of the rest of the trip reached the backend. The page now asks for a new token long
before the old one expires (frontend/src/live/agent.ts `keepSession`). What the exchange must not do:
revive an expired token, or keep a deleted account alive.
"""

from datetime import UTC, datetime, timedelta

import jwt

from backend import db
from backend.security import create_token, decode_token
from tests.test_backend.conftest import login


def claims(settings, headers):
    return decode_token(settings.jwt_secret, headers["Authorization"].split()[1])


def test_a_valid_token_is_exchanged_for_one_with_a_full_lifetime(client, settings):
    old = login(client, "an")
    r = client.post("/auth/refresh", headers=old)
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "driver" and body["expires_in"] == settings.token_ttl_min * 60
    new = {"Authorization": f"Bearer {body['access_token']}"}
    assert client.get("/auth/me", headers=new).json() == {"username": "an", "role": "driver", "driver_id": "drv-001"}
    assert claims(settings, new)["exp"] >= claims(settings, old)["exp"]


def test_the_new_token_sends_a_trip_batch(client):
    token = client.post("/auth/refresh", headers=login(client, "an")).json()["access_token"]
    beat = {
        "device_id": "web-an",
        "heartbeat": {"state": "monitoring", "ts": datetime.now(UTC).isoformat(), "trip_id": "trip-m97"},
    }
    r = client.post("/api/v1/web/events", json=beat, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text


def test_an_expired_token_gets_nothing(client, settings):
    past = datetime.now(UTC) - timedelta(minutes=1)
    payload = {"sub": "an", "role": "driver", "driver_id": "drv-001", "iat": past - timedelta(minutes=5), "exp": past}
    expired = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    assert client.post("/auth/refresh", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
    assert client.post("/auth/refresh").status_code == 401  # and no token at all


def test_a_token_signed_by_someone_else_gets_nothing(client, settings):
    forged = create_token("x" * 48, "admin", "admin", None, settings.token_ttl_min)
    assert client.post("/auth/refresh", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_a_deleted_account_does_not_live_on_in_refreshed_tokens(client, settings):
    headers = login(client, "binh")
    with db.closing(settings.db_path) as conn:
        assert db.delete_user(conn, "binh")
    assert client.post("/auth/refresh", headers=headers).status_code == 401


def test_the_new_token_carries_the_account_as_it_is_now(client, settings):
    """The role and driver come from the database, not from the old token."""
    headers = login(client, "an")
    with db.closing(settings.db_path) as conn:
        conn.execute("UPDATE users SET driver_id = ? WHERE username = ?", ("drv-009", "an"))
        conn.commit()
    new = {"Authorization": f"Bearer {client.post('/auth/refresh', headers=headers).json()['access_token']}"}
    assert claims(settings, new)["driver_id"] == "drv-009"
