import threading
import time

import numpy as np
import pytest

from edge_agent.capture import CaptureConfig, FrameSource
from edge_agent.capture.frame_source import parse_source


class FakeCapture:
    """Stands in for cv2.VideoCapture; yields `n` tiny frames tagged with their index."""

    def __init__(self, n: int, fps: float = 0.0, gate: threading.Event | None = None):
        self.n = n
        self.fps = fps
        self.i = 0
        self.gate = gate

    def isOpened(self):  # noqa: N802 - mirrors OpenCV API
        return True

    def read(self):
        if self.gate is not None:
            self.gate.wait()
        if self.i >= self.n:
            return False, None
        img = np.full((4, 4, 3), self.i % 256, dtype=np.uint8)
        self.i += 1
        return True, img

    def get(self, prop):
        return self.fps

    def set(self, prop, value):
        if prop == 1:  # cv2.CAP_PROP_POS_FRAMES
            self.i = int(value)
        return True

    def release(self):
        pass


def make_source(cap, **cfg):
    config = CaptureConfig(**{"video_realtime": False, "reconnect_interval_s": 0.0, **cfg})
    return FrameSource(0, config, capture_factory=lambda _src: cap)


def test_parse_source():
    assert parse_source("0") == 0
    assert parse_source(2) == 2
    assert parse_source("clip.mp4") == "clip.mp4"


def test_keeps_only_latest_frame():
    gate = threading.Event()
    cap = FakeCapture(50, gate=gate)
    src = make_source(cap, max_consecutive_failures=1)
    with src:
        gate.set()
        src._thread.join(timeout=2.0)  # producer finishes all frames before we read
        frame = src.read(timeout=1.0)
        assert frame is not None
        assert frame.frame_id == 49
        assert src.dropped_frames == 49
        assert src.read(timeout=0.2) is None
        assert src.ended


def test_read_never_returns_same_frame_twice():
    src = make_source(FakeCapture(20), max_consecutive_failures=1)
    ids = []
    with src:
        while (f := src.read(timeout=1.0)) is not None:
            ids.append(f.frame_id)
    assert ids == sorted(set(ids))
    assert ids[-1] == 19


def test_missing_video_file_raises():
    with pytest.raises(FileNotFoundError):
        FrameSource("does_not_exist.mp4").start()


def test_stop_unblocks_reader():
    gate = threading.Event()  # producer stays blocked, no frames arrive
    src = make_source(FakeCapture(5, gate=gate))
    src.start()
    src._stop_event.set()
    assert src.read(timeout=5.0) is None
    gate.set()
    src.stop()


class FlakyCamera(FakeCapture):
    """Delivers frames, then fails every read (unplugged); a new instance works again."""

    def __init__(self, good: int):
        super().__init__(10**9)
        self.good = good

    def read(self):
        if self.i >= self.good:
            return False, None
        return super().read()


def test_lost_camera_is_reopened_and_frames_resume():
    opened = []

    def factory(_src):
        cap = FlakyCamera(good=5 if not opened else 10**9)
        opened.append(cap)
        return cap

    config = CaptureConfig(video_realtime=False, max_consecutive_failures=3, reconnect_interval_s=0.05)
    src = FrameSource(0, config, capture_factory=factory)
    with src:
        seen_lost = False
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline and not (seen_lost and src.reconnects and not src.lost):
            seen_lost |= src.lost
            src.read(timeout=0.05)
        assert seen_lost and src.reconnects == 1 and not src.lost and not src.ended
        assert src.read(timeout=1.0) is not None  # frames flow again


def test_camera_that_cannot_be_reopened_stays_lost():
    class Dead(FakeCapture):
        def isOpened(self):  # noqa: N802
            return False

    caps = iter([FlakyCamera(good=2)])
    config = CaptureConfig(video_realtime=False, max_consecutive_failures=2, reconnect_interval_s=0.02)
    src = FrameSource(0, config, capture_factory=lambda _s: next(caps, Dead(0)))
    with src:
        time.sleep(0.3)
        assert src.lost and not src.ended and src.reconnects == 0
    assert not src.lost  # stopped: nothing to report


def test_hanging_camera_counts_as_lost_after_timeout():
    gate = threading.Event()  # read() blocks forever, never fails
    src = make_source(FakeCapture(5, gate=gate), frame_timeout_s=0.1)
    with src:
        assert not src.lost
        time.sleep(0.2)
        assert src.lost
        gate.set()
