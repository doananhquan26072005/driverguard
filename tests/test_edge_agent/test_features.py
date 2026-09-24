import cv2
import numpy as np
import pytest

from edge_agent.perception.features import (
    LEFT_EYE,
    MOUTH_CORNERS,
    MOUTH_VERTICAL_PAIRS,
    POSE_LANDMARKS,
    POSE_MODEL_POINTS,
    RIGHT_EYE,
    FeatureExtractor,
    camera_matrix,
    eye_aspect_ratio,
    mouth_aspect_ratio,
)
from edge_agent.perception.landmarks import FaceLandmarks, bbox_area, in_frame_ratio

W, H = 640, 480


def euler_to_rvec(pitch, yaw, roll):
    """Inverse of the module convention: rotate about x (pitch), y (-yaw), z (roll)."""
    p, y, r = np.radians([pitch, -yaw, roll])
    rx = np.array([[1, 0, 0], [0, np.cos(p), -np.sin(p)], [0, np.sin(p), np.cos(p)]])
    ry = np.array([[np.cos(y), 0, np.sin(y)], [0, 1, 0], [-np.sin(y), 0, np.cos(y)]])
    rz = np.array([[np.cos(r), -np.sin(r), 0], [np.sin(r), np.cos(r), 0], [0, 0, 1]])
    rvec, _ = cv2.Rodrigues(rz @ ry @ rx)
    return rvec


def synthetic_landmarks(pitch=0.0, yaw=0.0, roll=0.0) -> FaceLandmarks:
    points = np.zeros((478, 3), dtype=np.float32)
    points[:, 0], points[:, 1] = W / 2, H / 2
    cam = camera_matrix(W, H, 1.0)
    tvec = np.array([0.0, 0.0, 60.0])  # face ~60 cm from the camera
    projected, _ = cv2.projectPoints(POSE_MODEL_POINTS, euler_to_rvec(pitch, yaw, roll), tvec, cam, np.zeros(4))
    for idx, (x, y) in zip(POSE_LANDMARKS, projected.reshape(-1, 2), strict=True):
        points[idx, :2] = (x, y)
    return FaceLandmarks(points, W, H, face_conf=1.0, num_faces=1, frame_id=3, timestamp=0.1)


def set_eye(points, idx, width, height):
    p1, p2, p3, p4, p5, p6 = idx
    points[p1, :2] = (0, 0)
    points[p4, :2] = (width, 0)
    points[p2, :2] = (width / 3, -height / 2)
    points[p3, :2] = (2 * width / 3, -height / 2)
    points[p6, :2] = (width / 3, height / 2)
    points[p5, :2] = (2 * width / 3, height / 2)


@pytest.mark.parametrize(("height", "expected"), [(10.0, 1 / 3), (0.0, 0.0)])
def test_eye_aspect_ratio(height, expected):
    points = np.zeros((478, 3), dtype=np.float32)
    set_eye(points, RIGHT_EYE, width=30.0, height=height)
    assert eye_aspect_ratio(points, RIGHT_EYE) == pytest.approx(expected)


def test_ear_is_symmetric_between_eyes():
    points = np.zeros((478, 3), dtype=np.float32)
    set_eye(points, RIGHT_EYE, 30.0, 9.0)
    set_eye(points, LEFT_EYE, 30.0, 9.0)
    assert eye_aspect_ratio(points, LEFT_EYE) == pytest.approx(eye_aspect_ratio(points, RIGHT_EYE))


def test_mouth_aspect_ratio():
    points = np.zeros((478, 3), dtype=np.float32)
    points[MOUTH_CORNERS[0], :2] = (0, 0)
    points[MOUTH_CORNERS[1], :2] = (50, 0)
    for up, lo in MOUTH_VERTICAL_PAIRS:
        points[up, :2] = (25, -15)
        points[lo, :2] = (25, 15)
    assert mouth_aspect_ratio(points) == pytest.approx(30 / 50)


def test_degenerate_eye_does_not_divide_by_zero():
    points = np.zeros((478, 3), dtype=np.float32)
    assert eye_aspect_ratio(points, LEFT_EYE) == 0.0
    assert mouth_aspect_ratio(points) == 0.0


@pytest.mark.parametrize(
    ("pitch", "yaw", "roll"),
    [(0, 0, 0), (20, 0, 0), (-15, 0, 0), (0, 30, 0), (0, -30, 0), (0, 0, 15), (10, -20, 5)],
)
def test_head_pose_recovers_known_angles(pitch, yaw, roll):
    feats = FeatureExtractor()(synthetic_landmarks(pitch, yaw, roll), frame_id=3, timestamp=0.1)
    assert feats.pitch == pytest.approx(pitch, abs=1.0)
    assert feats.yaw == pytest.approx(yaw, abs=1.0)
    assert feats.roll == pytest.approx(roll, abs=1.0)


def test_head_pose_sign_conventions_in_image():
    """pitch>0 moves the nose down, yaw>0 moves it right, roll>0 turns the eye line clockwise."""
    nose, r_eye, l_eye = 1, 33, 263

    def nose_offset(**angles):
        # Nose tip relative to the centre of the other pose points (the nose sits in front of them).
        pts = synthetic_landmarks(**angles).points
        others = [i for i in POSE_LANDMARKS if i != nose]
        return pts[nose, :2] - pts[others, :2].mean(axis=0)

    base = nose_offset()
    assert nose_offset(pitch=20)[1] > base[1]
    assert nose_offset(yaw=20)[0] > base[0]
    rolled = synthetic_landmarks(roll=20).points
    assert rolled[l_eye, 1] > rolled[r_eye, 1]  # image-right eye drops = clockwise


def test_open_mouth_does_not_change_head_pose():
    """Yawning moves chin and lips; they are excluded from solvePnP so pitch must not jump."""
    lm = synthetic_landmarks(pitch=5)
    before = FeatureExtractor()(lm, 0, 0.0)
    moved = lm.points.copy()
    moved[[152, 14, 17, 87, 317], 1] += 40  # jaw drops 40 px
    after = FeatureExtractor()(FaceLandmarks(moved, W, H, 1.0, 1, 0, 0.0), 0, 0.0)
    assert after.pitch == pytest.approx(before.pitch, abs=0.01)


def test_no_face_gives_empty_features_and_resets_pose():
    ex = FeatureExtractor()
    ex(synthetic_landmarks(10, 0, 0), 0, 0.0)
    feats = ex(None, frame_id=5, timestamp=1.0)
    assert not feats.face_found
    assert feats.face_conf == 0.0
    assert feats.ear is None and feats.pitch is None
    assert (feats.frame_id, feats.timestamp) == (5, 1.0)
    assert ex.pose_vectors is None


def test_pose_tracking_across_frames():
    ex = FeatureExtractor()
    for p in range(0, 30, 5):
        feats = ex(synthetic_landmarks(pitch=p), 0, 0.0)
        assert feats.pitch == pytest.approx(p, abs=1.0)


def test_landmark_helpers():
    pts = np.array([[0, 0, 0], [10, 20, 0], [700, 5, 0], [5, 5, 0]], dtype=np.float32)
    assert bbox_area(pts) == pytest.approx(700 * 20)
    assert in_frame_ratio(pts, W, H) == pytest.approx(0.75)
