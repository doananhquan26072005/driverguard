"""Block 2 - Preprocessing.

- Resize to `target_width` (aspect ratio kept, downscale only).
- IR / grayscale input (1 channel, or 3 nearly identical channels) -> 3-channel BGR,
  because MediaPipe and YOLO expect 3 channels.
- CLAHE on luminance to stabilize contrast under low light / harsh sun.
- Report `brightness` (mean luminance before CLAHE) for the context block.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

from edge_agent.capture.frame_source import Frame
from edge_agent.config import config_from_dict


@dataclass(frozen=True)
class PreprocessConfig:
    target_width: int = 640
    ir_channel_diff_max: float = 2.0
    clahe_enabled: bool = True
    clahe_clip_limit: float = 2.0
    clahe_tile_grid: int = 8

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> PreprocessConfig:
        c = config_from_dict(cls, d, "preprocess")
        return cls(
            target_width=int(c.target_width),
            ir_channel_diff_max=float(c.ir_channel_diff_max),
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


class Preprocessor:
    def __init__(self, config: PreprocessConfig | None = None) -> None:
        self.config = config or PreprocessConfig()
        tile = self.config.clahe_tile_grid
        self._clahe = cv2.createCLAHE(clipLimit=self.config.clahe_clip_limit, tileGridSize=(tile, tile))

    def is_ir_image(self, image: np.ndarray) -> bool:
        if image.ndim == 2 or image.shape[2] == 1:
            return True
        # Subsample for speed: channel similarity is a global property.
        s = image[::4, ::4].astype(np.int16)
        diff = (np.abs(s[..., 0] - s[..., 1]).mean() + np.abs(s[..., 1] - s[..., 2]).mean()) / 2.0
        return float(diff) <= self.config.ir_channel_diff_max

    def resize(self, image: np.ndarray) -> tuple[np.ndarray, float]:
        h, w = image.shape[:2]
        if w <= self.config.target_width:
            return image, 1.0
        scale = self.config.target_width / w
        new_size = (self.config.target_width, max(1, round(h * scale)))
        return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA), scale

    def process_image(self, image: np.ndarray) -> tuple[np.ndarray, np.ndarray, float, bool, float]:
        """Core transform on a raw image. Returns (bgr, gray, brightness, is_ir, scale)."""
        if image.dtype != np.uint8:
            raise ValueError(f"Expected uint8 image, got {image.dtype}")
        if image.ndim == 3 and image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)

        is_ir = self.is_ir_image(image)
        small, scale = self.resize(image)

        if is_ir:
            gray = small if small.ndim == 2 else (small[..., 0] if small.shape[2] == 1 else small[..., 1])
            gray = np.ascontiguousarray(gray)
            brightness = float(gray.mean())
            if self.config.clahe_enabled:
                gray = self._clahe.apply(gray)
            bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        else:
            # CLAHE on L of LAB so colors are not shifted.
            lab = cv2.cvtColor(small, cv2.COLOR_BGR2LAB)
            l_ch, a_ch, b_ch = cv2.split(lab)
            brightness = float(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).mean())
            if self.config.clahe_enabled:
                l_ch = self._clahe.apply(l_ch)
                bgr = cv2.cvtColor(cv2.merge((l_ch, a_ch, b_ch)), cv2.COLOR_LAB2BGR)
            else:
                bgr = small
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

        return bgr, gray, brightness, is_ir, scale

    def __call__(self, frame: Frame) -> PreprocessedFrame:
        bgr, gray, brightness, is_ir, scale = self.process_image(frame.image)
        return PreprocessedFrame(
            image=bgr,
            gray=gray,
            brightness=brightness,
            is_ir=is_ir,
            scale=scale,
            frame_id=frame.frame_id,
            timestamp=frame.timestamp,
        )
