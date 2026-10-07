"""M48: a driver exports their own data and asks for deletion from the page; an admin answers;
the database file is closed to other local users; nothing secret can reach an image."""

import os
import re
import stat
from pathlib import Path

import pytest

from backend import db, manage
from backend.schemas import find_image_data
from tests.test_backend.conftest import DEVICE_KEY, OTHER_DEVICE_KEY, login, make_event

ROOT = Path(__file__).resolve().parents[2]


def seed(client):
    for key, device in ((DEVICE_KEY, "cam-001"), (OTHER_DEVICE_KEY, "cam-002")):
        client.post(
            "/api/v1/events",
            json={"device_id": device, "events": [make_event(), make_event()]},
            headers={"X-Device-Key": key},
        )
    client.get("/api/v1/events?driver_id=drv-001", headers=login(client, "boss"))  # a manager looks at An's data


def test_export_holds_only_the_drivers_own_rows_and_who_looked(client):
    seed(client)
    r = client.get("/api/v1/me/data", headers=login(client, "an"))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["driver_id"] == "drv-001" and data["account"] == "an"
    assert len(data["events"]) == 2 and {e["device_id"] for e in data["events"]} == {"cam-001"}
    assert data["events"][0]["reasons"] == ["phone"] and isinstance(data["events"][0]["metrics"], dict)
    assert [row["username"] for row in data["access_log"]] == ["boss"]
    assert data["retention_days"] == {"events": 60, "trip_summaries": 365}
    assert find_image_data(data) is None  # numbers and short codes, as stored
    assert "password" not in r.text and "key_hash" not in r.text


def test_export_is_the_drivers_only(client):
    seed(client)
    assert client.get("/api/v1/me/data").status_code == 401
    assert client.get("/api/v1/me/data", headers=login(client, "boss")).status_code == 403
    assert client.get("/api/v1/me/data", headers=login(client, "admin")).status_code == 403


def test_request_then_admin_deletes_and_it_is_logged(client):
    seed(client)
    an = login(client, "an")
    assert client.get("/api/v1/me/deletion-request", headers=an).json() is None
    req = client.post("/api/v1/me/deletion-request", headers=an).json()
    assert req["status"] == "pending" and req["driver_id"] == "drv-001"
    assert client.post("/api/v1/me/deletion-request", headers=an).json()["id"] == req["id"]  # asked once

    admin = login(client, "admin")
    assert [r["id"] for r in client.get("/api/v1/deletion-requests", headers=admin).json()] == [req["id"]]
    assert client.get("/api/v1/deletion-requests", headers=login(client, "boss")).status_code == 403
    done = client.post(f"/api/v1/deletion-requests/{req['id']}", json={"action": "delete"}, headers=admin)
    assert done.status_code == 200 and done.json()["status"] == "done" and done.json()["handled_by"] == "admin"

    assert client.get("/api/v1/me/data", headers=an).json()["events"] == []
    boss = login(client, "boss")
    assert len(client.get("/api/v1/events?driver_id=drv-002", headers=boss).json()) == 2  # Binh's untouched
    assert client.get("/api/v1/me/deletion-request", headers=an).json()["status"] == "done"
    log = client.get("/api/v1/access-log", headers=admin).json()
    assert any(r["action"] == "delete_driver_data" and r["driver_id"] == "drv-001" for r in log)
    again = client.post(f"/api/v1/deletion-requests/{req['id']}", json={"action": "delete"}, headers=admin)
    assert again.status_code == 404  # handled once


def test_refusal_needs_a_reason_code_and_keeps_the_data(client):
    seed(client)
    an, admin = login(client, "an"), login(client, "admin")
    req = client.post("/api/v1/me/deletion-request", headers=an).json()
    url = f"/api/v1/deletion-requests/{req['id']}"
    assert client.post(url, json={"action": "refuse"}, headers=admin).status_code == 422
    assert client.post(url, json={"action": "refuse", "reason": "because"}, headers=admin).status_code == 422
    assert client.post(url, json={"action": "delete", "reason": "other"}, headers=admin).status_code == 422
    out = client.post(url, json={"action": "refuse", "reason": "incident_open"}, headers=admin).json()
    assert out["status"] == "refused" and out["reason"] == "incident_open"
    mine = client.get("/api/v1/me/deletion-request", headers=an).json()
    assert mine["status"] == "refused" and mine["reason"] == "incident_open"
    assert len(client.get("/api/v1/me/data", headers=an).json()["events"]) == 2
    assert client.post("/api/v1/me/deletion-request", headers=an).json()["id"] != req["id"]  # may ask again


def test_delete_user_tool(client, settings, capsys):
    seed(client)
    assert manage.main(["--db", settings.db_path, "delete-user", "an"]) == 1  # no --yes
    assert manage.main(["--db", settings.db_path, "delete-user", "nobody", "--yes"]) == 1
    assert manage.main(["--db", settings.db_path, "delete-user", "an", "--with-data", "--yes"]) == 0
    assert "removed account 'an'" in capsys.readouterr().out
    r = client.post("/auth/login", json={"username": "an", "password": "correct-horse-1"})
    assert r.status_code == 401
    boss = login(client, "boss")
    assert client.get("/api/v1/events?driver_id=drv-001", headers=boss).json() == []
    with db.closing(settings.db_path) as conn:
        actions = [r["action"] for r in db.query_access_log(conn, limit=10)]
    assert "delete_user" in actions and "delete_driver_data" in actions


@pytest.mark.skipif(os.name == "nt", reason="POSIX file modes")
def test_database_file_is_owner_only(tmp_path):
    path = str(tmp_path / "dg.db")
    db.init_db(path)
    with db.closing(path) as conn:
        conn.execute("SELECT 1")
    db.restrict_file(path)
    for name in os.listdir(tmp_path):
        mode = stat.S_IMODE(os.stat(tmp_path / name).st_mode)
        assert mode & 0o077 == 0, f"{name} is readable by others ({oct(mode)})"


# ------------------------------------------------------------------ nothing secret in an image
def ignored(pattern_file: Path) -> list[str]:
    return [ln.strip() for ln in pattern_file.read_text().splitlines() if ln.strip() and not ln.startswith("#")]


def test_dockerignore_keeps_secrets_and_databases_out_of_every_build():
    patterns = ignored(ROOT / ".dockerignore")
    for needed in (".env", "**/.env", "**/.env.*", "data/", "**/*.db", "**/*.db-wal", "**/*.db-shm", ".git"):
        assert needed in patterns, f".dockerignore lost {needed}"
    assert not any(p.startswith("!") and (".env" in p or ".db" in p or p.startswith("!data")) for p in patterns)


def test_no_dockerfile_copies_data_or_sets_a_secret():
    files = sorted(ROOT.glob("Dockerfile*"))
    assert len(files) >= 3
    for f in files:
        text = f.read_text()
        for line in text.splitlines():
            if line.strip().startswith(("COPY", "ADD")):
                assert not re.search(r"(^|[\s/])data(/|\s|$)|\.env|\.db\b", line), f"{f.name}: {line}"
        # A secret baked into an image layer stays there: none may be given a value at build time.
        assert not re.search(r"(?m)^\s*(ENV|ARG)\s+.*(DG_JWT_SECRET|DG_DEVICE_KEY|PASSWORD|API_KEY)\s*=\s*\S", text), (
            f.name
        )
