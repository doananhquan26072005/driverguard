"""Numpy versions of the few OpenCV calls blocks 4 and 6 need, for where OpenCV is not installed.

The browser build (#/live, Pyodide) used to download OpenCV (11.7 MB) for three things only: the
head pose of block 6 (solvePnP + Rodrigues + RQDecomp3x3) and the box suppression of block 4
(dnn.NMSBoxes). They are small enough to write out. The device keeps OpenCV; here are the same
computations in numpy, and tests/test_edge_agent/test_geometry.py holds them against OpenCV on
random poses and boxes, so both sides see the same numbers.

- rodrigues:           rotation vector -> matrix
- rq_euler_degrees:    the Euler angles cv2.RQDecomp3x3 returns for a rotation matrix
- solve_pnp:           pose minimising the reprojection error (Levenberg-Marquardt, as
                       cv2.SOLVEPNP_ITERATIVE does from an extrinsic guess)
- nms:                 greedy non-maximum suppression, the kept indices in score order

solve_pnp runs on every frame, in Pyodide, where each numpy call costs far more than on the device.
Its Jacobian is therefore analytic (one pass instead of 12 projections per iteration, M49) and the
fit stops once a step no longer moves the pose (tools/bench_web.py measures the calls per frame).
"""

from __future__ import annotations

import math

import numpy as np

PNP_MAX_ITERATIONS = 30
# A step shorter than this (radians / model units, ~1e-4 degrees) ends the fit: the tests hold the
# result within 0.05 degrees of OpenCV, and tracking from the previous frame gets here in a few steps.
PNP_STEP_EPS = 1e-6
# Starts tried without a previous pose (yaw in degrees about the camera's y axis): a face seen from
# the side must not settle in the mirrored minimum next to the frontal start.
PNP_START_YAWS_DEG = (0.0, 50.0, -50.0)


def rodrigues(rvec: np.ndarray) -> np.ndarray:
    """Rotation vector (3,) or (3, 1) -> 3 x 3 rotation matrix."""
    x, y, z = (float(v) for v in np.asarray(rvec, dtype=np.float64).reshape(3))
    theta = math.sqrt(x * x + y * y + z * z)
    if theta < 1e-12:
        return np.eye(3)
    x, y, z = x / theta, y / theta, z / theta
    c, s = math.cos(theta), math.sin(theta)
    v = 1.0 - c
    return np.array(
        [
            [c + v * x * x, v * x * y - s * z, v * x * z + s * y],
            [v * x * y + s * z, c + v * y * y, v * y * z - s * x],
            [v * x * z - s * y, v * y * z + s * x, c + v * z * z],
        ]
    )


def _skew(x: float, y: float, z: float) -> np.ndarray:
    return np.array([[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]])


_UNIT_SKEWS = (_skew(1.0, 0.0, 0.0), _skew(0.0, 1.0, 0.0), _skew(0.0, 0.0, 1.0))


def _rotation_derivatives(rvec: np.ndarray, rmat: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """dR / d(rvec[i]) for i = 0, 1, 2 (Gallego & Yezzi 2015, eq. 9):
    (v_i [v]x + [v x (I - R) e_i]x) R / |v|^2, and [e_i]x at v = 0."""
    x, y, z = (float(v) for v in rvec)
    theta2 = x * x + y * y + z * z
    if theta2 < 1e-24:
        return _UNIT_SKEWS
    vx = _skew(x, y, z)
    out = []
    for i, vi in enumerate((x, y, z)):
        a, b, c = (float(k) for k in (np.eye(3) - rmat)[:, i])
        w = _skew(y * c - z * b, z * a - x * c, x * b - y * a)  # v x (I - R) e_i
        out.append((vi * vx + w) @ rmat / theta2)
    return out[0], out[1], out[2]


def rq_euler_degrees(rmat: np.ndarray) -> tuple[float, float, float]:
    """Euler angles (x, y, z, degrees) of cv2.RQDecomp3x3 for a rotation matrix: three Givens
    rotations that zero m32, m31 and m21 in turn."""
    m = np.asarray(rmat, dtype=np.float64)

    def unit(c: float, s: float) -> tuple[float, float]:
        n = float(np.hypot(c, s))
        return (1.0, 0.0) if n < 1e-15 else (c / n, s / n)

    c, s = unit(m[2, 2], m[2, 1])
    qx = np.array([[1.0, 0.0, 0.0], [0.0, c, s], [0.0, -s, c]])
    r = m @ qx
    ax = np.degrees(np.arccos(np.clip(c, -1.0, 1.0))) * (1.0 if s >= 0 else -1.0)

    c, s = unit(r[2, 2], -r[2, 0])
    qy = np.array([[c, 0.0, -s], [0.0, 1.0, 0.0], [s, 0.0, c]])
    m2 = r @ qy
    ay = np.degrees(np.arccos(np.clip(c, -1.0, 1.0))) * (1.0 if s >= 0 else -1.0)

    c, s = unit(m2[1, 1], m2[1, 0])
    az = np.degrees(np.arccos(np.clip(c, -1.0, 1.0))) * (1.0 if s >= 0 else -1.0)
    return float(ax), float(ay), float(az)


def _project(model: np.ndarray, pose: np.ndarray, cam: np.ndarray) -> np.ndarray:
    """Model points -> image points (N, 2) for pose = (rvec, tvec); NaN-free only in front of the camera."""
    p = model @ rodrigues(pose[:3]).T + pose[3:]
    z = p[:, 2:3]
    return p[:, :2] / z * np.array([cam[0, 0], cam[1, 1]]) + np.array([cam[0, 2], cam[1, 2]])


def _jacobian(model: np.ndarray, pose: np.ndarray, cam: np.ndarray) -> np.ndarray:
    """d(image points, ravelled as u0, v0, u1, v1, ...) / d(pose): (2 N, 6), in closed form."""
    fx, fy = cam[0, 0], cam[1, 1]
    rmat = rodrigues(pose[:3])
    p = model @ rmat.T + pose[3:]
    x, y, iz = p[:, 0], p[:, 1], 1.0 / p[:, 2]
    jac = np.zeros((2 * len(model), 6))
    for i, d in enumerate(_rotation_derivatives(pose[:3], rmat)):
        dp = model @ d.T  # how each point moves with rvec[i]
        jac[0::2, i] = fx * iz * (dp[:, 0] - x * iz * dp[:, 2])
        jac[1::2, i] = fy * iz * (dp[:, 1] - y * iz * dp[:, 2])
    jac[0::2, 3] = fx * iz
    jac[1::2, 4] = fy * iz
    jac[0::2, 5] = -fx * x * iz * iz
    jac[1::2, 5] = -fy * y * iz * iz
    return jac


def _refine(model: np.ndarray, image: np.ndarray, cam: np.ndarray, pose: np.ndarray) -> tuple[np.ndarray, float]:
    """Levenberg-Marquardt on the reprojection error from `pose`. Returns (pose, squared error)."""

    def residual(x: np.ndarray) -> np.ndarray:
        return (_project(model, x, cam) - image).ravel()

    r = residual(pose)
    err = float(r @ r)
    lam = 1e-3
    for _ in range(PNP_MAX_ITERATIONS):
        jac = _jacobian(model, pose, cam)
        a, g = jac.T @ jac, jac.T @ r
        improved = False
        for _ in range(10):
            try:
                step = np.linalg.solve(a + lam * np.diag(np.diag(a) + 1e-12), -g)
            except np.linalg.LinAlgError:
                lam *= 10.0
                continue
            trial = pose + step
            rt = residual(trial)
            et = float(rt @ rt)
            if np.isfinite(et) and et < err:
                pose, r, err, lam, improved = trial, rt, et, lam * 0.3, True
                break
            lam *= 10.0
        if not improved or float(np.linalg.norm(step)) < PNP_STEP_EPS:
            break
    return pose, err


def solve_pnp(
    model: np.ndarray,
    image: np.ndarray,
    cam: np.ndarray,
    rvec: np.ndarray | None = None,
    tvec: np.ndarray | None = None,
) -> tuple[bool, np.ndarray, np.ndarray]:
    """Pose of `model` (N, 3) seen at `image` (N, 2) by a camera without distortion.

    rvec / tvec: a previous pose to start from (the tracker's case). Without one, a few starts
    facing the camera are tried and the best fit is kept. Returns (ok, rvec (3, 1), tvec (3, 1)).
    """
    model = np.asarray(model, dtype=np.float64)
    image = np.asarray(image, dtype=np.float64)
    if rvec is not None and tvec is not None:
        starts = [np.concatenate([np.asarray(rvec, float).reshape(3), np.asarray(tvec, float).reshape(3)])]
    else:
        # Distance from the apparent size, position from where the points sit in the image.
        span_model = float(np.linalg.norm(model.max(axis=0)[:2] - model.min(axis=0)[:2]))
        span_image = float(np.linalg.norm(image.max(axis=0) - image.min(axis=0)))
        z = cam[0, 0] * span_model / max(span_image, 1e-6)
        centre = image.mean(axis=0)
        t0 = np.array([(centre[0] - cam[0, 2]) * z / cam[0, 0], (centre[1] - cam[1, 2]) * z / cam[1, 1], z])
        starts = []
        for yaw in PNP_START_YAWS_DEG:
            r0 = np.array([0.0, np.radians(yaw), 0.0])
            starts.append(np.concatenate([r0, t0 - rodrigues(r0) @ model.mean(axis=0)]))
    best, best_err = None, np.inf
    for start in starts:
        pose, err = _refine(model, image, cam, start)
        if np.isfinite(err) and err < best_err:
            best, best_err = pose, err
    if best is None:
        return False, np.zeros((3, 1)), np.zeros((3, 1))
    return True, best[:3].reshape(3, 1), best[3:].reshape(3, 1)


def nms(boxes_xywh: np.ndarray, scores: np.ndarray, score_threshold: float, iou_threshold: float) -> list[int]:
    """cv2.dnn.NMSBoxes: indices kept, best score first. A box is dropped when it overlaps a kept one
    by more than iou_threshold."""
    boxes = np.asarray(boxes_xywh, dtype=np.float64).reshape(-1, 4)
    scores = np.asarray(scores, dtype=np.float64).reshape(-1)
    order = [int(i) for i in np.argsort(-scores, kind="stable") if scores[i] > score_threshold]
    x1, y1 = boxes[:, 0], boxes[:, 1]
    x2, y2 = x1 + boxes[:, 2], y1 + boxes[:, 3]
    area = boxes[:, 2] * boxes[:, 3]
    kept: list[int] = []
    for i in order:
        ok = True
        for k in kept:
            w = min(x2[i], x2[k]) - max(x1[i], x1[k])
            h = min(y2[i], y2[k]) - max(y1[i], y1[k])
            inter = max(w, 0.0) * max(h, 0.0)
            union = area[i] + area[k] - inter
            if union > 0 and inter / union > iou_threshold:
                ok = False
                break
        if ok:
            kept.append(i)
    return kept
