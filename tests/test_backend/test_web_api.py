"""In-browser agent (#/live): events posted with the signed-in user's token instead of a device key."""

from tests.test_backend.conftest import login, make_event


def post_web(client, headers, device_id, events):
    return client.post("/api/v1/web/events", json={"device_id": device_id, "events": events}, headers=headers)


def test_driver_posts_as_own_browser_device(client):
    an = login(client, "an")
    r = post_web(client, an, "web-an", [make_event()])
    assert r.status_code == 200 and r.json()["accepted"] == 1
    events = client.get("/api/v1/events", headers=an).json()
    assert [(e["device_id"], e["driver_id"]) for e in events] == [("web-an", "drv-001")]
    # another driver does not see it
    assert client.get("/api/v1/events", headers=login(client, "binh")).json() == []


def test_web_device_id_must_be_the_users(client):
    an = login(client, "an")
    assert post_web(client, an, "web-binh", [make_event()]).status_code == 403
    assert post_web(client, an, "cam-001", [make_event()]).status_code == 403


def test_web_events_need_a_token(client):
    assert post_web(client, {}, "web-an", [make_event()]).status_code == 401


def test_web_feedback_and_samples(client):
    an = login(client, "an")
    event = make_event()
    body = {
        "device_id": "web-an",
        "events": [event],
        "feedback": [{"event_id": event["event_id"], "verdict": "false_alarm", "ts": event["ts"]}],
        "samples": [
            {
                "sample_id": "8a6f7c1e-4a55-4c43-9f0e-1c9d4c1f2b3a",
                "ts": event["ts"],
                "trip_id": event["trip_id"],
                "drowsy_score": 12.0,
                "perclos_60s": 0.05,
                "max_level": 2,
            }
        ],
    }
    r = client.post("/api/v1/web/events", json=body, headers=an)
    assert r.json() == {"accepted": 1, "duplicates": 0, "feedback_applied": 1, "samples_accepted": 1}


def test_web_thresholds_readable_by_driver(client):
    r = client.get("/api/v1/web/thresholds", headers=login(client, "an"))
    assert r.status_code == 200 and r.json()["version"] == 0
    assert client.get("/api/v1/web/thresholds").status_code == 401
