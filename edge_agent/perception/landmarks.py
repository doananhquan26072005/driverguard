"""Block 3 - Face landmarks (MediaPipe Face Landmarker, 478 points).

Wraps the MediaPipe Tasks API in VIDEO mode (uses tracking between frames, faster
than per-image detection). Returns `FaceLandmarks` in pixel coordinates of the
preprocessed image, or None when no face is found.

When several faces are visible (e.g. a passenger), the largest one is taken as
the driver, since the driver sits closest to the camera.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

from edge_agent.config import PROJECT_ROOT, config_from_dict
from edge_agent.perception.preprocess import PreprocessedFrame


@dataclass(frozen=True)
class LandmarkConfig:
    model_path: str = "models/face_landmarker.task"
    num_faces: int = 2
    min_face_detection_confidence: float = 0.5
    min_face_presence_confidence: float = 0.5
    min_tracking_confidence: float = 0.5

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> LandmarkConfig:
        return config_from_dict(cls, d, "landmarks")

    def resolved_model_path(self) -> Path:
        p = Path(self.model_path)
        return p if p.is_absolute() else PROJECT_ROOT / p


@dataclass(frozen=True)
class FaceLandmarks:
    points: np.ndarray  # (478, 3) float32: x, y in pixels; z in pixels (same scale as x), smaller = closer
    image_width: int
    image_height: int
    # MediaPipe Tasks exposes no per-face score; faces below min_face_presence_confidence
    # are already rejected. face_conf is the fraction of landmarks inside the image,
    # so a face partially out of frame gets a lower confidence.
    face_conf: float
    num_faces: int  # faces seen in the frame (driver + others)
    frame_id: int
    timestamp: float


def bbox_area(points: np.ndarray) -> float:
    xy = points[:, :2]
    w, h = xy.max(axis=0) - xy.min(axis=0)
    return float(w * h)


def in_frame_ratio(points: np.ndarray, width: int, height: int) -> float:
    x, y = points[:, 0], points[:, 1]
    inside = (x >= 0) & (x < width) & (y >= 0) & (y < height)
    return float(inside.mean())


class FaceLandmarkDetector:
    def __init__(self, config: LandmarkConfig | None = None, image_mode: bool = False) -> None:
        """image_mode: unrelated still images (dataset evaluation), no tracking between calls."""
        self.config = config or LandmarkConfig()
        self.image_mode = image_mode
        model = self.config.resolved_model_path()
        if not model.exists():
            raise FileNotFoundError(f"Model not found: {model}. Run: python tools/download_models.py")
        options = vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model)),
            running_mode=vision.RunningMode.IMAGE if image_mode else vision.RunningMode.VIDEO,
            num_faces=self.config.num_faces,
            min_face_detection_confidence=self.config.min_face_detection_confidence,
            min_face_presence_confidence=self.config.min_face_presence_confidence,
            min_tracking_confidence=self.config.min_tracking_confidence,
        )
        self._landmarker = vision.FaceLandmarker.create_from_options(options)
        self._last_ts_ms = -1

    def close(self) -> None:
        self._landmarker.close()

    def __enter__(self) -> FaceLandmarkDetector:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _next_timestamp_ms(self, timestamp: float) -> int:
        # VIDEO mode requires strictly increasing timestamps.
        ts = max(int(timestamp * 1000), self._last_ts_ms + 1)
        self._last_ts_ms = ts
        return ts

    def detect(self, frame: PreprocessedFrame) -> FaceLandmarks | None:
        h, w = frame.image.shape[:2]
        rgb = cv2.cvtColor(frame.image, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        if self.image_mode:
            result = self._landmarker.detect(mp_image)
        else:
            result = self._landmarker.detect_for_video(mp_image, self._next_timestamp_ms(frame.timestamp))
        if not result.face_landmarks:
            return None

        faces = [
            np.array([(lm.x * w, lm.y * h, lm.z * w) for lm in face], dtype=np.float32)
            for face in result.face_landmarks
        ]
        driver = max(faces, key=bbox_area)
        return FaceLandmarks(
            points=driver,
            image_width=w,
            image_height=h,
            face_conf=in_frame_ratio(driver, w, h),
            num_faces=len(faces),
            frame_id=frame.frame_id,
            timestamp=frame.timestamp,
        )
