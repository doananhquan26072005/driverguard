"""Block 3 - Face landmarks (MediaPipe Face Landmarker, 478 points).

Wraps the MediaPipe Tasks API in VIDEO mode (uses tracking between frames, faster
than per-image detection). Returns `FaceLandmarks` in pixel coordinates of the
preprocessed image, or None when no face is found.

When several faces are visible (e.g. a passenger), `DriverSelector` picks the driver:
- before driver enrollment (block 6 stage, edge_agent/perception/enrollment.py): the largest
  face, since the driver usually sits closest to the camera;
- after it: the face whose shape signature (ratios of landmark distances, nearly constant
  when the head turns) and position match the enrolled driver best. A driver turning to a
  mirror shrinks in 2D and a passenger leaning in grows, so "largest" alone swaps people.
Only numbers are kept (ratios, a centre, a size), never an image.
After enrollment the best face is still nobody's when it is further than `driver_max_distance` from
where the driver was last seen (M83): with the driver hidden or out of view, a passenger alone in the
frame used to be read as the driver. No face is then reported, so the "face lost" path of blocks 8
and 9 runs. The limit is on the position alone: measured on 14 people (DROZY), the shape signature
of a stranger is as close to the driver's as the driver's own on another day, so it cannot tell.

With `blendshapes` on, the same model also outputs its 52 blendshape scores; the driver's
eyeBlinkLeft / eyeBlinkRight (0 = open, 1 = shut) are kept. They are pretrained, need no
per-driver baseline and cost no measurable time (NITYMED: AUC 0.986 for closed eyes, EAR
0.987, eye CNN 0.881), so block 5 uses them as its eye-state score. browOuterUpLeft / Right
(frontalis, FACS AU2) are kept too: drowsy drivers raise the brows to keep the eyes open
(Vural et al. 2007), a drowsiness sign of block 7.
The gaze and mouth scores of TRACE_BLENDSHAPES (eyeLook*, jawOpen, mouthClose) are kept as numbers
for the recording tools (tools/record_trace.py, tools/seq_eval.py); no block reads them yet.

Only finite numbers leave this block (M77): a face with a NaN / inf landmark is not a face
(`finite_faces`), and a blendshape score that is not finite is a missing one. MediaPipe has not
been seen to output either, but one NaN eyelid point made EAR NaN, and one NaN EAR kept block 7's
open-eye baseline NaN, so the eyes read as open, for as long as that frame stayed in its window.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from edge_agent.config import PROJECT_ROOT, config_from_dict
from edge_agent.cv import cv2
from edge_agent.perception.preprocess import PreprocessedFrame


@dataclass(frozen=True)
class LandmarkConfig:
    model_path: str = "models/face_landmarker.task"
    num_faces: int = 2
    # Driver choice once enrolled: score = shape distance / driver_shape_tol
    # + centre distance / (driver_position_tol x enrolled face size); lowest wins.
    driver_shape_tol: float = 0.08
    driver_position_tol: float = 2.0
    # Enrolled only: a face further than this from where the driver was last seen is not the driver
    # (in enrolled inter-ocular distances, the unit of driver_position_tol); 0 = off.
    driver_max_distance: float = 4.0
    min_face_detection_confidence: float = 0.5
    min_face_presence_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    blendshapes: bool = True  # also output eyeBlink scores (block 5)

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> LandmarkConfig:
        """Build the config from its section of thresholds.yaml; an unknown key is an error."""
        return config_from_dict(cls, d, "landmarks")

    def resolved_model_path(self) -> Path:
        """The model path, relative to the project root unless absolute."""
        p = Path(self.model_path)
        return p if p.is_absolute() else PROJECT_ROOT / p


# Blendshapes kept for traces only (M39): where the eyes look, how open the mouth is.
TRACE_BLENDSHAPES = (
    "eyeLookDownLeft",
    "eyeLookDownRight",
    "eyeLookUpLeft",
    "eyeLookUpRight",
    "eyeLookInLeft",
    "eyeLookInRight",
    "eyeLookOutLeft",
    "eyeLookOutRight",
    "jawOpen",
    "mouthClose",
)


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
    # MediaPipe blendshapes eyeBlinkLeft, eyeBlinkRight of the driver (0 open .. 1 shut), None when off.
    eye_blink: tuple[float, float] | None = None
    # MediaPipe blendshape browOuterUp, mean of both sides (0 rest .. 1 raised), None when off.
    brow_up: float | None = None
    # MediaPipe blendshapes of TRACE_BLENDSHAPES by name (0..1), None when off. Traces only.
    blendshapes: dict[str, float] | None = None


# Rigid points for the shape signature (no mouth / chin: they move when talking or yawning).
EYE_OUTER = (33, 263)  # right, left eye outer corners: the inter-ocular distance unit
SHAPE_PAIRS = (
    (33, 133),  # right eye width
    (362, 263),  # left eye width
    (168, 1),  # nose length: between the eyes -> nose tip
    (10, 168),  # forehead -> between the eyes
    (234, 454),  # face width at the cheeks
    (129, 358),  # nose width (alae)
    (133, 362),  # inner eye corners
)


@dataclass(frozen=True)
class DriverAnchor:
    """The enrolled driver, as numbers only: who to pick among several faces."""

    shape: tuple[float, ...]  # face_shape() of the driver
    center: tuple[float, float]  # face centre / image width (x and y)
    size: float  # inter-ocular distance / image width


def face_shape(points: np.ndarray) -> tuple[float, ...]:
    """Ratios of 3D landmark distances to the inter-ocular distance: a per-person signature."""
    iod = float(np.linalg.norm(points[EYE_OUTER[0]] - points[EYE_OUTER[1]]))
    if iod < 1e-6:
        return tuple(0.0 for _ in SHAPE_PAIRS)
    return tuple(float(np.linalg.norm(points[a] - points[b])) / iod for a, b in SHAPE_PAIRS)


def face_center_size(points: np.ndarray, width: int) -> tuple[tuple[float, float], float]:
    """Face centre (mean of the eye corners and nose tip) and inter-ocular distance, / image width."""
    w = max(width, 1)
    c = points[[EYE_OUTER[0], EYE_OUTER[1], 1], :2].mean(axis=0) / w
    iod = float(np.linalg.norm(points[EYE_OUTER[0], :2] - points[EYE_OUTER[1], :2])) / w
    return (float(c[0]), float(c[1])), iod


def shape_distance(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    """Mean relative difference of two shape signatures (0 = same)."""
    return float(np.mean([abs(x - y) / max(abs(y), 1e-6) for x, y in zip(a, b, strict=True)]))


class DriverSelector:
    """Which of the detected faces is the driver. Keeps the driver's last position between frames."""

    def __init__(self, config: LandmarkConfig | None = None) -> None:
        self.config = config or LandmarkConfig()
        self.anchor: DriverAnchor | None = None
        self._last_center: tuple[float, float] | None = None

    def set_anchor(self, anchor: DriverAnchor | None) -> None:
        """Set (or clear) the driver's position that the selection is held to."""
        self.anchor = anchor
        self._last_center = None if anchor is None else anchor.center

    def choose(self, faces: list[np.ndarray], width: int) -> int:
        """Index of the driver's face, -1 when there is none."""
        if not faces:
            return -1
        if self.anchor is None:
            return max(range(len(faces)), key=lambda i: bbox_area(faces[i]))
        k = min(range(len(faces)), key=lambda i: self._score(faces[i], width))
        limit = self.config.driver_max_distance
        if limit > 0 and self._distance(faces[k], width) > limit:
            return -1  # someone else; the driver's last position is kept for when they are back
        self._last_center = face_center_size(faces[k], width)[0]
        return k

    def _distance(self, points: np.ndarray, width: int) -> float:
        """From where the driver was last seen to this face's centre, in enrolled inter-ocular distances."""
        anchor = self.anchor
        assert anchor is not None
        center, _ = face_center_size(points, width)
        ref = self._last_center or anchor.center
        return float(np.hypot(center[0] - ref[0], center[1] - ref[1])) / max(anchor.size, 1e-6)

    def _score(self, points: np.ndarray, width: int) -> float:
        cfg, anchor = self.config, self.anchor
        assert anchor is not None
        return (
            shape_distance(face_shape(points), anchor.shape) / cfg.driver_shape_tol
            + self._distance(points, width) / cfg.driver_position_tol
        )


def bbox_area(points: np.ndarray) -> float:
    """Area of the landmarks' bounding box, in pixels squared."""
    xy = points[:, :2]
    w, h = xy.max(axis=0) - xy.min(axis=0)
    return float(w * h)


def in_frame_ratio(points: np.ndarray, width: int, height: int) -> float:
    """face_conf: share of the landmarks that lie inside the image."""
    x, y = points[:, 0], points[:, 1]
    inside = (x >= 0) & (x < width) & (y >= 0) & (y < height)
    return float(inside.mean())


def finite_faces(faces: list[np.ndarray]) -> list[int]:
    """Indices of the faces whose landmarks are all finite; the others are not faces (module doc)."""
    return [i for i, points in enumerate(faces) if np.isfinite(points).all()]


def finite_scores(*scores: float) -> tuple[float, ...] | None:
    """Blendshape scores as floats, None when one of them is NaN / inf (the same as not output)."""
    values = tuple(float(s) for s in scores)
    return values if np.isfinite(values).all() else None


class FaceLandmarkDetector:
    def __init__(self, config: LandmarkConfig | None = None, image_mode: bool = False) -> None:
        """image_mode: unrelated still images (dataset evaluation), no tracking between calls."""
        # Imported here so FaceLandmarks and the feature blocks work without MediaPipe's Python
        # package (the in-browser agent runs MediaPipe in JavaScript, edge_agent/web).
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions, vision

        self._mp = mp
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
            output_face_blendshapes=self.config.blendshapes,
        )
        self._landmarker = vision.FaceLandmarker.create_from_options(options)
        self._last_ts_ms = -1
        self.selector = DriverSelector(self.config)

    def close(self) -> None:
        """Release the MediaPipe landmarker."""
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
        """Block 3: the driver's face landmarks in pixels, or None when no usable face is found."""
        h, w = frame.image.shape[:2]
        rgb = cv2.cvtColor(frame.image, cv2.COLOR_BGR2RGB)
        mp_image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
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
        usable = finite_faces(faces)
        if not usable:
            return None
        chosen = self.selector.choose([faces[i] for i in usable], w)
        if chosen < 0:
            return None
        k = usable[chosen]  # index in MediaPipe's own order
        driver = faces[k]
        eye_blink = brow_up = traced = None
        if result.face_blendshapes and k < len(result.face_blendshapes):
            scores = {c.category_name: c.score for c in result.face_blendshapes[k]}
            traced = {
                name: float(scores[name]) for name in TRACE_BLENDSHAPES if name in scores and np.isfinite(scores[name])
            }
            if "eyeBlinkLeft" in scores and "eyeBlinkRight" in scores:
                eye_blink = finite_scores(scores["eyeBlinkLeft"], scores["eyeBlinkRight"])
            if "browOuterUpLeft" in scores and "browOuterUpRight" in scores:
                brows = finite_scores(scores["browOuterUpLeft"], scores["browOuterUpRight"])
                brow_up = None if brows is None else (brows[0] + brows[1]) / 2.0
        return FaceLandmarks(
            points=driver,
            image_width=w,
            image_height=h,
            face_conf=in_frame_ratio(driver, w, h),
            num_faces=len(usable),
            frame_id=frame.frame_id,
            timestamp=frame.timestamp,
            eye_blink=eye_blink,
            brow_up=brow_up,
            blendshapes=traced,
        )
