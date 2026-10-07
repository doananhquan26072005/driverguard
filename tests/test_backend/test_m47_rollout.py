"""M47: which thresholds version runs where: the fleet's, a trial pinned to some devices, a roll back."""

import pytest

from backend import db
from backend.security import hash_password
from tests.test_backend.conftest import DEVICE_KEY, OTHER_DEVICE_KEY, PASSWORD, login, make_event
from tests.test_backend.test_fleet import beat, fleet


@pytest.fixture
def engineer(client, settings):
    with db.closing(settings.db_path) as conn:
        db.create_user(conn, "eng", hash_password(PASSWORD), "engineer", None)


def save(client, values, trial=None, user="eng"):
    body = {"values": values} | ({"trial_devices": trial} if trial else {})
    return client.put("/api/v1/thresholds", json=body, headers=login(client, user))


def device(client, key=DEVICE_KEY):
    r = client.get("/api/v1/device/thresholds", headers={"X-Device-Key": key})
    assert r.status_code == 200, r.text
    return r.json()


def rollout(client, version, user="eng"):
    return client.post("/api/v1/thresholds/rollout", json={"version": version}, headers=login(client, user))


def versions(client, user="eng"):
    r = client.get("/api/v1/thresholds/versions", headers=login(client, user))
    assert r.status_code == 200, r.text
    return {v["version"]: v for v in r.json()}


def test_a_plain_save_goes_to_the_whole_fleet_as_before(client, engineer):
    assert device(client)["version"] == 0 and device(client)["values"] == {}
    assert save(client, {"risk.drowsy.l1": 45}).json()["fleet_version"] == 1
    assert device(client)["version"] == 1 and device(client, OTHER_DEVICE_KEY)["values"] == {"risk.drowsy.l1": 45}


def test_a_trial_reaches_only_its_devices_until_it_is_rolled_out(client, engineer):
    save(client, {"risk.drowsy.l1": 45})
    out = save(client, {"risk.drowsy.l1": 50}, trial=["cam-002"]).json()
    assert out["version"] == 2 and out["fleet_version"] == 1  # the dashboard edits on the newest
    assert device(client)["version"] == 1 and device(client)["values"]["risk.drowsy.l1"] == 45
    assert device(client, OTHER_DEVICE_KEY)["version"] == 2
    v = versions(client)
    assert v[1]["fleet"] and not v[2]["fleet"] and v[2]["pinned_devices"] == ["cam-002"]
    assert v[2]["changed"] == ["risk.drowsy.l1"]

    assert rollout(client, 2).json()["fleet_version"] == 2
    assert device(client)["version"] == 2 and device(client, OTHER_DEVICE_KEY)["version"] == 2
    assert versions(client)[2]["pinned_devices"] == [] and versions(client)[2]["fleet"]


def test_roll_back_gives_the_older_version_without_rewriting_history(client, engineer):
    save(client, {"risk.drowsy.l1": 45})
    save(client, {"risk.drowsy.l1": 60})
    assert device(client)["values"]["risk.drowsy.l1"] == 60
    assert rollout(client, 1).status_code == 200
    got = device(client)
    assert got["version"] == 1 and got["values"]["risk.drowsy.l1"] == 45
    assert set(versions(client)) == {1, 2}  # nothing was copied or deleted
    dash = client.get("/api/v1/thresholds", headers=login(client, "eng")).json()
    assert dash["version"] == 2 and dash["fleet_version"] == 1
    assert rollout(client, 99).status_code == 404


def test_only_engineers_roll_out_and_it_is_logged(client, engineer):
    save(client, {"risk.drowsy.l1": 45})
    assert rollout(client, 1, user="boss").status_code == 403
    assert save(client, {"risk.drowsy.l1": 50}, trial=["cam-001"], user="boss").status_code == 403
    assert client.get("/api/v1/thresholds/versions", headers=login(client, "an")).status_code == 403
    save(client, {"risk.drowsy.l1": 50}, trial=["cam-001"])
    rollout(client, 1)
    log = client.get("/api/v1/access-log", headers=login(client, "admin")).json()
    details = {row["action"]: row["detail"] for row in log}
    assert "trial on cam-001" in next(r["detail"] for r in log if "trial" in (r["detail"] or ""))
    assert details["rollout_thresholds"] == "fleet version 1 -> 1"


def test_fleet_view_judges_a_device_against_its_own_target(client, engineer):
    save(client, {"risk.drowsy.l1": 45})
    save(client, {"risk.drowsy.l1": 50}, trial=["cam-002"])
    info = {"app": "3.0.0", "thresholds_ignored": False, "models": {}}
    beat(client, versions={**info, "thresholds_version": 1})
    beat(client, device_id="cam-002", key=OTHER_DEVICE_KEY, versions={**info, "thresholds_version": 2})
    got = fleet(client)
    assert got["cam-001"]["thresholds_current"] is True and got["cam-001"]["thresholds_latest"] == 1
    assert got["cam-002"]["thresholds_current"] is True and got["cam-002"]["thresholds_latest"] == 2
    rollout(client, 2)
    assert fleet(client)["cam-001"]["thresholds_current"] is False  # still on 1 until it is parked


def test_history_counts_alerts_and_false_alarms_per_version(client, engineer):
    save(client, {"risk.drowsy.l1": 45})
    save(client, {"risk.drowsy.l1": 50}, trial=["cam-001"])
    info = {"app": "3.0.0", "thresholds_ignored": False, "models": {}}
    old = [make_event(versions={**info, "thresholds_version": 1}) for _ in range(3)]
    new = [make_event(versions={**info, "thresholds_version": 2}) for _ in range(2)]
    forced = make_event(versions={**info, "thresholds_version": 2}, tags=["forced"])
    headers = {"X-Device-Key": DEVICE_KEY}
    client.post("/api/v1/events", json={"device_id": "cam-001", "events": old + new + [forced]}, headers=headers)
    mark = {"event_id": new[0]["event_id"], "verdict": "false_alarm", "ts": new[0]["ts"]}
    client.post("/api/v1/events", json={"device_id": "cam-001", "feedback": [mark]}, headers=headers)
    beat(client, versions={**info, "thresholds_version": 2})
    v = versions(client)
    assert (v[1]["alerts"], v[1]["false_alarms"]) == (3, 0)
    assert (v[2]["alerts"], v[2]["false_alarms"]) == (2, 1)
    assert v[2]["running_devices"] == ["cam-001"]


def test_browser_follows_its_pin_too(client, engineer):
    save(client, {"risk.drowsy.l1": 45})
    save(client, {"risk.drowsy.l1": 50}, trial=["web-an"])
    an = client.get("/api/v1/web/thresholds", headers=login(client, "an")).json()
    binh = client.get("/api/v1/web/thresholds", headers=login(client, "binh")).json()
    assert an["version"] == 2 and binh["version"] == 1


def test_an_inconsistent_or_malformed_trial_is_refused(client, engineer):
    assert save(client, {"risk.drowsy.l1": 99}, trial=["cam-001"]).status_code == 422  # above l2
    assert save(client, {"risk.drowsy.l1": 45}, trial=["../etc"]).status_code == 422
    assert versions(client) == {}
