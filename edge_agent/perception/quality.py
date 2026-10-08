"""Block 6 stage - Frame quality (PRD FR-6): can this frame be judged at all?

A face that is too dark, washed out or blurred still gets landmarks from block 3, and blocks 7 / 8
would go on guessing from them: false alarms, or misses nobody knows about. This stage names what
is wrong with a frame, from numbers only:

- camera_blocked: no face, and the whole image is nearly black or nearly flat (lens covered).
  No face in a normal image is "driver out of view": not an issue of the image, block 8 times it.
- bad_angle:      a face, but partly out of the image or without a head pose (camera aimed badly).
- low_light:      the face is darker than `dark_face_brightness`.
- glare:          the face is brighter than `glare_face_brightness` (sun, washed out).
- blur:           the face's sharpness is below `blur_sharpness` (dirty lens, out of focus).

`QualityMonitor` times how long an issue has lasted (good frames for `clear_s` end it) and keeps
`score`, the share of the last `window_s` with a usable frame. The risk engine (block 9) turns a
lasting issue into "monitoring unavailable" with that reason (risk.unavailable). A number that was
not measured (None: old traces, synthetic sequences) is never an issue; bad_angle needs none of
them (it comes from block 6's face_reliable and head pose), so it is judged on every trace.

`measure` takes the numbers on the device from block 2's luminance (before CLAHE); the browser
measures the same ones in frontend/src/live/measure.ts. Sharpness = variance of the 4-neighbour
Laplacian of the luminance inside the landmark box. Nothing here keeps or writes an image.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any

import numpy as np

from edge_agent.config import config_from_dict
from edge_agent.perception.features import FrameFeatures
from edge_agent.perception.landmarks import FaceLandmarks
from edge_agent.perception.preprocess import PreprocessedFrame

# Issues with a face in view (timed against risk.unavailable.low_quality_s), and without a usable one
# (they name why block 8's no-face time is running). bad_angle is both (M72): the face is in view, so
# block 8's no-face time does not run, and it is timed like the face issues (TIMED_ISSUES).
FACE_ISSUES = ("low_light", "glare", "blur")
NO_FACE_ISSUES = ("camera_blocked", "bad_angle")
ISSUES = NO_FACE_ISSUES + FACE_ISSUES
TIMED_ISSUES = (*FACE_ISSUES, "bad_angle")


@dataclass(frozen=True)
class QualityConfig:
    enabled: bool = True
    dark_face_brightness: float = 25.0  # mean face luminance 0-255 below this = too dark; 0 = off
    glare_face_brightness: float = 225.0  # ... above this = washed out; 0 = off
    blur_sharpness: float = 3.0  # Laplacian variance of the face below this = blurred; 0 = off
    blocked_brightness: float = 12.0  # no face and the image darker than this = covered / black; 0 = off
    blocked_contrast: float = 6.0  # no face and luminance spread (std) below this = flat image; 0 = off
    clear_s: float = 1.0  # usable frames for this long end an issue
    window_s: float = 10.0  # score = usable share of this window
    max_gap_s: float = 0.5  # a longer gap between frames adds no time

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> QualityConfig:
        return config_from_dict(cls, d, "quality")


@dataclass(frozen=True)
class QualityState:
    issue: str | None = None  # what is wrong now (one of ISSUES), None = usable or not measured
    duration: float = 0.0  # seconds the issue has lasted
    score: float = 1.0  # share of the last window_s with a usable frame (1.0 before any data)


def laplacian_variance(luma: np.ndarray) -> float | None:
    """Variance of the 4-neighbour Laplacian (cv2.Laplacian, ksize 1) of a luminance patch."""
    if luma.shape[0] < 3 or luma.shape[1] < 3:
        return None
    y = luma.astype(np.float32)
    lap = y[:-2, 1:-1] + y[2:, 1:-1] + y[1:-1, :-2] + y[1:-1, 2:] - 4.0 * y[1:-1, 1:-1]
    return float(lap.var())


def measure(pre: PreprocessedFrame, lm: FaceLandmarks | None, stride: int) -> dict[str, float | None]:
    """The quality numbers of one frame, as FrameFeatures fields. All None without block 2's luminance.
    stride: preprocess.sample_stride, the whole-image numbers are taken on every stride-th pixel."""
    out: dict[str, float | None] = dict.fromkeys(("face_brightness", "scene_brightness", "scene_contrast", "sharpness"))
    luma = pre.luma
    if luma is None or luma.size == 0:
        return out
    out["scene_brightness"] = float(pre.brightness)
    out["scene_contrast"] = float(luma[::stride, ::stride].std())
    if lm is None:
        return out
    h, w = luma.shape[:2]
    x1, y1 = np.floor(lm.points[:, :2].min(axis=0)).astype(int)
    x2, y2 = np.ceil(lm.points[:, :2].max(axis=0)).astype(int)
    x1, y1, x2, y2 = max(x1, 0), max(y1, 0), min(x2, w), min(y2, h)
    if x2 - x1 < 3 or y2 - y1 < 3:
        return out
    face = luma[y1:y2, x1:x2]
    out["face_brightness"] = float(face.mean())
    out["sharpness"] = laplacian_variance(face)
    return out


def frame_issue(f: FrameFeatures, cfg: QualityConfig) -> str | None:
    """What makes this frame unusable, or None. The first that applies, in the order of ISSUES."""
    if not cfg.enabled:
        return None
    if not f.face_found:
        dark = (
            cfg.blocked_brightness > 0
            and f.scene_brightness is not None
            and f.scene_brightness < cfg.blocked_brightness
        )
        flat = cfg.blocked_contrast > 0 and f.scene_contrast is not None and f.scene_contrast < cfg.blocked_contrast
        return "camera_blocked" if dark or flat else None
    if not f.face_reliable or f.yaw is None or f.pitch is None:
        return "bad_angle"
    b = f.face_brightness
    if b is not None and cfg.dark_face_brightness > 0 and b < cfg.dark_face_brightness:
        return "low_light"
    if b is not None and cfg.glare_face_brightness > 0 and b > cfg.glare_face_brightness:
        return "glare"
    if f.sharpness is not None and cfg.blur_sharpness > 0 and f.sharpness < cfg.blur_sharpness:
        return "blur"
    return None


class QualityMonitor:
    """How long the current issue has lasted, and the usable share of the last window."""

    def __init__(self, config: QualityConfig | None = None) -> None:
        self.config = config or QualityConfig()
        self._issue: str | None = None
        self._since: float | None = None  # time the running issue started
        self._good_since: float | None = None  # usable frames in a row since (while an issue runs)
        self._last_t: float | None = None
        self._window: deque[tuple[float, float, bool]] = deque()  # (t, dt, usable)
        self._total = 0.0  # running sums of the window: seconds, and seconds not usable
        self._bad = 0.0
        self._bad_n = 0  # unusable samples in the window: none = a score of exactly 1

    def update(self, f: FrameFeatures) -> QualityState:
        cfg, t = self.config, f.timestamp
        issue = frame_issue(f, cfg)
        dt = 0.0 if self._last_t is None else min(max(t - self._last_t, 0.0), cfg.max_gap_s)
        self._last_t = t

        if issue is not None:
            if self._since is None:
                self._since = t
            self._issue, self._good_since = issue, None
        elif self._since is not None:  # usable again: the issue ends once that has held for clear_s
            if self._good_since is None:
                self._good_since = t
            if t - self._good_since >= cfg.clear_s:
                self._issue = self._since = self._good_since = None

        self._window.append((t, dt, issue is None))
        self._total += dt
        if issue is not None:
            self._bad += dt
            self._bad_n += 1
        while self._window and t - self._window[0][0] > cfg.window_s:
            _, old_dt, ok = self._window.popleft()
            self._total -= old_dt
            if not ok:
                self._bad -= old_dt
                self._bad_n -= 1
        if self._bad_n == 0:
            self._bad = 0.0
        total = self._total
        return QualityState(
            issue=self._issue,
            duration=0.0 if self._since is None else t - self._since,
            score=min(max(1.0 - self._bad / total, 0.0), 1.0) if total > 1e-9 else 1.0,
        )
