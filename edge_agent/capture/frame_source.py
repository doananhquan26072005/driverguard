"""Block 1 - Frame camera.

Reads frames from a camera or a video file on a background thread and keeps
only the newest frame. Consumers always get the most recent frame; frames the
consumer was too slow to take are dropped (counted in `dropped_frames`).

Frames live in RAM only. Nothing here writes images to disk.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np


@dataclass(frozen=True)
class CaptureConfig:
    camera_width: int = 1280
    camera_height: int = 720
    camera_fps: int = 30
    video_realtime: bool = True
    video_fallback_fps: float = 30.0
    max_consecutive_failures: int = 30

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> CaptureConfig:
        d = d or {}
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d})


@dataclass(frozen=True)
class Frame:
    image: np.ndarray  # raw frame as delivered by OpenCV (BGR or single channel)
    frame_id: int  # increasing index of frames read from the source
    timestamp: float  # time.monotonic() when the frame was grabbed


def parse_source(source: str | int) -> str | int:
    """'0' -> camera index 0, anything else -> video path."""
    if isinstance(source, int):
        return source
    return int(source) if source.strip().isdigit() else source


class FrameSource:
    """Threaded reader that keeps only the latest frame.

    Usage:
        with FrameSource("video.mp4", cfg) as src:
            while (frame := src.read()) is not None:
                ...
    """

    def __init__(
        self,
        source: str | int,
        config: CaptureConfig | None = None,
        loop: bool = False,
        capture_factory: Callable[[str | int], Any] = cv2.VideoCapture,
    ) -> None:
        self.source = parse_source(source)
        self.config = config or CaptureConfig()
        self.loop = loop
        self.is_camera = isinstance(self.source, int)
        self._capture_factory = capture_factory

        self._cap: Any = None
        self._thread: threading.Thread | None = None
        self._cond = threading.Condition()
        self._stop_event = threading.Event()
        self._latest: Frame | None = None
        self._last_returned_id = -1
        self._ended = False
        self._next_id = 0
        self.dropped_frames = 0
        self.source_fps = 0.0

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> FrameSource:
        if self._thread is not None:
            return self
        if not self.is_camera and not Path(str(self.source)).exists():
            raise FileNotFoundError(f"Video not found: {self.source}")

        self._cap = self._capture_factory(self.source)
        if not self._cap.isOpened():
            raise RuntimeError(f"Cannot open source: {self.source}")

        if self.is_camera:
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.camera_width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.camera_height)
            self._cap.set(cv2.CAP_PROP_FPS, self.config.camera_fps)

        fps = float(self._cap.get(cv2.CAP_PROP_FPS) or 0.0)
        self.source_fps = fps if 0 < fps < 1000 else self.config.video_fallback_fps

        self._thread = threading.Thread(target=self._run, name="FrameSource", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop_event.set()
        with self._cond:
            self._cond.notify_all()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._latest = None  # drop the last image reference

    def __enter__(self) -> FrameSource:
        return self.start()

    def __exit__(self, *exc: object) -> None:
        self.stop()

    @property
    def ended(self) -> bool:
        """True once the source has no more frames (end of video / camera lost)."""
        return self._ended

    # ------------------------------------------------------------------ consumer
    def read(self, timeout: float = 1.0) -> Frame | None:
        """Block until a frame newer than the last returned one is available.

        Returns None on end of stream, on stop(), or when `timeout` expires.
        """
        deadline = time.monotonic() + timeout
        with self._cond:
            while True:
                latest = self._latest
                if latest is not None and latest.frame_id > self._last_returned_id:
                    self._last_returned_id = latest.frame_id
                    return latest
                if self._ended or self._stop_event.is_set():
                    return None
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self._cond.wait(remaining)

    # ------------------------------------------------------------------ producer
    def _run(self) -> None:
        pace = not self.is_camera and self.config.video_realtime
        period = 1.0 / self.source_fps
        next_due = time.monotonic()
        failures = 0

        while not self._stop_event.is_set():
            ok, image = self._cap.read()
            if not ok or image is None:
                if not self.is_camera:
                    if self.loop and self._next_id > 0:
                        self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    break
                failures += 1
                if failures >= self.config.max_consecutive_failures:
                    break
                time.sleep(0.01)
                continue
            failures = 0

            if pace:
                # Simulate a live camera: release frames at the video's native FPS.
                next_due += period
                delay = next_due - time.monotonic()
                if delay > 0:
                    if self._stop_event.wait(delay):
                        break
                else:
                    next_due = time.monotonic()  # fell behind, don't burst to catch up

            frame = Frame(image=image, frame_id=self._next_id, timestamp=time.monotonic())
            self._next_id += 1
            with self._cond:
                if self._latest is not None and self._latest.frame_id > self._last_returned_id:
                    self.dropped_frames += 1
                self._latest = frame
                self._cond.notify_all()

        with self._cond:
            self._ended = True
            self._cond.notify_all()
