"""Read-only accounts (13/10): the public demo's engineer sees what an engineer sees and changes nothing:
no new thresholds, no rollout, no review / note to a driver. Others are not affected."""

from backend import db
from backend.security import hash_password
from backend.settings import BackendSettings
from tests.test_backend.conftest import PASSWORD, login
from tests.test_backend.test_trip_reports import send, summary


def add_engineers(settings):
    with db.closing(settings.db_path) as conn:
        db.create_user(conn, "kysu_demo", hash_password(PASSWORD), "engineer", None)
        db.create_user(conn, "kysu", hash_password(PASSWORD), "engineer", None)


def test_the_demo_engineer_is_read_only_by_default():
    assert BackendSettings().is_read_only("kysu_demo")
    assert not BackendSettings().is_read_only("kysu")
    assert BackendSettings(read_only_users=" a , kysu ").is_read_only("kysu")
    assert not BackendSettings(read_only_users="").is_read_only("kysu_demo")


def test_the_demo_engineer_reads_but_cannot_change_anything(client, settings):
    add_engineers(settings)
    demo = login(client, "kysu_demo")
    assert client.post("/auth/login", json={"username": "kysu_demo", "password": PASSWORD}).json()["read_only"] is True
    assert client.get("/api/v1/thresholds", headers=demo).status_code == 200
    assert client.get("/api/v1/thresholds/versions", headers=demo).status_code == 200

    r = client.put("/api/v1/thresholds", json={"values": {"risk.drowsy.l1": 45}}, headers=demo)
    assert r.status_code == 403 and r.json()["detail"] == "demo account: read only"
    assert client.post("/api/v1/thresholds/rollout", json={"version": 1}, headers=demo).status_code == 403
    send(client, summary("trip-a"))
    review = client.post("/api/v1/trip-reports/cam-001/trip-a/review", json={"note": "spam"}, headers=demo)
    assert review.status_code == 403
    an = login(client, "an")
    assert client.get("/api/v1/trip-reports", headers=an).json()[0]["review_note"] is None  # nothing written


def test_other_accounts_keep_their_rights(client, settings):
    add_engineers(settings)
    assert client.post("/auth/login", json={"username": "kysu", "password": PASSWORD}).json()["read_only"] is False
    r = client.put("/api/v1/thresholds", json={"values": {"risk.drowsy.l1": 45}}, headers=login(client, "kysu"))
    assert r.status_code == 200
    send(client, summary("trip-a"))
    boss = login(client, "boss")
    assert (
        client.post("/api/v1/trip-reports/cam-001/trip-a/review", json={"note": "ok"}, headers=boss).status_code == 200
    )
