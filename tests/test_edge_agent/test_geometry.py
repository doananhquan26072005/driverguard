"""edge_agent/perception/geometry.py against OpenCV (M45): the browser build runs the numpy versions,
the device OpenCV, and both must give the same head pose and the same boxes."""

import cv2
import numpy as np
import pytest

from edge_agent.perception import geometry
from edge_agent.perception.features import POSE_MODEL_POINTS, camera_matrix
from edge_agent.perception.geometry import _jacobian, _project, nms, rodrigues, rq_euler_degrees, solve_pnp

W, H = 640, 480
CAM = camera_matrix(W, H, 1.0)


def rvec_from(pitch, yaw, roll):
    """Rotation vector of Rz(roll) Ry(yaw) Rx(pitch), degrees."""
    rx, _ = cv2.Rodrigues(np.array([np.radians(pitch), 0.0, 0.0]))
    ry, _ = cv2.Rodrigues(np.array([0.0, np.radians(yaw), 0.0]))
    rz, _ = cv2.Rodrigues(np.array([0.0, 0.0, np.radians(roll)]))
    rvec, _ = cv2.Rodrigues(rz @ ry @ rx)
    return rvec.reshape(3)


def project(rvec, tvec):
    pts, _ = cv2.projectPoints(POSE_MODEL_POINTS, rvec, tvec, CAM, np.zeros(4))
    return pts.reshape(-1, 2)


def random_poses(n, seed, yaw=60.0, pitch=40.0, roll=30.0):
    rng = np.random.default_rng(seed)
    for _ in range(n):
        angles = rng.uniform(-1, 1, 3) * (pitch, yaw, roll)
        tvec = np.array([rng.uniform(-12, 12), rng.uniform(-8, 8), rng.uniform(35, 90)])
        yield rvec_from(*angles), tvec


def test_rodrigues_matches_opencv():
    rng = np.random.default_rng(0)
    for _ in range(200):
        r = rng.uniform(-3, 3, 3)
        assert np.allclose(rodrigues(r), cv2.Rodrigues(r)[0], atol=1e-10)
    assert np.allclose(rodrigues(np.zeros(3)), np.eye(3))


def test_euler_angles_match_rqdecomp():
    for rvec, _ in random_poses(300, seed=1, yaw=85, pitch=85, roll=85):
        rmat = cv2.Rodrigues(rvec)[0]
        want = cv2.RQDecomp3x3(rmat)[0]
        assert np.allclose(rq_euler_degrees(rmat), want, atol=1e-6)


def test_pose_without_a_guess_matches_opencv():
    worst = 0.0
    for rvec, tvec in random_poses(200, seed=2):
        image = project(rvec, tvec) + np.random.default_rng(3).normal(0, 0.3, (10, 2))  # landmark jitter
        ok_cv, r_cv, t_cv = cv2.solvePnP(POSE_MODEL_POINTS, image, CAM, np.zeros(4), flags=cv2.SOLVEPNP_ITERATIVE)
        ok, r, t = solve_pnp(POSE_MODEL_POINTS, image, CAM)
        assert ok and ok_cv and t[2, 0] > 0
        a = np.array(rq_euler_degrees(rodrigues(r)))
        b = np.array(cv2.RQDecomp3x3(cv2.Rodrigues(r_cv)[0])[0])
        worst = max(worst, float(np.abs(a - b).max()))
        assert np.allclose(t, t_cv, atol=0.05)
    assert worst < 0.05  # degrees


def test_pose_tracked_from_the_previous_frame_matches_opencv():
    """The extractor's case: each frame starts from the last pose, on both sides."""
    rng = np.random.default_rng(4)
    r_cv = t_cv = r = t = None
    for i in range(120):
        angles = (15 * np.sin(i / 9), 40 * np.sin(i / 14), 8 * np.sin(i / 5))
        image = project(rvec_from(*angles), np.array([2.0, -1.0, 55.0])) + rng.normal(0, 0.3, (10, 2))
        guess = r_cv is not None
        _, r_cv, t_cv = cv2.solvePnP(
            POSE_MODEL_POINTS,
            image,
            CAM,
            np.zeros(4),
            rvec=r_cv.copy() if guess else None,
            tvec=t_cv.copy() if guess else None,
            useExtrinsicGuess=guess,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )
        _, r, t = solve_pnp(POSE_MODEL_POINTS, image, CAM, r, t)
        a = np.array(rq_euler_degrees(rodrigues(r)))
        b = np.array(cv2.RQDecomp3x3(cv2.Rodrigues(r_cv)[0])[0])
        assert np.abs(a - b).max() < 0.05, (i, a, b)


def test_analytic_jacobian_matches_central_differences():
    """M49: the closed-form Jacobian of the projection, also at rvec = 0 (its own formula)."""
    poses = [np.concatenate([r, t]) for r, t in random_poses(40, seed=5, yaw=85, pitch=85, roll=85)]
    poses.append(np.array([0.0, 0.0, 0.0, 1.0, -2.0, 60.0]))
    for pose in poses:
        want = np.empty((2 * len(POSE_MODEL_POINTS), 6))
        for j in range(6):
            d = np.zeros(6)
            d[j] = 1e-6
            want[:, j] = (
                _project(POSE_MODEL_POINTS, pose + d, CAM) - _project(POSE_MODEL_POINTS, pose - d, CAM)
            ).ravel() / 2e-6
        assert np.allclose(_jacobian(POSE_MODEL_POINTS, pose, CAM), want, rtol=1e-5, atol=1e-4)


def test_tracking_needs_only_a_few_passes_per_frame(monkeypatch):
    """M49: the fit runs every frame in Pyodide. From the previous frame's pose it must not go back
    to dozens of projections per frame (it was ~100 with finite differences and a 1e-10 step limit)."""
    passes = {"n": 0}

    def counted(fn):
        def wrapper(*args):
            passes["n"] += 1
            return fn(*args)

        return wrapper

    monkeypatch.setattr(geometry, "_project", counted(geometry._project))
    monkeypatch.setattr(geometry, "_jacobian", counted(geometry._jacobian))
    rng = np.random.default_rng(6)
    r = t = None
    frames = 150
    for i in range(frames):
        angles = (10 * np.sin(i / 70), 25 * np.sin(i / 45), 5 * np.sin(i / 30))  # head turning at 30 FPS
        image = project(rvec_from(*angles), np.array([2.0, -1.0, 60.0])) + rng.normal(0, 0.3, (10, 2))
        ok, r, t = solve_pnp(POSE_MODEL_POINTS, image, CAM, r, t)
        assert ok
    assert passes["n"] / frames < 12


@pytest.mark.parametrize("seed", range(5))
def test_nms_keeps_the_same_boxes_as_opencv(seed):
    rng = np.random.default_rng(seed)
    n = 60
    centres = rng.uniform(50, 400, (n, 2))
    sizes = rng.uniform(20, 120, (n, 2))
    boxes = np.concatenate([centres - sizes / 2, sizes], axis=1)
    scores = rng.uniform(0.05, 0.99, n)
    want = [int(i) for i in np.array(cv2.dnn.NMSBoxes(boxes.tolist(), scores.tolist(), 0.35, 0.45)).reshape(-1)]
    assert nms(boxes, scores, 0.35, 0.45) == want


def test_nms_with_nothing_above_the_threshold():
    assert nms(np.array([[0, 0, 10, 10]]), np.array([0.1]), 0.35, 0.45) == []
