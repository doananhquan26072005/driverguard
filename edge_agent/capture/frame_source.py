"""Block 1 - Frame camera.

Reads frames from a camera or a video file on a background thread and keeps
only the newest frame. Consumers always get the most recent frame; frames the
consumer was too slow to take are dropped (counted in `dropped_frames`).

Camera lost (unplugged, driver crash): after `max_consecutive_failures` failed reads the
camera is released and reopened every `reconnect_interval_s` until it works again, instead
of ending the stream. `lost` is True meanwhile, and also when no frame arrived for
`frame_timeout_s` (a read that hangs instead of failing), so the main loop can tell the
HUD and the backend that the driver is not monitored. A video file still ends normally.

Camera frozen (M83): a driver that hands the same image again and again reads without an error, and
the image shows a face with open eyes that never moves. Every `frozen_stride`-th pixel of a camera
frame is compared with the previous frame's; equal for `frame_timeout_s` is a lost camera too (no
frames are handed on, it is reopened like one that fails), until an image that differs arrives. A
live sensor has noise, so two real frames are not equal; an image of one single value (covered or
saturated lens: nothing in it can change) is left to block 6's quality check instead.

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
    frozen_stride: int = 8  # compare every n-th pixel (rows and columns) with the last frame; 0 = off
    web_camera_width: int = 640  # what the page asks its camera for
    web_camera_height: int = 480
    web_max_frame_age_s: float = 1.0  # the page: a capture time older than this is not believed

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> CaptureConfig:
        """Build the config from its section of thresholds.yaml; an unknown key is an error."""
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
        self._started = False
        self._run_done = False  # the reader thread left its loop
        self._abandoned = False  # stop() gave up waiting for it: it releases the capture itself
        self._next_id = 0
        self._lost = False
        self._last_frame_t = 0.0
        self._sample: np.ndarray | None = None  # sparse pixels of the last camera frame that differed
        self._changed_t = 0.0
        self.dropped_frames = 0
        self.reconnects = 0
        self.freezes = 0  # times the camera was found handing the same image again and again
        self.reopen_attempts = 0  # tries to reopen the camera since it was lost (HUD "Lần thử N", M65)
        self.source_fps = 0.0

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> FrameSource:
        """Open the camera or video and start the reader thread; FileNotFoundError for a missing video."""
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

        self._last_frame_t = self._changed_t = time.monotonic()
        self._started = True
        self._thread = threading.Thread(target=self._run, name="FrameSource", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        """Stop the reader thread and release the capture."""
        self._stop_event.set()
        with self._cond:
            self._cond.notify_all()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        with self._cond:
            # A reader still inside read() (a camera driver that hangs) keeps the capture: releasing
            # it under a running read() is not safe in OpenCV. It lets go when read() returns.
            self._abandoned = self._started and not self._run_done and self._cap is not None
            cap = None if self._abandoned else self._cap
            if not self._abandoned:
                self._cap = None
        if cap is not None:
            cap.release()
        self._latest = self._sample = None  # drop the last image references

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
            now = time.monotonic()
            if not self._repeats(image):
                self._changed_t = now
            elif now - self._changed_t > self.config.frame_timeout_s:  # frozen: not a view of the driver
                if not self._lost:
                    self.freezes += 1
                if self.config.reconnect_interval_s <= 0 or not self._reconnect():
                    break
                continue
            self._lost = False
            self.reopen_attempts = 0
            self._last_frame_t = now

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
            self._ended = self._run_done = True
            cap = self._cap if self._abandoned else None
            if cap is not None:
                self._cap = None
            self._cond.notify_all()
        if cap is not None:  # stop() did not wait for this thread (see there)
            cap.release()

    def _repeats(self, image: np.ndarray) -> bool:
        """Camera only: this frame's sparse pixels equal the last frame's, and are not one single value."""
        stride = self.config.frozen_stride
        if not self.is_camera or stride <= 0:
            return False
        sample = image[::stride, ::stride]
        last = self._sample
        if last is not None and last.shape == sample.shape and np.array_equal(last, sample):
            return bool(sample.min() != sample.max())
        self._sample = sample.copy()  # the capture may reuse its buffer
        return False

    def _configure(self) -> None:
        if self.is_camera:
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.camera_width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.camera_height)
            self._cap.set(cv2.CAP_PROP_FPS, self.config.camera_fps)

    def _reconnect(self) -> bool:
        """Camera lost: reopen it every reconnect_interval_s. False when stopped meanwhile."""
        self._lost = True
        while not self._stop_event.wait(self.config.reconnect_interval_s):
            self.reopen_attempts += 1
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
