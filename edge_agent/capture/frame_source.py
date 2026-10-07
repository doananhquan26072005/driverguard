"""Block 1 - Frame camera.

Reads frames from a camera or a video file on a background thread and keeps
only the newest frame. Consumers always get the most recent frame; frames the
consumer was too slow to take are dropped (counted in `dropped_frames`).

Camera lost (unplugged, driver crash): after `max_consecutive_failures` failed reads the
camera is released and reopened every `reconnect_interval_s` until it works again, instead
of ending the stream. `lost` is True meanwhile, and also when no frame arrived for
`frame_timeout_s` (a read that hangs instead of failing), so the main loop can tell the
HUD and the backend that the driver is not monitored. A video file still ends normally.

Frames live in RAM only. Nothing here writes images to disk.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from edge_agent.config import config_from_dict
from edge_agent.cv import cv2


@dataclass(frozen=True)
class CaptureConfig:
    camera_width: int = 1280
    camera_height: int = 720
    camera_fps: int = 30
    video_realtime: bool = True
    video_fallback_fps: float = 30.0
    max_consecutive_failures: int = 30
    reconnect_interval_s: float = 2.0  # 0 = no reconnect: a lost camera ends the stream
    frame_timeout_s: float = 3.0

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> CaptureConfig:
        return config_from_dict(cls, d, "capture")


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
        capture_factory: Callable[[str | int], Any] | None = None,
    ) -> None:
        self.source = parse_source(source)
        self.config = config or CaptureConfig()
        self.loop = loop
        self.is_camera = isinstance(self.source, int)
        self._capture_factory = capture_factory or cv2.VideoCapture  # OpenCV unless a test hands one in

        self._cap: Any = None
        self._thread: threading.Thread | None = None
        self._cond = threading.Condition()
        self._stop_event = threading.Event()
        self._latest: Frame | None = None
        self._last_returned_id = -1
        self._ended = False
        self._next_id = 0
        self._lost = False
        self._last_frame_t = 0.0
        self.dropped_frames = 0
        self.reconnects = 0
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

        self._configure()
        fps = float(self._cap.get(cv2.CAP_PROP_FPS) or 0.0)
        self.source_fps = fps if 0 < fps < 1000 else self.config.video_fallback_fps

        self._last_frame_t = time.monotonic()
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
        """True once the source has no more frames (end of video, or camera lost without reconnect)."""
        return self._ended

    @property
    def lost(self) -> bool:
        """Camera only: reads keep failing (reconnecting) or no frame for `frame_timeout_s`."""
        if not self.is_camera or self._thread is None:
            return False
        return self._lost or time.monotonic() - self._last_frame_t > self.config.frame_timeout_s

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
                    if self.config.reconnect_interval_s <= 0 or not self._reconnect():
                        break
                    failures = 0
                    continue
                time.sleep(0.01)
                continue
            failures = 0
            self._lost = False
            self._last_frame_t = time.monotonic()

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

    def _configure(self) -> None:
        if self.is_camera:
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.camera_width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.camera_height)
            self._cap.set(cv2.CAP_PROP_FPS, self.config.camera_fps)

    def _reconnect(self) -> bool:
        """Camera lost: reopen it every reconnect_interval_s. False when stopped meanwhile."""
        self._lost = True
        while not self._stop_event.wait(self.config.reconnect_interval_s):
            if self._cap is not None:
                self._cap.release()
            try:
                self._cap = self._capture_factory(self.source)
                opened = bool(self._cap.isOpened())
            except Exception:  # noqa: BLE001 - a driver error must not kill the reader thread
                opened = False
            if opened:
                self._configure()
                self.reconnects += 1
                return True  # `lost` clears on the first good frame
        return False
