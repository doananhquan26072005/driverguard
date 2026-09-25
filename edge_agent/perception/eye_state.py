"""Block 5 - Eye-state CNN (pretrained, called only when EAR is not reliable).

Model: Intel Open Model Zoo `open-closed-eye-0001` (Apache-2.0), trained on the MRL Eye
dataset (mostly infrared eye crops), 46 KB ONNX. Input: BGR 32x32, (x - 127) / 255.
Output: softmax over 2 classes where index 0 = CLOSED and index 1 = OPEN. The model README
says the opposite, but Intel's own gaze_estimation_demo treats `out[0] < out[1]` as "eye
open" (and our sanity check agrees), so p_closed = out[0].

Crop, as in that demo: a square of `crop_scale` x the distance between the two eye corners,
centred on their midpoint and rotated so the eye line is horizontal.

EAR stays the primary signal (block 6). The CNN only runs when EAR is likely wrong:
- infrared / grayscale image or a dark cabin (night),
- the two eyes' EAR disagree a lot (glare on glasses or one eye occluded).
The crops live in RAM only.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import cv2
import numpy as np

from edge_agent.config import PROJECT_ROOT, config_from_dict
from edge_agent.perception.features import FrameFeatures
from edge_agent.perception.landmarks import FaceLandmarks
from edge_agent.perception.preprocess import PreprocessedFrame

# MediaPipe eye corners (outer, inner) per eye.
RIGHT_EYE_CORNERS = (33, 133)
LEFT_EYE_CORNERS = (263, 362)


@dataclass(frozen=True)
class EyeStateConfig:
    enabled: bool = True
    model_path: str = "models/open_closed_eye.onnx"
    input_size: int = 32
    crop_scale: float = 1.8
    mean: float = 127.0
    scale: float = 255.0
    closed_index: int = 0
    # When to call the CNN (EAR not reliable):
    run_on_ir: bool = True
    low_light_brightness: float = 60.0  # mean luminance (0-255) below this = night
    ear_asymmetry_max: float = 0.35  # |L - R| / mean EAR above this = one eye unreliable
    always_run: bool = False  # debug / evaluation

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> EyeStateConfig:
        return config_from_dict(cls, d, "eye_state")

    def resolved_model_path(self) -> Path:
        p = Path(self.model_path)
        return p if p.is_absolute() else PROJECT_ROOT / p


@dataclass(frozen=True)
class EyeState:
    p_closed_left: float
    p_closed_right: float
    reason: str  # why the CNN was called: ir, low_light, ear_asymmetry, always

    @property
    def p_closed(self) -> float:
        return (self.p_closed_left + self.p_closed_right) / 2.0


class EyeClassifier(Protocol):
    def __call__(self, crops: np.ndarray) -> np.ndarray:
        """(N, 32, 32, 3) BGR uint8 -> (N,) probability that the eye is closed."""


def eye_crop(image: np.ndarray, p1: np.ndarray, p2: np.ndarray, scale: float, size: int) -> np.ndarray:
    """Square crop around the eye, rotated so the corner line is horizontal, resized to size x size."""
    p1, p2 = np.asarray(p1, dtype=np.float64), np.asarray(p2, dtype=np.float64)
    if p1[0] > p2[0]:
        p1, p2 = p2, p1  # left-to-right in the image, so the crop is never upside down
    center = (p1 + p2) / 2.0
    side = max(float(np.linalg.norm(p2 - p1)) * scale, 1.0)
    angle = float(np.degrees(np.arctan2(p2[1] - p1[1], p2[0] - p1[0])))
    m = cv2.getRotationMatrix2D((float(center[0]), float(center[1])), angle, size / side)
    m[:, 2] += (size / 2.0) - center  # move the eye centre to the middle of the output
    return cv2.warpAffine(image, m, (size, size), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REPLICATE)


def trigger_reason(pre: PreprocessedFrame, f: FrameFeatures, cfg: EyeStateConfig) -> str | None:
    """Why EAR should not be trusted on this frame (the CNN is then called), or None."""
    if cfg.always_run:
        return "always"
    if cfg.run_on_ir and pre.is_ir:
        return "ir"
    if pre.brightness < cfg.low_light_brightness:
        return "low_light"
    if f.ear_left is not None and f.ear_right is not None:
        mean = (f.ear_left + f.ear_right) / 2.0
        if mean > 1e-6 and abs(f.ear_left - f.ear_right) / mean > cfg.ear_asymmetry_max:
            return "ear_asymmetry"
    return None


class OnnxEyeClassifier:
    def __init__(self, config: EyeStateConfig) -> None:
        import onnxruntime as ort

        model = config.resolved_model_path()
        if not model.exists():
            raise FileNotFoundError(f"Model not found: {model}. Run: python tools/download_models.py")
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 1  # tiny model: one thread, leave CPU for MediaPipe
        self._session = ort.InferenceSession(str(model), opts, providers=["CPUExecutionProvider"])
        self._input = self._session.get_inputs()[0].name
        self.config = config

    def __call__(self, crops: np.ndarray) -> np.ndarray:
        x = (crops.astype(np.float32) - self.config.mean) / self.config.scale
        x = np.ascontiguousarray(x.transpose(0, 3, 1, 2))  # NHWC -> NCHW, BGR kept
        probs = np.stack([self._session.run(None, {self._input: x[i : i + 1]})[0].ravel() for i in range(len(x))])
        return probs[:, self.config.closed_index]


class EyeStateEstimator:
    """Runs the CNN when needed and adds p_closed to the frame's features."""

    def __init__(self, config: EyeStateConfig | None = None, classifier: EyeClassifier | None = None) -> None:
        self.config = config or EyeStateConfig()
        self._classifier = classifier if classifier is not None else OnnxEyeClassifier(self.config)
        self.runs = 0

    def estimate(self, pre: PreprocessedFrame, lm: FaceLandmarks | None, f: FrameFeatures) -> EyeState | None:
        if not self.config.enabled or lm is None:
            return None
        reason = trigger_reason(pre, f, self.config)
        if reason is None:
            return None
        cfg = self.config
        crops = np.stack(
            [
                eye_crop(pre.image, lm.points[a, :2], lm.points[b, :2], cfg.crop_scale, cfg.input_size)
                for a, b in (LEFT_EYE_CORNERS, RIGHT_EYE_CORNERS)
            ]
        )
        p_left, p_right = (float(p) for p in self._classifier(crops))
        self.runs += 1
        return EyeState(p_closed_left=p_left, p_closed_right=p_right, reason=reason)

    def __call__(self, pre: PreprocessedFrame, lm: FaceLandmarks | None, f: FrameFeatures) -> FrameFeatures:
        state = self.estimate(pre, lm, f)
        if state is None:
            return f
        return dataclasses.replace(f, p_closed=state.p_closed, eye_cnn_reason=state.reason)


def make_estimator(config: EyeStateConfig) -> EyeStateEstimator | None:
    """Estimator, or None (EAR only) when disabled or the model file is missing."""
    if not config.enabled:
        return None
    try:
        return EyeStateEstimator(config)
    except FileNotFoundError as e:
        print(f"[eye-state] disabled, EAR only: {e}")
        return None
