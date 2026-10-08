"""M90 (audit 08/10, A4 L5): an event_id another device already used is not this device's duplicate."""

from tests.test_backend.conftest import OTHER_DEVICE_KEY, login, make_event, post_events


def test_a_retry_of_the_same_device_is_a_duplicate(client):
    event = make_event()
    assert post_events(client, [event]).json()["accepted"] == 1
    again = post_events(client, [event]).json()
    assert (again["accepted"], again["duplicates"], again["conflicts"]) == (0, 1, 0)


def test_an_event_id_of_another_device_is_a_conflict_and_is_said(client, caplog):
    taken = make_event()
    assert post_events(client, [taken]).json()["accepted"] == 1
    mine = make_event(event_id=taken["event_id"], level=3, reasons=["microsleep"], type="drowsiness")
    with caplog.at_level("WARNING", logger="driverguard.backend"):
        r = post_events(client, [mine, make_event()], device_id="cam-002", key=OTHER_DEVICE_KEY)
    assert r.status_code == 200  # the rest of the batch goes through
    body = r.json()
    assert (body["accepted"], body["duplicates"], body["conflicts"]) == (1, 0, 1)  # before: "duplicates": 1
    assert "cam-002" in caplog.text and taken["event_id"] not in caplog.text  # who, never what
    # The first device's event is untouched.
    stored = client.get("/api/v1/events", headers=login(client, "admin")).json()
    rows = stored["items"] if isinstance(stored, dict) else stored
    kept = [e for e in rows if e["event_id"] == taken["event_id"]]
    assert len(kept) == 1 and kept[0]["device_id"] == "cam-001" and kept[0]["level"] == 2
