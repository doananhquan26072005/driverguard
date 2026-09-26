"""Block 6 - Per-frame feature extractor.

From 478 MediaPipe landmarks compute:
- ear (Eye Aspect Ratio), per eye and mean: small when the eye is closed.
- mar (Mouth Aspect Ratio): large when the mouth is open (yawn).
- pitch / yaw / roll in degrees via cv2.solvePnP against a generic 3D face model.

Angle conventions (camera looking at the driver):
- pitch > 0: head tilted down (nodding), < 0: looking up
- yaw   > 0: face turned towards image right, < 0: towards image left
- roll  > 0: head tilted clockwise in the image

Output is `FrameFeatures`, always produced (fields are None when no face),
so the temporal blocks get one sample per frame.

face_reliable: face_conf (fraction of landmarks inside the image) >= `min_face_conf`.
A face partly out of frame has extrapolated landmarks, so EAR / MAR / pose are kept for
display but blocks 7 and 8 treat the frame as "not measurable".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

from edge_agent.config import config_from_dict
from edge_agent.perception.landmarks import FaceLandmarks

# MediaPipe Face Mesh indices. "Right"/"left" are the driver's own sides.
# EAR order: p1 (outer corner), p2, p3 (upper lid), p4 (inner corner), p5, p6 (lower lid).
RIGHT_EYE = (33, 160, 158, 133, 153, 144)
LEFT_EYE = (263, 387, 385, 362, 380, 373)
# Inner lip: corners, then (upper, lower) pairs.
MOUTH_CORNERS = (78, 308)
MOUTH_VERTICAL_PAIRS = ((82, 87), (13, 14), (312, 317))

# Head pose: 3D points from MediaPipe's canonical face model
# (mediapipe/modules/face_geometry/data/canonical_face_model.obj, units ~cm), converted to
# camera-aligned axes (x right, y down, z away from camera) with the nose tip at origin.
# Only rigid points: chin and mouth move when yawning and would fake a head nod.
POSE_LANDMARKS = (1, 6, 168, 10, 33, 133, 362, 263, 234, 454)
POSE_MODEL_POINTS = np.array(
    [
        (0.0, 0.0, 0.0),  # 1   nose tip
        (0.0, -3.600, 1.687),  # 6   nose bridge
        (0.0, -4.398, 2.240),  # 168 between the eyes
        (0.0, -9.389, 2.994),  # 10  forehead
        (-4.446, -3.791, 4.302),  # 33  right eye outer corner (image left)
        (-1.856, -3.712, 3.718),  # 133 right eye inner corner
        (1.856, -3.712, 3.718),  # 362 left eye inner corner
        (4.446, -3.791, 4.302),  # 263 left eye outer corner (image right)
        (-7.664, -1.800, 9.911),  # 234 right cheek edge (image left)
        (7.664, -1.800, 9.911),  # 454 left cheek edge (image right)
    ],
    dtype=np.float64,
)


@dataclass(frozen=True)
class FeatureConfig:
    # Camera focal length in pixels = focal_length_scale * image width (no calibration).
    focal_length_scale: float = 1.0
    # Below this face_conf the measurements are not trusted (face_reliable = False).
    min_face_conf: float = 0.9

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> FeatureConfig:
        return config_from_dict(cls, d, "features")


@dataclass(frozen=True)
class FrameFeatures:
    frame_id: int
    timestamp: float
    face_found: bool
    face_conf: float
    face_reliable: bool = True  # face_found and face_conf >= features.min_face_conf
    ear: float | None = None
    ear_left: float | None = None
    ear_right: float | None = None
    mar: float | None = None
    pitch: float | None = None
    yaw: float | None = None
    roll: float | None = None
    # MediaPipe blendshape eyeBlink, mean of both eyes (0 open .. 1 shut); None when off (block 3).
    eye_blink: float | None = None
    # Block 5 (eye-state score), only set on frames where EAR is not reliable.
    p_closed: float | None = None
    eye_cnn_reason: str | None = None


def _dist(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b))


def eye_aspect_ratio(points: np.ndarray, idx: tuple[int, ...]) -> float:
    p1, p2, p3, p4, p5, p6 = (points[i, :2] for i in idx)
    width = _dist(p1, p4)
    if width < 1e-6:
        return 0.0
    return (_dist(p2, p6) + _dist(p3, p5)) / (2.0 * width)


def mouth_aspect_ratio(points: np.ndarray) -> float:
    width = _dist(points[MOUTH_CORNERS[0], :2], points[MOUTH_CORNERS[1], :2])
    if width < 1e-6:
        return 0.0
    height = np.mean([_dist(points[u, :2], points[lo, :2]) for u, lo in MOUTH_VERTICAL_PAIRS])
    return float(height / width)


def camera_matrix(width: int, height: int, focal_length_scale: float) -> np.ndarray:
    f = focal_length_scale * width
    return np.array([[f, 0, width / 2.0], [0, f, height / 2.0], [0, 0, 1]], dtype=np.float64)


def rotation_to_euler(rvec: np.ndarray) -> tuple[float, float, float]:
    """Rotation vector -> (pitch, yaw, roll) in degrees using the module conventions."""
    rmat, _ = cv2.Rodrigues(rvec)
    angles, *_ = cv2.RQDecomp3x3(rmat)
    ax, ay, az = angles
    return float(ax), float(-ay), float(az)


class FeatureExtractor:
    """Stateful only for solvePnP: reuses the previous pose as initial guess to reduce jitter."""

    def __init__(self, config: FeatureConfig | None = None) -> None:
        self.config = config or FeatureConfig()
        self._rvec: np.ndarray | None = None
        self._tvec: np.ndarray | None = None

    def reset(self) -> None:
        self._rvec = self._tvec = None

    @property
    def pose_vectors(self) -> tuple[np.ndarray, np.ndarray] | None:
        """(rvec, tvec) of the last successful solvePnP, for drawing the head axes."""
        if self._rvec is None or self._tvec is None:
            return None
        return self._rvec, self._tvec

    def head_pose(self, lm: FaceLandmarks) -> tuple[float, float, float] | None:
        image_points = lm.points[list(POSE_LANDMARKS), :2].astype(np.float64)
        cam = camera_matrix(lm.image_width, lm.image_height, self.config.focal_length_scale)
        use_guess = self._rvec is not None
        ok, rvec, tvec = cv2.solvePnP(
            POSE_MODEL_POINTS,
            image_points,
            cam,
            np.zeros(4),
            rvec=self._rvec.copy() if use_guess else None,
            tvec=self._tvec.copy() if use_guess else None,
            useExtrinsicGuess=use_guess,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )
        if not ok or tvec[2, 0] <= 0:  # face must be in front of the camera
            self.reset()
            return None
        self._rvec, self._tvec = rvec, tvec
        return rotation_to_euler(rvec)

    def __call__(self, lm: FaceLandmarks | None, frame_id: int, timestamp: float) -> FrameFeatures:
        if lm is None:
            self.reset()
            return FrameFeatures(
                frame_id=frame_id, timestamp=timestamp, face_found=False, face_conf=0.0, face_reliable=False
            )

        ear_left = eye_aspect_ratio(lm.points, LEFT_EYE)
        ear_right = eye_aspect_ratio(lm.points, RIGHT_EYE)
        pose = self.head_pose(lm)
        pitch, yaw, roll = pose if pose is not None else (None, None, None)
        return FrameFeatures(
            frame_id=frame_id,
            timestamp=timestamp,
            face_found=True,
            face_conf=lm.face_conf,
            face_reliable=lm.face_conf >= self.config.min_face_conf,
            ear=(ear_left + ear_right) / 2.0,
            ear_left=ear_left,
            ear_right=ear_right,
            mar=mouth_aspect_ratio(lm.points),
            pitch=pitch,
            yaw=yaw,
            roll=roll,
            eye_blink=None if lm.eye_blink is None else (lm.eye_blink[0] + lm.eye_blink[1]) / 2.0,
        )
