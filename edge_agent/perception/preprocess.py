"""Block 2 - Preprocessing.

- Resize to `target_width` (aspect ratio kept, downscale only).
- IR / grayscale input (1 channel, or 3 nearly identical channels) -> 3-channel BGR,
  because MediaPipe and YOLO expect 3 channels.
- CLAHE on luminance (Y of YCrCb) to stabilize contrast under low light / harsh sun.
- Report `brightness` (mean luminance before CLAHE) for the context block.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from edge_agent.capture.frame_source import Frame
from edge_agent.config import config_from_dict
from edge_agent.cv import cv2


@dataclass(frozen=True)
class PreprocessConfig:
    target_width: int = 640
    ir_channel_diff_max: float = 2.0
    ir_channel_rel_max: float = 0.03  # ... and below this share of the frame's brightness (0 = not asked)
    ir_switch_s: float = 2.0  # the camera's kind changes only after frames said so for this long
    sample_stride: int = 4  # the whole-image numbers are taken on every n-th pixel (also block 6's)
    clahe_enabled: bool = True
    clahe_clip_limit: float = 2.0
    clahe_tile_grid: int = 8

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> PreprocessConfig:
        c = config_from_dict(cls, d, "preprocess")
        return cls(
            target_width=int(c.target_width),
            ir_channel_diff_max=float(c.ir_channel_diff_max),
            ir_channel_rel_max=float(c.ir_channel_rel_max),
            ir_switch_s=float(c.ir_switch_s),
            sample_stride=max(int(c.sample_stride), 1),
            clahe_enabled=bool(c.clahe_enabled),
            clahe_clip_limit=float(c.clahe_clip_limit),
            clahe_tile_grid=int(c.clahe_tile_grid),
        )


@dataclass(frozen=True)
class PreprocessedFrame:
    image: np.ndarray  # BGR uint8, 3 channels, resized + CLAHE
    gray: np.ndarray  # single-channel version of `image`
    brightness: float  # mean luminance of the input before CLAHE, 0-255
    is_ir: bool  # input was grayscale / IR
    scale: float  # output_size / input_size, to map coordinates back
    frame_id: int
    timestamp: float
    # Luminance before CLAHE, same size as `image` (CLAHE lifts dark regions, so it cannot
    # tell a lit face in a dark cabin from a dark face). Block 5 reads the face's brightness here.
    luma: np.ndarray | None = None


def looks_infrared(cfg: PreprocessConfig, channel_diff: float, brightness: float | None) -> bool:
    """One frame's verdict from its two numbers: the mean absolute difference between neighbouring
    channels, and the mean luminance (None = not measured: the relative test is not asked).

    A grayscale / infrared camera hands over three equal channels: the difference is about 0 at any
    light. A colour camera's difference shrinks with the light (6-20 % of the brightness on the webcam
    of the self-recorded sessions), so in a dark cabin it fell under the absolute limit and the colour
    image passed for infrared (audit 08/10, A1 H1: 98-100 % of the frames at a face brightness of
    10-11). The difference must therefore also be small against the brightness (M98)."""
    if channel_diff > cfg.ir_channel_diff_max:
        return False
    if cfg.ir_channel_rel_max <= 0 or brightness is None:
        return True
    return channel_diff <= cfg.ir_channel_rel_max * brightness


class IrLatch:
    """The kind of camera (infrared / grayscale or colour) over time. A camera does not change its kind
    from one frame to the next, so the first frame's verdict stands until the frames have said otherwise
    for `ir_switch_s` without a break (a camera that switches its IR filter at dusk). Time that does not
    move forward (another video, a single image) starts it again."""

    def __init__(self, config: PreprocessConfig) -> None:
        self.config = config
        self._is_ir: bool | None = None
        self._last_t: float | None = None
        self._other_since: float | None = None

    def update(self, t: float, verdict: bool) -> bool:
        if self._is_ir is None or self._last_t is None or t <= self._last_t:
            self._is_ir, self._other_since = verdict, None
        elif verdict == self._is_ir:
            self._other_since = None
        else:
            if self._other_since is None:
                self._other_since = t
            if t - self._other_since >= self.config.ir_switch_s:
                self._is_ir, self._other_since = verdict, None
        self._last_t = t
        return self._is_ir


class Preprocessor:
    def __init__(self, config: PreprocessConfig | None = None) -> None:
        self.config = config or PreprocessConfig()
        tile = self.config.clahe_tile_grid
        self._clahe = cv2.createCLAHE(clipLimit=self.config.clahe_clip_limit, tileGridSize=(tile, tile))
        self._kind = IrLatch(self.config)

    def is_ir_image(self, image: np.ndarray) -> bool:
        """This one image alone (see `looks_infrared`); `__call__` holds the camera's kind over time."""
        if image.ndim == 2 or image.shape[2] == 1:
            return True
        # Subsample for speed: channel similarity is a global property.
        step = self.config.sample_stride
        s = image[::step, ::step].astype(np.int16)
        diff = (np.abs(s[..., 0] - s[..., 1]).mean() + np.abs(s[..., 1] - s[..., 2]).mean()) / 2.0
        # BT.601 luma, as the page's scene brightness (frontend/src/live/measure.ts lumaSpread, same stride)
        brightness = float(cv2.cvtColor(np.ascontiguousarray(image[::step, ::step]), cv2.COLOR_BGR2GRAY).mean())
        return looks_infrared(self.config, float(diff), brightness)

    def resize(self, image: np.ndarray) -> tuple[np.ndarray, float]:
        h, w = image.shape[:2]
        if w <= self.config.target_width:
            return image, 1.0
        scale = self.config.target_width / w
        new_size = (self.config.target_width, max(1, round(h * scale)))
        return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA), scale

    def process_image(
        self, image: np.ndarray, is_ir: bool | None = None
    ) -> tuple[np.ndarray, np.ndarray, float, bool, float, np.ndarray]:
        """Core transform on a raw image. Returns (bgr, gray, brightness, is_ir, scale, luma before CLAHE).
        is_ir: the camera's kind when the caller knows it (`__call__`); None = judged on this image alone."""
        if image.dtype != np.uint8:
            raise ValueError(f"Expected uint8 image, got {image.dtype}")
        if image.ndim == 3 and image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)

        one_channel = image.ndim == 2 or image.shape[2] == 1
        is_ir = one_channel or (self.is_ir_image(image) if is_ir is None else is_ir)
        small, scale = self.resize(image)

        if is_ir:
            gray = small if small.ndim == 2 else (small[..., 0] if small.shape[2] == 1 else small[..., 1])
            gray = np.ascontiguousarray(gray)
            luma = gray
            brightness = float(gray.mean())
            if self.config.clahe_enabled:
                gray = self._clahe.apply(gray)
            bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        else:
            # CLAHE on Y of YCrCb so colors are not shifted. Y uses the same weights as
            # BGR2GRAY, so brightness needs no extra conversion (LAB took two more).
            ycc = cv2.cvtColor(small, cv2.COLOR_BGR2YCrCb)
            y = np.ascontiguousarray(ycc[..., 0])
            luma = y
            brightness = float(cv2.mean(y)[0])
            if self.config.clahe_enabled:
                ycc[..., 0] = self._clahe.apply(y)
                bgr = cv2.cvtColor(ycc, cv2.COLOR_YCrCb2BGR)
            else:
                bgr = small
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)  # of the output (colour clipping shifts Y a bit)

        return bgr, gray, brightness, is_ir, scale, luma

    def __call__(self, frame: Frame) -> PreprocessedFrame:
        kind = self._kind.update(frame.timestamp, self.is_ir_image(frame.image))
        bgr, gray, brightness, is_ir, scale, luma = self.process_image(frame.image, is_ir=kind)
        return PreprocessedFrame(
            image=bgr,
            gray=gray,
            brightness=brightness,
            is_ir=is_ir,
            scale=scale,
            frame_id=frame.frame_id,
            timestamp=frame.timestamp,
            luma=luma,
        )
