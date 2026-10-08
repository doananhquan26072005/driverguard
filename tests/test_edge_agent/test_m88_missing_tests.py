"""M88: tests the 08/10 audit found missing in blocks 1-12 (A1 L4, A3 L5). Tests only, no code changed.

What M71-M86 already cover is not repeated here (frame gaps, reminders, context resets, non-finite
numbers, a frozen camera, a YOLO run that raises). What was still open:

- Blocks 1 and 4 run on threads and were only tested with real sleeps and wide ranges ("6 to 12 runs
  in a second"). Here their loops run in the test's own thread on a clock the test moves, so the
  schedule is asserted exactly: when YOLO runs and on which frame, when a lost camera is asked for again.
- Block 2: `resize` keeps the aspect ratio; a dark colour image is not an infrared one (audit A1 H1,
  still open: stated as what is wanted, xfail strict).
- The page and the device measure an image with the same arithmetic written twice (Python, measure.ts):
  one fixture, checked from both sides (tools/measure_fixture.py, frontend/src/live/measureCross.test.ts).
- Block 12 with the thresholds of config/thresholds.yaml (L3 has no cooldown there; the unit tests of
  test_decision.py use 10 s), and with frames that do not come evenly.
- The context factors (night, long drive) on the fixture traces: the trace regression replays at noon
  with no driving behind it, so nothing pinned what the factors do on real recordings.

Fake sequences and the fixture traces (numbers only), no video, no model.
"""

from __future__ import annotations

import json
import math
import threading

import numpy as np
import pytest

from edge_agent.capture import CaptureConfig, FrameSource
from edge_agent.capture import frame_source as frame_source_module
from edge_agent.config import load_thresholds
from edge_agent.decision.alert_manager import AlertConfig, AlertManager
from edge_agent.decision.risk_engine import RiskAssessment, RuleHit
from edge_agent.perception import phone_detector as phone_detector_module
from edge_agent.perception.phone_detector import AsyncPhoneDetector, PhoneDetectorConfig
from edge_agent.perception.preprocess import PreprocessConfig, PreprocessedFrame, Preprocessor
from tools import measure_fixture
from tools import regression_traces as rt
from tools.seq_eval import replay, set_threshold

TH = load_thresholds()


# ---------------------------------------------------------------- a clock the test moves


class Clock:
    """Stands in for the `time` module of the module under test: time passes only when something
    waits, sleeps or works, by exactly that long."""

    def __init__(self) -> None:
        self.t = 0.0

    def monotonic(self) -> float:
        return self.t

    def perf_counter(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.t += seconds


class Until:
    """Stands in for a thread's stop event: waiting on it moves the clock, and it is set from `end` on."""

    def __init__(self, clock: Clock, end: float) -> None:
        self.clock, self.end = clock, end

    def is_set(self) -> bool:
        return self.clock.t >= self.end

    def wait(self, timeout: float | None = None) -> bool:
        self.clock.t += timeout or 0.0
        return self.is_set()

    def set(self) -> None:
        self.end = -math.inf


# ---------------------------------------------------------------- block 4: when YOLO runs, and on what

LOOP_FPS = 30.0


class LoopFeeds:
    """Stands in for the detector's condition variable. The main loop offers a frame every 1 / LOOP_FPS,
    so whenever the detector's thread looks, the newest frame is the one pending (camera False: the
    loop has no frames to offer, e.g. a lost camera)."""

    def __init__(self, detector: AsyncPhoneDetector, clock: Clock, camera: bool = True) -> None:
        self.detector, self.clock, self.camera, self.waits = detector, clock, camera, 0

    def __enter__(self) -> LoopFeeds:
        if self.camera:
            i = int(self.clock.t * LOOP_FPS + 1e-9)
            img = np.zeros((8, 8, 3), dtype=np.uint8)
            self.detector._pending = PreprocessedFrame(img, img[..., 0], 0.0, False, 1.0, i, i / LOOP_FPS)
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def wait(self, timeout: float | None = None) -> None:
        self.waits += 1
        self.clock.t += timeout or 0.0

    def notify(self) -> None:
        pass

    notify_all = notify


def run_detector(monkeypatch, cfg, infer_s, seconds, camera=True):
    """The detector's own loop, in this thread, for `seconds` of the fake clock. infer_s(n): how long
    the n-th run (1-based) takes, or an exception to raise. Returns (detector, runs, feed, calls): runs
    as (start time, frame id, frame time), calls the start of every call of the model, failed or not."""
    clock = Clock()
    monkeypatch.setattr(phone_detector_module, "time", clock)
    calls = []

    def model(image):
        calls.append(clock.t)
        took = infer_s(len(calls))
        if isinstance(took, Exception):
            raise took
        clock.t += took
        return ()

    detector = AsyncPhoneDetector(cfg, model=model)
    detector._stop = Until(clock, seconds)
    detector._cond = feed = LoopFeeds(detector, clock, camera)
    runs = []
    infer = detector._infer

    def watched(frame):
        runs.append((clock.t, frame.frame_id, frame.timestamp))
        infer(frame)

    detector._infer = watched
    detector._run()
    return detector, runs, feed, calls


def gaps(times):
    return [b - a for a, b in zip(times, times[1:], strict=False)]


def test_yolo_runs_every_period_on_the_newest_frame_not_on_every_frame(monkeypatch):
    cfg = PhoneDetectorConfig(target_fps=10.0, max_result_age_s=0.6)
    detector, runs, _, _ = run_detector(monkeypatch, cfg, lambda n: 0.02, seconds=1.95)
    starts = [t for t, _, _ in runs]
    assert starts == pytest.approx([k / 10.0 for k in range(20)])  # 60 frames offered, 20 runs
    assert detector.runs == 20 and detector.stale_results == 0 and detector.errors == 0
    # Each run took the frame that was newest when it started: at most one loop frame old.
    assert all(-1e-9 <= t - frame_t < 1.0 / LOOP_FPS + 1e-9 for t, _, frame_t in runs)
    ids = [i for _, i, _ in runs]
    assert ids == sorted(set(ids)) and ids[-1] == int(1.9 * LOOP_FPS + 1e-9)


def test_a_model_slower_than_the_period_runs_back_to_back_and_does_not_catch_up_afterwards(monkeypatch):
    cfg = PhoneDetectorConfig(target_fps=10.0, max_result_age_s=0.6)
    slow_runs = 4
    _, runs, _, _ = run_detector(monkeypatch, cfg, lambda n: 0.25 if n <= slow_runs else 0.02, seconds=1.95)
    starts = [t for t, _, _ in runs]
    assert starts[: slow_runs + 1] == pytest.approx([0.0, 0.25, 0.5, 0.75, 1.0])
    # Fast again: one run per period from there, no burst for the runs that were "missed".
    assert gaps(starts[slow_runs:]) == pytest.approx([0.1] * (len(starts) - slow_runs - 1))
    assert min(gaps(starts)) >= 0.1 - 1e-9
    assert all(t - frame_t < 1.0 / LOOP_FPS + 1e-9 for t, _, frame_t in runs)  # never a queued old frame


def test_target_fps_zero_runs_as_fast_as_the_model_answers(monkeypatch):
    cfg = PhoneDetectorConfig(target_fps=0.0, max_result_age_s=0.6)
    _, runs, _, _ = run_detector(monkeypatch, cfg, lambda n: 0.05, seconds=0.98)
    assert [t for t, _, _ in runs] == pytest.approx([k * 0.05 for k in range(20)])


def test_a_run_longer_than_max_result_age_is_unknown_every_time_and_warned_once(monkeypatch, capsys):
    cfg = PhoneDetectorConfig.from_dict(TH["phone"])
    slow = cfg.max_result_age_s + 0.1
    detector, runs, _, _ = run_detector(monkeypatch, cfg, lambda n: slow, seconds=9.5 * slow)
    assert detector.runs == len(runs) == 10 and detector.stale_results == detector.runs
    assert detector.latest(now=detector._result.finished_at) is None  # too old the moment it arrives
    assert capsys.readouterr().out.count("WARNING") == 1


def test_a_result_is_used_until_max_result_age_after_its_frame(monkeypatch):
    cfg = PhoneDetectorConfig.from_dict(TH["phone"])
    detector, runs, _, _ = run_detector(monkeypatch, cfg, lambda n: 0.03, seconds=0.01)
    assert len(runs) == 1
    frame_t = runs[0][2]
    assert detector.latest(now=frame_t + cfg.max_result_age_s) is not None
    assert detector.latest(now=frame_t + cfg.max_result_age_s + 1e-6) is None


def test_a_run_that_raises_does_not_shift_the_schedule(monkeypatch, capsys):
    cfg = PhoneDetectorConfig(target_fps=10.0, max_result_age_s=0.6)
    boom = RuntimeError("boom")
    detector, _, _, calls = run_detector(monkeypatch, cfg, lambda n: boom if n in (3, 4) else 0.02, seconds=0.95)
    # The failing runs held their slots: the model is called once per period all the same.
    assert calls == pytest.approx([k / 10.0 for k in range(10)])
    assert detector.runs == 8 and detector.errors == 2
    assert capsys.readouterr().out.count("run failed") == 1  # one streak


def test_without_frames_the_thread_waits_and_does_not_spin(monkeypatch):
    cfg = PhoneDetectorConfig(target_fps=10.0, max_result_age_s=0.6)
    detector, runs, feed, _ = run_detector(monkeypatch, cfg, lambda n: 0.02, seconds=5.0, camera=False)
    assert runs == [] and detector.latest(now=5.0) is None
    assert feed.waits == 10  # one look every 0.5 s, not a busy loop


# ---------------------------------------------------------------- block 1: a lost camera, on a clock


def textured(i: int) -> np.ndarray:
    """A small image that differs from frame to frame (a live sensor is never still)."""
    return ((np.arange(48 * 64 * 3, dtype=np.uint32).reshape(48, 64, 3) * 7 + i * 13) % 251).astype(np.uint8)


class Handoffs:
    """Stands in for the source's condition variable: notes when a frame is handed to the consumer."""

    def __init__(self, src: FrameSource, log: list) -> None:
        self.src, self.log = src, log

    def __enter__(self) -> Handoffs:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def notify_all(self) -> None:
        if not self.src._ended:
            self.log.append(("handed", self.src._latest.timestamp))


class TimedCamera:
    """Stands in for cv2.VideoCapture on the fake clock: a read takes one frame time and gives a frame,
    until `good` frames were read; then every read fails at once (unplugged)."""

    def __init__(self, clock: Clock, log: list, good: float = math.inf, opened: bool = True, read_s: float = 1 / 30):
        self.clock, self.log, self.good, self.opened, self.read_s = clock, log, good, opened, read_s
        self.reads, self.released = 0, False

    def isOpened(self):  # noqa: N802 - mirrors OpenCV API
        return self.opened

    def read(self):
        if self.reads >= self.good:
            return False, None
        self.clock.t += self.read_s
        self.reads += 1
        self.log.append(("frame", self.clock.t))
        return True, textured(self.reads + id(self) % 1000)

    def get(self, prop):
        return 30.0

    def set(self, prop, value):
        return True

    def release(self):
        self.released = True


def run_reader(monkeypatch, cameras, cfg, seconds, source=0):
    """Block 1's reader loop, in this thread, for `seconds` of the fake clock. cameras(clock, log, n):
    the n-th camera the source opens (0 = at start); it may raise. Returns (source, log, opened, ended_at):
    log holds ("frame" read | "handed" to the consumer | "open" | "lost" | "back", time), opened the
    cameras that were built, ended_at the time the loop returned (`seconds` unless the stream ended)."""
    clock, log, opened, asked = Clock(), [], [], []
    monkeypatch.setattr(frame_source_module, "time", clock)

    def factory(_source):
        log.append(("open", clock.t))
        asked.append(clock.t)
        cam = cameras(clock, log, len(asked) - 1)
        opened.append(cam)
        return cam

    src = FrameSource(source, cfg, capture_factory=factory)
    src._cap = factory(source)
    del log[0]  # the first open is the start, not a reopen
    src.source_fps = 30.0
    src._last_frame_t = src._changed_t = clock.t
    src._thread = threading.current_thread()  # `lost` only answers for a source that was started
    stop = src._stop_event = Until(clock, seconds)
    waited = stop.wait

    def wait(timeout=None):  # the reader waits here between two attempts: note what it reports meanwhile
        log.append(("lost" if src.lost else "back", clock.t))
        return waited(timeout)

    stop.wait = wait
    src._cond = Handoffs(src, log)
    src._run()
    return src, log, opened, clock.t


def times(log, kind):
    return [t for k, t in log if k == kind]


CAPTURE = CaptureConfig.from_dict(TH["capture"])
GIVE_UP_S = (CAPTURE.max_consecutive_failures - 1) * 0.01  # failed reads, 10 ms apart, until the camera is let go


def test_a_lost_camera_is_asked_for_every_reconnect_interval_until_it_opens(monkeypatch):
    def cameras(clock, log, n):
        if n == 0:
            return TimedCamera(clock, log, good=30)  # one second of frames, then unplugged
        return TimedCamera(clock, log, opened=n >= 3)  # the third attempt finds it again

    src, log, opened, _ = run_reader(monkeypatch, cameras, CAPTURE, seconds=12.0)
    lost_at = 1.0 + GIVE_UP_S
    every = CAPTURE.reconnect_interval_s
    assert times(log, "open") == pytest.approx([lost_at + every, lost_at + 2 * every, lost_at + 3 * every])
    assert times(log, "lost") == pytest.approx([lost_at, lost_at + every, lost_at + 2 * every])
    assert times(log, "back") == []  # never reported as working while it was being reopened
    assert src.reconnects == 1
    assert [c.released for c in opened] == [True, True, True, False]  # every dead handle was let go
    # Frames flow again one frame time after the camera opened, and the outage is over.
    frames = times(log, "handed")
    assert frames[29] == pytest.approx(1.0)
    assert frames[30] == pytest.approx(lost_at + 3 * every + 1 / 30)
    assert not src.lost and src.reopen_attempts == 0
    assert src._latest.frame_id == len(frames) - 1  # ids go on, no frame id is used twice


def test_no_frame_is_handed_on_while_the_camera_is_away(monkeypatch):
    def cameras(clock, log, n):
        return TimedCamera(clock, log, good=30) if n == 0 else TimedCamera(clock, log, opened=False)

    src, log, _, _ = run_reader(monkeypatch, cameras, CAPTURE, seconds=20.0)
    assert len(times(log, "handed")) == 30 and src._latest.frame_id == 29
    assert src.lost and src.reconnects == 0
    assert src.reopen_attempts == len(times(log, "open")) >= 9  # the HUD's "attempt N" keeps counting


def test_a_driver_error_while_reopening_is_one_more_failed_attempt(monkeypatch):
    def cameras(clock, log, n):
        if n == 1:
            raise OSError("device busy")
        return TimedCamera(clock, log, good=30 if n == 0 else math.inf)

    src, log, opened, _ = run_reader(monkeypatch, cameras, CAPTURE, seconds=8.0)
    assert len(times(log, "open")) == 2 and len(opened) == 2 and src.reconnects == 1
    assert not src.lost and len(times(log, "handed")) > 30


def test_with_reconnect_off_a_lost_camera_ends_the_stream(monkeypatch):
    from dataclasses import replace

    cfg = replace(CAPTURE, reconnect_interval_s=0.0)
    cameras = lambda clock, log, n: TimedCamera(clock, log, good=30)  # noqa: E731
    src, log, _, ended_at = run_reader(monkeypatch, cameras, cfg, seconds=10.0)
    assert src.ended and ended_at == pytest.approx(1.0 + GIVE_UP_S)  # at once, not when the test's time ran out
    assert times(log, "open") == [] and len(times(log, "handed")) == 30


def test_a_few_failed_reads_are_not_a_lost_camera(monkeypatch):
    class Hiccup(TimedCamera):
        def read(self):
            self.calls = getattr(self, "calls", 0) + 1
            if self.calls % 40 == 0:  # one bad read now and then
                return False, None
            return super().read()

    src, log, opened, _ = run_reader(monkeypatch, lambda clock, log, n: Hiccup(clock, log), CAPTURE, seconds=10.0)
    assert len(opened) == 1 and src.reconnects == 0 and not src.lost
    assert max(gaps(times(log, "handed"))) == pytest.approx(1 / 30 + 0.01)


def test_a_camera_whose_read_hangs_is_lost_after_frame_timeout_and_not_before(monkeypatch):
    clock = Clock()
    monkeypatch.setattr(frame_source_module, "time", clock)
    src = FrameSource(0, CAPTURE, capture_factory=lambda _s: None)
    src._thread = threading.current_thread()
    src._last_frame_t = clock.t = 50.0
    clock.t += CAPTURE.frame_timeout_s
    assert not src.lost
    clock.t += 0.001
    assert src.lost
    src._last_frame_t = clock.t  # a frame came
    assert not src.lost


def test_a_video_file_is_released_at_its_own_fps_and_does_not_burst_after_a_slow_frame(monkeypatch):
    class Clip(TimedCamera):
        def read(self):
            if self.reads == 10:
                self.clock.t += 0.5  # one frame takes half a second to decode
            return super().read()

    cfg = CaptureConfig(video_realtime=True)
    src, log, _, _ = run_reader(
        monkeypatch, lambda clock, log, n: Clip(clock, log, read_s=0.0), cfg, seconds=2.0, source="clip.mp4"
    )
    handed = gaps(times(log, "handed"))
    assert not src.lost  # a file is never "lost"
    assert handed[:9] == pytest.approx([1 / 30] * 9)
    assert max(handed) == pytest.approx(0.5)
    after = handed[handed.index(max(handed)) + 1 :]
    assert len(after) > 20 and after == pytest.approx([1 / 30] * len(after))  # no catching up


# ---------------------------------------------------------------- block 2


@pytest.mark.parametrize(
    ("size", "expected"),
    [
        ((1280, 720), (640, 360)),
        ((1920, 1080), (640, 360)),
        ((1000, 333), (640, 213)),
        ((641, 480), (640, 479)),
        ((640, 480), (640, 480)),  # at the target width: untouched
        ((320, 240), (320, 240)),  # smaller: never enlarged
        ((4000, 3), (640, 1)),  # never a height of 0
    ],
)
def test_resize_keeps_the_aspect_ratio_and_only_shrinks(size, expected):
    (w, h), (out_w, out_h) = size, expected
    pre = Preprocessor(PreprocessConfig.from_dict(TH["preprocess"]))
    image = np.zeros((h, w, 3), dtype=np.uint8)
    out, scale = pre.resize(image)
    assert out.shape[:2] == (out_h, out_w)
    assert scale == pytest.approx(out_w / w)
    assert abs(out_h - max(1.0, h * scale)) <= 0.5  # the height follows the width, to the nearest pixel
    if w <= pre.config.target_width:
        assert out is image and scale == 1.0


def test_scale_maps_a_point_of_the_output_back_to_the_camera_image():
    pre = Preprocessor(PreprocessConfig.from_dict(TH["preprocess"]))
    image = np.zeros((720, 1280, 3), dtype=np.uint8)
    image[300:420, 800:960] = 255  # a bright block, centre (880, 360)
    bgr, _gray, _brightness, _is_ir, scale, luma = pre.process_image(image)
    ys, xs = np.nonzero(luma > 128)
    assert (xs.mean() + 0.5) / scale == pytest.approx(880, abs=1.0)
    assert (ys.mean() + 0.5) / scale == pytest.approx(360, abs=1.0)
    assert bgr.shape[:2] == luma.shape[:2] == (360, 640)


def colour_image(brightness: float, tint: float = 0.15) -> np.ndarray:
    """A colour image (BGR) whose channels lie `tint` of its brightness apart. On the webcam of the
    self-recorded sessions the channel difference is 6-20 % of the brightness (audit A1 H1)."""
    bgr = np.array([brightness * (1 - tint), brightness, brightness * (1 + tint)])
    return np.broadcast_to(np.round(bgr).astype(np.uint8), (48, 64, 3)).copy()


def test_a_colour_image_in_daylight_is_not_infrared():
    pre = Preprocessor(PreprocessConfig.from_dict(TH["preprocess"]))
    for brightness in (40, 80, 120, 200):
        assert not pre.is_ir_image(colour_image(brightness)), brightness


@pytest.mark.xfail(
    strict=True,
    reason="audit A1 H1, open (docs/improvements.md: block 5 in low light): the IR test compares the "
    "absolute channel difference with preprocess.ir_channel_diff_max, so a dark colour image passes for infrared",
)
@pytest.mark.parametrize("brightness", [6, 10, 12])
def test_a_dark_colour_image_is_not_infrared(brightness):
    pre = Preprocessor(PreprocessConfig.from_dict(TH["preprocess"]))
    assert not pre.is_ir_image(colour_image(brightness))


# ---------------------------------------------------------------- the page measures as the device does


def test_the_fixture_the_page_is_checked_against_is_what_the_device_measures():
    """frontend/src/live/measure.fixture.json is generated (tools/measure_fixture.py) and checked in.
    The numbers are recomputed on the pixels in the file, so this holds on any platform."""
    how = "run: python tools/measure_fixture.py"
    assert measure_fixture.DEST.exists(), how
    doc = json.loads(measure_fixture.DEST.read_text(encoding="utf-8"))
    cfg = PreprocessConfig.from_dict(TH["preprocess"])
    assert (doc["stride"], doc["ir_channel_diff_max"]) == (cfg.sample_stride, cfg.ir_channel_diff_max), how
    assert doc["tolerance"] == measure_fixture.TOLERANCE and doc["box"] == list(measure_fixture.BOX), how
    assert set(doc["images"]) == set(measure_fixture.IMAGES), how
    for name, image in doc["images"].items():
        rgb = np.array(image["rgb"], dtype=np.uint8).reshape(doc["height"], doc["width"], 3)
        now = measure_fixture.device_numbers(rgb, TH)
        assert now["is_ir"] == image["device"]["is_ir"], f"{name}: {how}"
        for key, value in image["device"].items():
            assert now[key] == pytest.approx(value, abs=1e-3), f"{name}.{key}: {how}"


def test_the_fixture_shows_a_colour_a_gray_and_a_dim_colour_image():
    doc = measure_fixture.fixture(TH)
    device = {name: image["device"] for name, image in doc["images"].items()}
    assert not device["colour"]["is_ir"] and device["colour"]["channel_diff"] > 5 * doc["ir_channel_diff_max"]
    assert device["gray"]["is_ir"] and device["gray"]["channel_diff"] == 0
    assert device["dim"]["face_brightness"] < TH["quality"]["dark_face_brightness"]  # dark enough to matter
    assert all(d["sharpness"] > TH["quality"]["blur_sharpness"] for d in device.values())


# ---------------------------------------------------------------- block 12 with the thresholds of the YAML

ALERTS = AlertConfig.from_dict(TH["alert"])
HOLD_S = ALERTS.fall_hold_s
DT = 0.1


def play(script, cfg=ALERTS, frame_times=None):
    """script: (level, reasons, seconds) one after the other. frame_times: when frames come (default:
    every DT). Returns (alerts as (time, level, reasons), active level per frame as (time, level))."""
    end = sum(seconds for _, _, seconds in script)
    ts = [i * DT for i in range(round(end / DT))] if frame_times is None else [t for t in frame_times if t < end]
    m, alerts, active = AlertManager(cfg), [], []
    for t in ts:
        at = 0.0
        for level, reasons, seconds in script:
            at += seconds
            if t < at - 1e-9:
                break
        hits = tuple(RuleHit(level, r, 1.0) for r in reasons) if level else ()
        out = m.update(RiskAssessment(t, level, hits, 0.0, 0.0, (0, 0, 0, 0)))
        active.append((t, out.active_level))
        if out.new_alert is not None:
            alerts.append((round(t, 3), out.new_alert.level, out.new_alert.reasons))
    return alerts, active


MICROSLEEP = (3, ("microsleep",), 2.0)
AWAKE = lambda seconds: (0, (), seconds)  # noqa: E731


def test_the_yaml_gives_l3_no_cooldown_and_no_wait():
    assert ALERTS.cooldown_s[3] == 0 and ALERTS.rise_confirm_s[3] == 0


def test_l3_is_raised_in_the_frame_it_appears():
    alerts, _ = play([AWAKE(5.0), MICROSLEEP])
    assert alerts == [(5.0, 3, ("microsleep",))]


def test_a_second_microsleep_after_the_hold_is_a_new_l3_alert_at_once():
    alerts, _ = play([MICROSLEEP, AWAKE(HOLD_S + 0.5), MICROSLEEP])
    assert [(t, level) for t, level, _ in alerts] == [(0.0, 3), (2.0 + HOLD_S + 0.5, 3)]


def test_eyes_open_for_less_than_the_hold_is_still_the_same_l3():
    alerts, active = play([MICROSLEEP, AWAKE(HOLD_S - 0.5), MICROSLEEP])
    assert [level for _, level, _ in alerts] == [3]
    assert all(level == 3 for _, level in active)  # the level never dropped in between


def test_with_the_10_s_cooldown_of_the_older_unit_tests_the_second_microsleep_would_wait():
    """What test_decision.py's CFG (cooldown_s[3] = 10) shows is not what the product does: there the
    second microsleep is held back until the cooldown has passed."""
    from dataclasses import replace

    cfg = replace(ALERTS, cooldown_s={**ALERTS.cooldown_s, 3: 10.0})
    alerts, _ = play([MICROSLEEP, AWAKE(HOLD_S + 0.5), (3, ("microsleep",), 8.0)], cfg)
    assert [t for t, _, _ in alerts] == [0.0, 10.0 + ALERTS.rise_confirm_s[3]]


def test_the_level_drops_fall_hold_s_after_the_last_frame_that_showed_it():
    _, active = play([MICROSLEEP, AWAKE(HOLD_S + 2.0)])
    last_seen = 2.0 - DT
    dropped = next(t for t, level in active if level == 0)
    assert dropped == pytest.approx(last_seen + HOLD_S, abs=DT + 1e-9)
    assert all(level == 3 for t, level in active if t < last_seen + HOLD_S - 1e-9)


def uneven_times(seed, fps, end):
    """Frames about 1 / fps apart with log-normal waits (eval.fps_study_jitter_cv), as M75's loops."""
    cv = float(TH["eval"]["fps_study_jitter_cv"])
    sigma2 = math.log(1.0 + cv**2)
    waits = np.random.default_rng(seed).lognormal(-math.log(fps) - sigma2 / 2.0, math.sqrt(sigma2), int(end * fps * 3))
    t = np.concatenate(([0.0], np.cumsum(waits)))
    return [float(x) for x in t[t < end]]


@pytest.mark.parametrize("seed", range(12))
@pytest.mark.parametrize("level", [1, 2])
def test_on_uneven_frames_a_level_is_confirmed_by_time_not_by_frame_count(level, seed):
    confirm = ALERTS.rise_confirm_s[level]
    ts = uneven_times(seed, 12.0, 20.0)
    start = 5.0
    alerts, _ = play([AWAKE(start), (level, ("x",), 15.0)], frame_times=ts)
    seen = [t for t in ts if t >= start]
    worst_gap = max(gaps(seen[: next(i for i, t in enumerate(seen) if t > start + confirm + 1.0)]))
    assert worst_gap <= ALERTS.max_gap_s  # these loops never trip the gap rule: the wait is the plain one
    assert len(alerts) >= 1
    first = alerts[0][0]
    assert first >= seen[0] + confirm - 1e-9  # never before the level was seen for that long
    assert first <= seen[0] + confirm + worst_gap + 1e-9  # late by one frame gap at most


@pytest.mark.parametrize("seed", range(12))
def test_on_uneven_frames_a_level_seen_for_less_than_the_wait_is_never_alerted(seed):
    confirm = ALERTS.rise_confirm_s[2]
    ts = uneven_times(seed, 12.0, 30.0)
    script = []
    for _ in range(8):  # eight looks away, each just under the confirmation time
        script += [AWAKE(2.0), (2, ("off_road",), confirm - 0.05)]
    alerts, active = play(script, frame_times=ts)
    assert alerts == [] and all(level == 0 for _, level in active)


# ---------------------------------------------------------------- the context factors on real recordings


def at_night_after_a_long_drive(thresholds):
    set_threshold(thresholds, "eval.replay_clock_hour=2")
    set_threshold(thresholds, f"eval.replay_drive_time_s={2 * thresholds['context']['long_drive_s']}")
    return thresholds


@pytest.fixture(scope="module")
def day_and_night():
    """Every fixture video replayed twice on the device path: at noon with no driving behind it (what
    the trace regression pins), and at 02:00 after a long drive."""
    traces = rt.load_fixture()
    day, night = load_thresholds(), at_night_after_a_long_drive(load_thresholds())
    return {name: (replay(tr, day, "block5"), replay(tr, night, "block5")) for name, tr in traces.items()}


def test_night_and_a_long_drive_multiply_the_drowsy_score_and_nothing_else(day_and_night):
    drowsy = TH["risk"]["drowsy"]
    factor = drowsy["night_factor"] * drowsy["long_drive_factor"]
    raised = 0
    for name, (day, night) in day_and_night.items():
        d, n = day["cols"]["drowsy_score"], night["cols"]["drowsy_score"]
        assert np.allclose(n, np.minimum(d * factor, 100.0), atol=1e-6), name
        raised += int((n > d + 1e-9).sum())
        # What blocks 7 and 8 measure does not know the hour.
        assert day["events"] == night["events"], name
        for col in ("closed_duration", "perclos", "off_road_s", "distraction_level", "unavailable"):
            assert np.array_equal(day["cols"][col], night["cols"][col], equal_nan=True), (name, col)
    assert raised > 1000  # the factors are really on: thousands of frames score higher


def other_rules(run):
    """The alerts that name a rule other than the drowsy score, without that name."""
    out = []
    for frame, level, reasons in run["alerts"]:
        rest = tuple(r for r in reasons if r != "drowsy_score")
        if rest:
            out.append((frame, level, rest))
    return out


def test_night_and_a_long_drive_never_lower_a_level_and_only_add_drowsiness_alerts(day_and_night):
    added = []
    for name, (day, night) in day_and_night.items():
        assert np.all(night["cols"]["level"] >= day["cols"]["level"]), name
        # Alerts of the other rules (microsleep, off_road, phone, ...) come in the same frame at the same
        # level; a drowsiness line crossed at night may only be named beside them.
        by_day, by_night = other_rules(day), other_rules(night)
        assert by_night == by_day, name
        added.append(len(night["alerts"]) - len(day["alerts"]))
    assert sum(added) > 0, "no fixture video crosses a drowsiness line at night: the test shows nothing"
    assert min(added) >= 0  # no video has fewer alerts at night
