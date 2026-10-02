"""In-browser agent bridge (edge_agent/web/bridge.py) driven by fake landmark sequences, no browser."""

import json

import numpy as np
import pytest

from edge_agent.perception.features import (
    LEFT_EYE,
    MOUTH_CORNERS,
    MOUTH_VERTICAL_PAIRS,
    POSE_LANDMARKS,
    POSE_MODEL_POINTS,
    RIGHT_EYE,
)
from edge_agent.web.bridge import WebAgent, web_thresholds

W, H = 640, 480
FPS = 30.0


def project(p: np.ndarray, distance_cm: float = 60.0) -> np.ndarray:
    """Pinhole camera with f = image width (features.focal_length_scale = 1), face looking at the camera."""
    z = distance_cm + p[2]
    return np.array([W * p[0] / z + W / 2, W * p[1] / z + H / 2, W * p[2] / z])


def synthetic_face(ear: float = 0.30, mar: float = 0.05) -> np.ndarray:
    """478 landmarks: rigid pose points from the canonical model, eyes and mouth set to the given EAR / MAR."""
    pts = np.zeros((478, 3), dtype=np.float32)
    model = {idx: project(p) for idx, p in zip(POSE_LANDMARKS, POSE_MODEL_POINTS, strict=True)}
    nose = model[1]
    rng = np.random.default_rng(0)  # the rest of the mesh: spread over the face box
    pts[:, 0] = nose[0] + rng.uniform(-75, 75, 478)
    pts[:, 1] = nose[1] + rng.uniform(-90, 60, 478)
    for idx, p in model.items():
        pts[idx] = p
    for eye in (RIGHT_EYE, LEFT_EYE):
        outer, inner = pts[eye[0], :2], pts[eye[3], :2]
        width = float(np.linalg.norm(inner - outer))
        for k, (upper, lower) in enumerate(((eye[1], eye[5]), (eye[2], eye[4]))):
            x = outer[0] + (inner[0] - outer[0]) * (k + 1) / 3
            y = (outer[1] + inner[1]) / 2
            pts[upper, :2] = (x, y - ear * width / 2)
            pts[lower, :2] = (x, y + ear * width / 2)
    left, right = nose[0] - 25, nose[0] + 25
    mouth_y = nose[1] + 30
    pts[MOUTH_CORNERS[0], :2] = (left, mouth_y)
    pts[MOUTH_CORNERS[1], :2] = (right, mouth_y)
    for k, (upper, lower) in enumerate(MOUTH_VERTICAL_PAIRS):
        x = left + 50 * (k + 1) / 4
        pts[upper, :2] = (x, mouth_y - mar * 50 / 2)
        pts[lower, :2] = (x, mouth_y + mar * 50 / 2)
    return pts


def run(agent, seconds, t0=0.0, points=None, blink=(0.05, 0.05), frame0=0):
    state = None
    n = int(seconds * FPS)
    for i in range(n):
        p = None if points is None else points.ravel()
        state = agent.frame(t0 + i / FPS, frame0 + i, W, H, p, 1, blink, 12.0, 140.0)
    return json.loads(state), t0 + n / FPS, frame0 + n


@pytest.fixture
def agent():
    return WebAgent("web-an", "trip-web-1", scenario="highway_night")


def events_of(agent):
    body = agent.take_batch()
    return [] if body is None else json.loads(body).get("events", [])


def test_awake_driver_stays_l0(agent):
    state, _, _ = run(agent, 12, points=synthetic_face())
    assert state["connected"] and state["level"] == 0
    assert state["measures"]["face"] and abs(state["measures"]["ear"] - 0.30) < 0.01
    assert abs(state["measures"]["yaw"]) < 3 and abs(state["measures"]["pitch"]) < 3
    assert agent.take_batch() is None  # nothing to send


def test_eyes_shut_while_driving_is_l3_microsleep(agent):
    _, t, f = run(agent, 12, points=synthetic_face())  # learn the open-eye baseline
    state, _, _ = run(agent, 2.5, t0=t, frame0=f, points=synthetic_face(ear=0.05), blink=(0.9, 0.9))
    assert state["level"] == 3 and "microsleep" in state["reasons"]
    events = events_of(agent)
    assert [e["level"] for e in events] == [3] and events[0]["reasons"] == ["microsleep"]


def test_batch_body_goes_to_the_users_browser_device(agent):
    _, t, f = run(agent, 12, points=synthetic_face())
    run(agent, 2.5, t0=t, frame0=f, points=synthetic_face(ear=0.05), blink=(0.9, 0.9))
    body = json.loads(agent.take_batch())
    assert body["device_id"] == "web-an" and body["events"][0]["trip_id"] == "trip-web-1"
    assert "image" not in json.dumps(body)


def test_no_face_while_driving_is_unavailable(agent):
    _, t, f = run(agent, 12, points=synthetic_face())
    state, t, f = run(agent, 4, t0=t, frame0=f, points=None)
    assert state["unavailable"] and state["level"] == 0 and state["reasons"] == []
    state, _, _ = run(agent, 1, t0=t, frame0=f, points=synthetic_face())
    assert not state["unavailable"]
    reasons = [e["reasons"] for e in events_of(agent)]
    assert reasons == [["monitoring_unavailable"], ["monitoring_restored"]]


def yolo_output_with_phone(box_xywh, num_boxes=8, classes=80):
    out = np.zeros((1, 4 + classes, num_boxes), dtype=np.float32)
    out[0, :4, 0] = box_xywh
    out[0, 4 + 67, 0] = 0.9  # COCO cell phone
    return out.ravel()


def test_phone_at_the_face_is_l2_phone(agent):
    face = synthetic_face()
    _, t, f = run(agent, 12, points=face)
    cx, cy = float(face[1, 0]), float(face[1, 1]) + 40  # phone just below the nose, letterbox pad 80 px on y
    out = yolo_output_with_phone((cx, cy + 80, 60, 100))
    state = None
    for i in range(int(3 * FPS)):
        now = t + i / FPS
        if i % 6 == 0:  # YOLO at 5 Hz
            assert agent.phone_output(out, 8, 1.0, 0, 80, W, H, now) == 1
        state = json.loads(agent.frame(now, f + i, W, H, face.ravel(), 1, (0.05, 0.05), 12.0, 140.0))
    assert state["measures"]["phone"] is True
    assert state["level"] == 2 and "phone" in state["reasons"]


def test_stale_phone_result_is_unknown(agent):
    face = synthetic_face()
    _, t, f = run(agent, 12, points=face)
    agent.phone_output(yolo_output_with_phone((320, 320, 60, 100)), 8, 1.0, 0, 80, W, H, t - 5.0)
    state = json.loads(agent.frame(t, f, W, H, face.ravel(), 1, (0.05, 0.05), 12.0, 140.0))
    assert state["measures"]["phone"] is None


def test_false_alarm_feedback_is_queued(agent):
    _, t, f = run(agent, 12, points=synthetic_face())
    run(agent, 2.5, t0=t, frame0=f, points=synthetic_face(ear=0.05), blink=(0.9, 0.9))
    event_id = events_of(agent)[0]["event_id"]
    assert agent.false_alarm(event_id) == "ok"
    assert agent.false_alarm(event_id) == "duplicate"
    feedback = json.loads(agent.take_batch())["feedback"]
    assert [fb["event_id"] for fb in feedback] == [event_id]


def test_camera_lost_is_a_system_event(agent):
    agent.camera(True)
    assert agent.hud.to_json()["camera_lost"] is True
    assert events_of(agent)[0]["reasons"] == ["camera_lost"]


def test_typed_array_buffer_accepted(agent):
    face = synthetic_face()
    state = json.loads(agent.frame(0.0, 0, W, H, memoryview(face.ravel().tobytes()), 1, None, 12.0, 140.0))
    assert state["measures"]["face"] is True


def test_browser_uses_blendshape_eye_state_and_tuned_values():
    th, problems = web_thresholds({"risk.microsleep_l3_s": 2.0})
    assert th["eye_state"]["source"] == "blendshape" and th["risk"]["microsleep_l3_s"] == 2.0 and problems == []
    th, problems = web_thresholds({"risk.nope": 1.0})
    assert problems and th["risk"]["microsleep_l3_s"] == 1.5  # rejected overrides: file values kept


def test_unknown_scenario_rejected():
    with pytest.raises(ValueError):
        WebAgent("web-an", "trip", scenario="moon")


def test_settings_come_from_thresholds(agent):
    s = json.loads(agent.settings())
    assert s["phone"] == {"input_size": 640, "target_fps": 5} and s["target_width"] == 640
    assert s["landmarks"]["num_faces"] == 2 and s["flush_interval_s"] == 5.0 and s["problems"] == []


def test_grey_frame_counts_as_infrared(agent):
    face = synthetic_face().ravel()
    agent.frame(0.0, 0, W, H, face, 1, (0.05, 0.05), 0.5, 140.0)  # channels nearly equal
    assert agent.eye_state.runs == 1  # IR: block 5 uses the eye-state score
    agent.frame(0.1, 1, W, H, face, 1, (0.05, 0.05), 12.0, 140.0)
    assert agent.eye_state.runs == 2  # held for eye_state.hold_s after IR


def test_every_face_goes_in_and_the_largest_is_the_driver_before_enrollment(agent):
    driver = synthetic_face(ear=0.30)
    small = synthetic_face(ear=0.20)
    small[:, :2] = (small[:, :2] - small[1, :2]) * 0.6 + (120, 300)  # a passenger further back
    faces = np.stack([small, driver]).ravel()
    state = json.loads(agent.frame(0.0, 0, W, H, faces, 2, (0.05, 0.05, 0.05, 0.05), 12.0, 140.0))
    assert abs(state["measures"]["ear"] - 0.30) < 0.01


def test_hud_state_carries_the_enrollment_step():
    parked = WebAgent("web-an", "trip-web-2", scenario="parked")
    state, t, n = run(parked, 0.2, points=synthetic_face())
    assert state["enrollment"]["status"] == "consent"
    assert parked.vehicle("enroll_start") == "ok"
    state, _, _ = run(parked, 1, t0=t, points=synthetic_face(), frame0=n)
    assert state["enrollment"]["status"] == "look_camera"
    assert 0 < state["enrollment"]["progress"] < 1


def test_a_failing_frame_is_caught_and_a_lasting_failure_shows_on_the_hud(agent, monkeypatch):
    """M28: an exception in the frame path must not reach the page (it used to console.error every frame)."""
    face = synthetic_face()
    _, t, n = run(agent, 1, points=face)

    def broken(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(agent, "extractor", broken)
    state, t, n = run(agent, 2, t0=t, points=face, frame0=n)
    assert state["processing_error"] is True and state["measures"]["face"] is False
    monkeypatch.undo()
    state, _, _ = run(agent, 0.2, t0=t, points=face, frame0=n)
    assert state["processing_error"] is False
    reasons = [e["reasons"] for e in events_of(agent)]
    assert ["agent_error"] in reasons and ["agent_recovered"] in reasons
