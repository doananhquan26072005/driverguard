"""Block 5 - Eye-state score (pretrained, used only when EAR is not reliable).

Two sources, `source` in thresholds.yaml:
- "blendshape": MediaPipe's eyeBlinkLeft / eyeBlinkRight (block 3 already outputs them, no
  extra model, no measurable time). On NITYMED night driving it separates closed eyes as
  well as EAR (AUC 0.986 vs 0.987), the CNN below only 0.881.
- "cnn": the open-closed-eye-0001 CNN on eye crops, described below.
The chosen score goes to FrameFeatures.p_closed with its name in p_closed_source: the two are not on
the same scale (shut eyes: CNN ~0.9+, eyeBlink ~0.55-0.7), so block 7 has thresholds for each.

CNN model: Intel Open Model Zoo `open-closed-eye-0001` (Apache-2.0), trained on the MRL Eye
dataset (mostly infrared eye crops), 46 KB ONNX. Input: BGR 32x32, (x - 127) / 255.
Output: softmax over 2 classes where index 0 = CLOSED and index 1 = OPEN. The model README
says the opposite, but Intel's own gaze_estimation_demo treats `out[0] < out[1]` as "eye
open" (and our sanity check agrees), so p_closed = out[0].

Crop, as in that demo: a square of `crop_scale` x the distance between the two eye corners,
centred on their midpoint and rotated so the eye line is horizontal.

EAR stays the primary signal (block 6). The score is only used when EAR is likely wrong:
- infrared / grayscale image, or a dark face. Brightness is the mean luminance of the face
  (landmark box, before CLAHE), not of the whole frame: at night the cabin is dark but a lit
  face still gives a good EAR (NITYMED: whole frame 49-59, below the threshold on 97 % of frames,
  which handed eye state to the weaker CNN and cut microsleep detection 3x).
- the two eyes' EAR disagree a lot (glare on glasses or one eye occluded): |L - R| / max(L, R)
  above `ear_asymmetry_max` while one eye still looks open (max >= `ear_asymmetry_min_open`).
  Dividing by the mean EAR, as before, blew up whenever both eyes closed (0.05 vs 0.08 ->
  0.46), so the CNN was called exactly on closures (59 % of NITYMED microsleep frames, 8 %
  of alert frames) and, seeing them as open, hid them.
Once called for the whole scene (infrared, dark face), the score stays on for `hold_s` after the
trigger clears: at dusk the brightness wobbles around `low_light_brightness`, and switching
EAR <-> CNN frame by frame lets the unreliable EAR frames fake closures (PERCLOS, blinks) in
between the CNN ones. An EAR asymmetry is not held: it comes from glasses / glare, where the
CNN is weak (YawDD: holding it there raised false microsleeps 6 -> 18, all in glasses clips).
The crops live in RAM only.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from edge_agent.config import PROJECT_ROOT, ConfigError, config_from_dict
from edge_agent.cv import cv2
from edge_agent.perception.features import FrameFeatures
from edge_agent.perception.landmarks import FaceLandmarks
from edge_agent.perception.preprocess import PreprocessedFrame

# MediaPipe eye corners (outer, inner) per eye.
RIGHT_EYE_CORNERS = (33, 133)
LEFT_EYE_CORNERS = (263, 362)
# Triggers about the whole scene, held for hold_s (see module doc); ear_asymmetry is not.
HELD_REASONS = ("ir", "low_light")
SOURCES = ("blendshape", "cnn")


@dataclass(frozen=True)
class EyeStateConfig:
    enabled: bool = True
    source: str = "cnn"  # "blendshape" (MediaPipe eyeBlink, block 3) or "cnn" (model_path)
    web_source: str = "blendshape"  # the page's source (edge_agent/web/bridge.py): it has no ONNX eye model
    web_blink_missing: float = 0.05  # the page: eyeBlink of a face MediaPipe gave none for (open)
    model_path: str = "models/open_closed_eye.onnx"
    input_size: int = 32
    crop_scale: float = 1.8
    mean: float = 127.0
    scale: float = 255.0
    closed_index: int = 0
    # When to call the CNN (EAR not reliable):
    run_on_ir: bool = True
    low_light_brightness: float = 0.0  # mean face luminance (0-255, before CLAHE) below this = too dark; 0 = off
    ear_asymmetry_max: float = 0.35  # |L - R| / max(L, R) above this = one eye unreliable
    ear_asymmetry_min_open: float = 0.18  # ... only while one eye still looks open (both closed agree)
    hold_s: float = 2.0  # keep the CNN on this long after an ir / low_light trigger clears (no flicker)
    always_run: bool = False  # debug / evaluation

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> EyeStateConfig:
        """Build the config from the `eye_state` section; ConfigError for an unknown source."""
        cfg = config_from_dict(cls, d, "eye_state")
        for key in ("source", "web_source"):
            if getattr(cfg, key) not in SOURCES:
                raise ConfigError(f"thresholds: eye_state.{key} {getattr(cfg, key)!r} must be one of {SOURCES}")
        return cfg

    def resolved_model_path(self) -> Path:
        """The model path, relative to the project root unless absolute."""
        p = Path(self.model_path)
        return p if p.is_absolute() else PROJECT_ROOT / p


@dataclass(frozen=True)
class EyeState:
    p_closed_left: float
    p_closed_right: float
    reason: str  # why the score was used: ir, low_light, ear_asymmetry, always
    source: str = "cnn"  # which score it is: cnn | blendshape

    @property
    def p_closed(self) -> float:
        """Probability that the eyes are closed: the mean of both eyes."""
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


def face_brightness(pre: PreprocessedFrame, lm: FaceLandmarks | None) -> float:
    """Mean luminance (before CLAHE) inside the landmark box; the whole frame's without a face."""
    if lm is None or pre.luma is None:
        return pre.brightness
    h, w = pre.luma.shape[:2]
    x1, y1 = np.floor(lm.points[:, :2].min(axis=0)).astype(int)
    x2, y2 = np.ceil(lm.points[:, :2].max(axis=0)).astype(int)
    x1, y1, x2, y2 = max(x1, 0), max(y1, 0), min(x2, w), min(y2, h)
    if x2 - x1 < 2 or y2 - y1 < 2:
        return pre.brightness
    return float(cv2.mean(pre.luma[y1:y2, x1:x2])[0])


def trigger_from_values(
    cfg: EyeStateConfig, is_ir: bool, brightness: float, ear_left: float | None, ear_right: float | None
) -> str | None:
    """Why EAR should not be trusted, from plain numbers (also used to replay recorded runs)."""
    if cfg.always_run:
        return "always"
    if cfg.run_on_ir and is_ir:
        return "ir"
    if brightness < cfg.low_light_brightness:
        return "low_light"
    if ear_left is not None and ear_right is not None:
        hi, lo = max(ear_left, ear_right), min(ear_left, ear_right)
        if hi >= cfg.ear_asymmetry_min_open and (hi - lo) / hi > cfg.ear_asymmetry_max:
            return "ear_asymmetry"
    return None


def trigger_reason(
    pre: PreprocessedFrame, f: FrameFeatures, cfg: EyeStateConfig, lm: FaceLandmarks | None = None
) -> str | None:
    """Why EAR should not be trusted on this frame (the eye-state score is then used), or None."""
    return trigger_from_values(cfg, pre.is_ir, face_brightness(pre, lm), f.ear_left, f.ear_right)


class OnnxEyeClassifier:
    def __init__(self, config: EyeStateConfig) -> None:
        from edge_agent.perception.onnx import load_ort

        ort = load_ort()

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
    """Adds p_closed (blendshape or CNN) to the frame's features when EAR is not reliable."""

    def __init__(self, config: EyeStateConfig | None = None, classifier: EyeClassifier | None = None) -> None:
        self.config = config or EyeStateConfig()
        if classifier is None and self.config.source == "cnn":
            classifier = OnnxEyeClassifier(self.config)
        self._classifier = classifier
        self.runs = 0
        self._hold_until = float("-inf")
        self._hold_reason = ""

    def decide(self, t: float, reason: str | None) -> str | None:
        """The trigger of this frame, with the hold for scene-wide triggers (pure: replayable)."""
        if reason in HELD_REASONS:
            self._hold_until, self._hold_reason = t + self.config.hold_s, reason
        elif reason is None:
            if t > self._hold_until:
                return None
            reason = self._hold_reason  # the face was too dark a moment ago: keep the same source
        return reason

    def estimate(self, pre: PreprocessedFrame, lm: FaceLandmarks | None, f: FrameFeatures) -> EyeState | None:
        """Block 5: p_closed of both eyes from the blendshapes or the CNN, only when a trigger says
        EAR cannot be trusted on this frame. None when it did not run."""
        if not self.config.enabled or lm is None:
            return None
        cfg = self.config
        reason = self.decide(pre.timestamp, trigger_reason(pre, f, cfg, lm))
        if reason is None:
            return None
        if cfg.source == "blendshape" or self._classifier is None:
            if lm.eye_blink is None:  # blendshapes off in block 3: EAR decides
                return None
            p_left, p_right = lm.eye_blink
            source = "blendshape"
        else:
            crops = np.stack(
                [
                    eye_crop(pre.image, lm.points[a, :2], lm.points[b, :2], cfg.crop_scale, cfg.input_size)
                    for a, b in (LEFT_EYE_CORNERS, RIGHT_EYE_CORNERS)
                ]
            )
            p_left, p_right = (float(p) for p in self._classifier(crops))
            source = "cnn"
        self.runs += 1
        return EyeState(p_closed_left=p_left, p_closed_right=p_right, reason=reason, source=source)

    def __call__(self, pre: PreprocessedFrame, lm: FaceLandmarks | None, f: FrameFeatures) -> FrameFeatures:
        state = self.estimate(pre, lm, f)
        if state is None:
            return f
        return dataclasses.replace(
            f, p_closed=state.p_closed, eye_cnn_reason=state.reason, p_closed_source=state.source
        )


def make_estimator(config: EyeStateConfig) -> EyeStateEstimator | None:
    """Estimator, or None (EAR only) when disabled or the CNN model file is missing."""
    if not config.enabled:
        return None
    try:
        return EyeStateEstimator(config)
    except FileNotFoundError as e:
        print(f"[eye-state] disabled, EAR only: {e}")
        return None
