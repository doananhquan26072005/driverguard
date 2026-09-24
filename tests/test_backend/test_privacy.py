"""The schema must refuse any payload that could carry an image or base64 data."""

import base64
import json

import pytest

from backend.schemas import EventBatch, find_image_data
from tests.test_backend.conftest import make_event, post_events

JPEG_B64 = base64.b64encode(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + bytes(range(256)) * 4).decode()
PNG_B64 = base64.b64encode(b"\x89PNG\r\n\x1a\n" + bytes(200)).decode()
RANDOM_B64 = base64.b64encode(bytes(range(120))).decode()


# ---------------------------------------------------------------- scanner


@pytest.mark.parametrize(
    "payload",
    [
        {"image": "x"},
        {"face_crop": [1, 2]},
        {"frameData": 1},
        {"a": {"b": [{"thumbnail_url": "x"}]}},
        {"note": "data:image/jpeg;base64,AAAA"},
        {"x": "data:application/octet-stream;base64,AAAA"},
        {"x": JPEG_B64[:40]},  # JPEG signature /9j/
        {"x": PNG_B64[:40]},  # PNG signature
        {"x": RANDOM_B64},  # any long base64 run
        {"x": [b"\x00\x01"]},
    ],
)
def test_scanner_finds_image_data(payload):
    assert find_image_data(payload) is not None


@pytest.mark.parametrize(
    "payload",
    [
        make_event(),
        {"device_id": "cam-001", "trip_id": "trip-20260924-150000"},
        {"event_id": "123e4567-e89b-12d3-a456-426614174000", "ts": "2026-09-24T08:00:00+00:00"},
        {"reasons": ["microsleep", "drowsy_score"], "speed": 88.5},
    ],
)
def test_scanner_accepts_normal_metadata(payload):
    assert find_image_data(payload) is None


def test_longest_valid_id_is_not_flagged_as_base64():
    batch = {"device_id": "a" * 48, "events": [make_event(trip_id="B" * 48)]}
    assert EventBatch.model_validate(batch).device_id == "a" * 48


# ---------------------------------------------------------------- API rejections


def assert_rejected(response, secret=None):
    assert response.status_code == 422, response.text
    if secret:  # the rejected content must not be echoed back
        assert secret not in response.text


@pytest.mark.parametrize(
    "extra",
    [
        {"image": JPEG_B64},
        {"frame": "abc"},
        {"snapshot_b64": "abc"},
        {"face_crop": [[0, 1], [2, 3]]},
    ],
)
def test_image_fields_rejected(client, extra):
    r = post_events(client, [make_event(**extra)])
    assert_rejected(r, JPEG_B64[:30])


def test_base64_hidden_in_allowed_field_rejected(client):
    assert_rejected(post_events(client, [make_event(trip_id=RANDOM_B64)]), RANDOM_B64[:30])
    assert_rejected(post_events(client, [make_event(reasons=[JPEG_B64])]), JPEG_B64[:30])
    assert_rejected(post_events(client, [make_event(metrics={"perclos_60s": PNG_B64})]), PNG_B64[:30])


def test_data_uri_rejected(client):
    uri = "data:image/png;base64," + PNG_B64[:20]
    assert_rejected(post_events(client, [make_event(trip_id=uri)]), uri)


def test_unknown_fields_rejected(client):
    assert_rejected(post_events(client, [make_event(comment="hello")]))
    assert_rejected(post_events(client, [make_event(metrics={"ear": 0.3})]))
    r = client.post(
        "/api/v1/events",
        json={"device_id": "cam-001", "events": [make_event()], "extra": 1},
        headers={"X-Device-Key": "dgk_test_key_cam001"},
    )
    assert_rejected(r)


def test_oversized_body_rejected(client):
    big = json.dumps({"device_id": "cam-001", "events": [make_event()], "pad": "x" * 300_000})
    r = client.post(
        "/api/v1/events",
        content=big,
        headers={"X-Device-Key": "dgk_test_key_cam001", "Content-Type": "application/json"},
    )
    assert r.status_code == 413


def test_nothing_stored_after_rejection(client):
    from tests.test_backend.conftest import login

    post_events(client, [make_event(image=JPEG_B64)])
    events = client.get("/api/v1/events", headers=login(client, "admin")).json()
    assert events == []


@pytest.mark.parametrize(
    "bad",
    [
        {"level": 4},
        {"reasons": ["sleepy"]},
        {"type": "other"},
        {"drowsy_score": 101},
        {"ts": "2026-09-24T08:00:00"},  # no timezone
        {"event_id": "not-a-uuid"},
    ],
)
def test_out_of_range_values_rejected(client, bad):
    assert_rejected(post_events(client, [make_event(**bad)]))
