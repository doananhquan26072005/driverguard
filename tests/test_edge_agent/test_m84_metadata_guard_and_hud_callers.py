"""M84: one metadata guard for the device, the page and the backend; the HUD server checks who calls
(audit 08/10, A4 M8, M6 and L6).

- Block 14: the in-browser agent queued records without the device's guard, and the device's list of
  forbidden words was shorter than the backend's. Now one module holds the list and the scanner.
- Block 13: any page open on the machine could POST to the HUD server (end the trip, change the
  driver), and a page reaching 127.0.0.1 under another host name could read /state.
Fake landmark numbers and a HUD server on a free port, no video.
"""

import http.client
import json

import numpy as np
import pytest

import backend.schemas as schemas
import edge_agent.io.publisher as publisher
from edge_agent.hud.server import DEFAULT_ORIGINS, HudServer, HudState, host_name
from edge_agent.io import metadata_guard
from edge_agent.io.publisher import check_metadata_only
from edge_agent.web.bridge import WebAgent
from tests.test_edge_agent.test_web_bridge import run, synthetic_face

# ---------------------------------------------------------------- one list, one scanner


def test_the_backend_and_the_device_use_the_same_scanner():
    assert schemas.find_image_data is metadata_guard.find_image_data
    assert publisher.find_image_data is metadata_guard.find_image_data
    for module in (schemas, publisher):  # no second list left to drift
        assert not hasattr(module, "FORBIDDEN_KEY_PARTS")
        assert not hasattr(module, "BASE64_RUN")


@pytest.mark.parametrize("word", ["jpg", "base64", "b64", "video", "blob", "face_crop"])
def test_the_device_now_refuses_the_words_only_the_backend_knew(word):
    with pytest.raises(ValueError, match="forbidden field name"):
        check_metadata_only({"metrics": {f"eye_{word}": 1}})


@pytest.mark.parametrize(
    "value",
    [
        "/9j/4AAQSkZJRgABAQ",  # JPEG signature, too short for the base64 run
        "iVBORw0KGgoAAAANSUhEUg",  # PNG signature
        "data:image/png;base64,AAAA",
        "x;base64,AAAA",  # the device's older rule, kept
        b"\xff\xd8",
        np.zeros((2, 2), np.uint8),
    ],
)
def test_the_device_refuses_what_the_backend_refuses(value):
    assert metadata_guard.find_image_data({"x": [value]}) is not None
    with pytest.raises(ValueError):
        check_metadata_only({"x": [value]})


# ---------------------------------------------------------------- the in-browser agent


@pytest.fixture
def agent():
    return WebAgent("web-an", "trip-web-1", scenario="highway_night")


def test_a_real_trip_in_the_page_passes_the_guard(agent):
    _, t, f = run(agent, 12, points=synthetic_face())
    run(agent, 2.5, t0=t, frame0=f, points=synthetic_face(ear=0.05), blink=(0.9, 0.9))  # L3 microsleep
    agent.camera(True)
    agent.end_trip()
    body = json.loads(agent.take_batch())
    assert body["events"] and body["summaries"]
    assert agent.take_heartbeat() is not None
    assert agent.refused_records == 0


@pytest.mark.parametrize(
    "bad",
    [
        {"snapshot_jpg": "x"},
        {"metrics": {"face_crop": [1, 2, 3]}},
        {"note": "data:image/jpeg;base64,AAAA"},
        {"metrics": {"x": np.zeros((2, 2), np.uint8)}},
    ],
)
def test_an_image_like_record_never_leaves_the_page(agent, bad, capsys):
    agent._queue("event", {"event_id": "e-1", "level": 3, "reasons": ["microsleep"], **bad})
    agent._queue("heartbeat", {"state": "monitoring", **bad})
    assert agent.take_batch() is None and agent.take_heartbeat() is None
    assert agent.refused_records == 2
    assert agent._urgent is False  # nothing to hurry the page for
    assert "record not sent" in capsys.readouterr().out
    agent._queue("event", {"event_id": "e-2", "level": 1, "reasons": ["drowsy_score"]})  # the next one goes
    assert [e["event_id"] for e in json.loads(agent.take_batch())["events"]] == ["e-2"]


def test_a_refused_record_does_not_fail_the_frame(agent, monkeypatch):
    # A record built wrongly somewhere in the runtime: the frame still returns the HUD state.
    emit = agent.runtime._emit
    monkeypatch.setattr(agent.runtime, "_emit", lambda kind, data: emit(kind, {**data, "frame_png": "x"}))
    state, _, _ = run(agent, 1, points=synthetic_face())
    assert state["connected"] is True and "error" not in state
    assert agent.refused_records >= 1 and agent.take_batch() is None


# ---------------------------------------------------------------- HUD server: who calls

ALLOWED = DEFAULT_ORIGINS[0]
JSON = {"Content-Type": "application/json"}


@pytest.fixture
def hud():
    flagged = []
    state = HudState()
    server = HudServer(state, flagged.append, port=0).start()
    yield state, server.port, flagged
    server.stop()


def request(port, method, path, body=None, headers=None):
    """Plain http.client: every header is ours, as a browser (or another page) would send it."""
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        data = None if body is None else json.dumps(body)
        conn.request(method, path, data, headers or {})
        resp = conn.getresponse()
        return resp.status, json.loads(resp.read() or b"{}")
    finally:
        conn.close()


@pytest.mark.parametrize("origin", ["http://evil.example", "null", "http://127.0.0.1:9999", ""])
def test_a_post_from_another_page_is_refused(hud, origin):
    state, port, flagged = hud
    state.add_alert("ev-1", 2, ("phone",))
    headers = {**JSON, "Origin": origin}
    assert request(port, "POST", "/end-trip", headers={"Origin": origin})[0] == 403
    for action in ("change_driver", "presence_ok", "enroll_later"):
        assert request(port, "POST", "/vehicle", {"action": action}, headers)[0] == 403
    assert request(port, "POST", "/feedback", {"event_id": "ev-1"}, headers)[0] == 403
    assert state.end_requested is False  # the trip goes on
    assert state.take_actions() == [] and flagged == [] and state.false_alarms == 0


def test_the_hud_page_and_local_tools_still_get_through(hud):
    state, port, flagged = hud
    state.add_alert("ev-1", 2, ("phone",))
    assert request(port, "POST", "/vehicle", {"action": "presence_ok"}, {**JSON, "Origin": ALLOWED})[0] == 202
    assert request(port, "POST", "/vehicle", {"action": "change_driver"}, JSON)[0] == 202  # no browser: no Origin
    assert state.take_actions() == ["presence_ok", "change_driver"]
    assert request(port, "POST", "/feedback", {"event_id": "ev-1"}, {**JSON, "Origin": ALLOWED})[0] == 200
    assert flagged == ["ev-1"]


def test_an_extra_origin_given_to_the_agent_may_post():
    hosted = "https://driveguard.example"
    state = HudState()
    server = HudServer(state, lambda _: None, port=0, allowed_origins=(*DEFAULT_ORIGINS, hosted)).start()
    try:
        assert request(server.port, "POST", "/vehicle", {"action": "presence_ok"}, {**JSON, "Origin": hosted})[0] == 202
    finally:
        server.stop()


@pytest.mark.parametrize(
    "content_type", [None, "text/plain", "application/x-www-form-urlencoded", "multipart/form-data; boundary=x"]
)
def test_a_body_that_needs_no_preflight_is_refused(hud, content_type):
    # The three types a page may send cross-origin without asking first, and no type at all.
    state, port, flagged = hud
    state.add_alert("ev-1", 2, ("phone",))
    headers = {} if content_type is None else {"Content-Type": content_type}
    assert request(port, "POST", "/vehicle", {"action": "change_driver"}, headers)[0] == 415
    assert request(port, "POST", "/feedback", {"event_id": "ev-1"}, headers)[0] == 415
    assert state.take_actions() == [] and flagged == []


def test_json_with_a_charset_is_still_json(hud):
    state, port, _ = hud
    headers = {"Content-Type": "application/json; charset=utf-8"}
    assert request(port, "POST", "/vehicle", {"action": "presence_ok"}, headers)[0] == 202


@pytest.mark.parametrize("host", ["evil.example", "evil.example:8765", "127.0.0.1.evil.example", "[::1]:8765", ""])
def test_a_request_under_another_host_name_is_refused(hud, host):
    # DNS rebinding: the page's own name resolves to 127.0.0.1, so its requests are same-origin.
    state, port, _ = hud
    assert request(port, "GET", "/state", headers={"Host": host}) == (403, {"detail": "host not allowed"})
    assert request(port, "POST", "/end-trip", headers={"Host": host})[0] == 403
    assert request(port, "POST", "/vehicle", {"action": "change_driver"}, {**JSON, "Host": host})[0] == 403
    assert request(port, "OPTIONS", "/state", headers={"Host": host})[0] == 403
    assert state.end_requested is False and state.take_actions() == []


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "LOCALHOST"])
def test_this_machines_names_are_served(hud, host):
    _, port, _ = hud
    assert request(port, "GET", "/state", headers={"Host": f"{host}:{port}"})[0] == 200
    assert request(port, "GET", "/state", headers={"Host": host})[0] == 200  # port 80 leaves it out


def test_host_name_drops_the_port():
    assert host_name("127.0.0.1:8765") == "127.0.0.1"
    assert host_name(" Localhost ") == "localhost"
    assert host_name(None) == ""
