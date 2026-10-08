"""M83: a passenger alone in view is not the driver; a camera that repeats one image is a lost camera
(audit 08/10, A1 M5 and A1 M3).

- Block 3: once enrolled, a face standing alone was the driver wherever it was. Now the best face is
  nobody's when it is further than landmarks.driver_max_distance from where the driver was last
  seen: no face is reported, so "face lost" runs (blocks 8, 9).
- Block 1: a camera whose driver hands the same image again and again read as a driver sitting still
  with open eyes. Now the same sparse pixels for capture.frame_timeout_s is a lost camera.
Fake landmark numbers and a fake capture, no video.
"""

import json
import threading
import time
from types import SimpleNamespace

import numpy as np
import pytest

from edge_agent.capture import CaptureConfig, FrameSource
from edge_agent.config import load_thresholds
from edge_agent.perception.landmarks import (
    DriverAnchor,
    DriverSelector,
    FaceLandmarkDetector,
    LandmarkConfig,
    face_center_size,
    face_shape,
)
from edge_agent.perception.preprocess import PreprocessedFrame
from edge_agent.web.bridge import WebAgent
from tests.test_edge_agent.test_enrollment import place, synthetic_mesh
from tests.test_edge_agent.test_web_bridge import H, W, events_of, run, synthetic_face

IOD = 60.0  # inter-ocular distance of synthetic_mesh at scale 1, pixels
SEAT = (220.0, 240.0)  # where the driver enrolls
LIMIT = LandmarkConfig().driver_max_distance


def driver_at(dx: float = 0.0, dy: float = 0.0, seed: int = 1) -> np.ndarray:
    """A face `dx`, `dy` enrolled inter-ocular distances from the driver's seat."""
    return place(synthetic_mesh(seed), 1.0, SEAT[0] + dx * IOD, SEAT[1] + dy * IOD)


def enrolled(config: LandmarkConfig | None = None) -> DriverSelector:
    selector = DriverSelector(config or LandmarkConfig())
    center, size = face_center_size(driver_at(), W)
    selector.set_anchor(DriverAnchor(face_shape(driver_at()), center, size))
    return selector


# ---------------------------------------------------------------- block 3: the limit


def test_the_limit_in_the_yaml_is_on_and_is_the_default():
    cfg = LandmarkConfig.from_dict(load_thresholds()["landmarks"])
    assert cfg.driver_max_distance == LIMIT > cfg.driver_position_tol  # looser than the unit of the score


def test_a_lone_face_far_from_the_driver_is_nobody():
    selector = enrolled()
    assert selector.choose([driver_at(LIMIT + 0.5, seed=2)], W) == -1
    assert selector.choose([driver_at(0, LIMIT + 0.5, seed=2)], W) == -1  # any direction


def test_a_lone_face_inside_the_limit_is_taken_whatever_its_shape():
    # The shape signature does not tell people apart (thresholds.yaml): a stranger in the driver's
    # seat is still read as the driver. Known limit, kept here so a change of it is seen.
    selector = enrolled()
    assert selector.choose([place(synthetic_mesh(2, cheek_scale=1.4), 1.0, *SEAT)], W) == 0
    assert selector.choose([driver_at(LIMIT - 0.5)], W) == 0


def test_the_driver_is_followed_across_the_image():
    selector = enrolled()
    for step in range(1, 9):  # 0.75 a frame: 6 enrolled inter-ocular distances in all
        assert selector.choose([driver_at(0.75 * step)], W) == 0


def test_a_rejected_face_does_not_move_the_drivers_position():
    selector = enrolled()
    stranger = driver_at(LIMIT + 1.0, seed=2)
    for _ in range(300):  # the passenger alone for 10 s: never accepted, however long
        assert selector.choose([stranger], W) == -1
    assert selector.choose([driver_at(0.5)], W) == 0  # the driver is back about where they were
    assert selector.choose([stranger], W) == -1


def test_driver_hidden_and_two_others_in_view_is_nobody():
    selector = enrolled()
    assert selector.choose([driver_at(LIMIT + 1.0, seed=2), driver_at(LIMIT + 3.0, seed=3)], W) == -1


def test_the_driver_is_still_chosen_next_to_a_passenger():
    selector = enrolled()
    passenger = place(synthetic_mesh(2, cheek_scale=1.4), 1.3, SEAT[0] + (LIMIT + 1.0) * IOD, SEAT[1])
    assert selector.choose([passenger, driver_at(0.2)], W) == 1
    assert selector.choose([driver_at(0.3), passenger], W) == 0


def test_zero_turns_the_limit_off():
    selector = enrolled(LandmarkConfig(driver_max_distance=0.0))
    assert selector.choose([driver_at(LIMIT + 5.0, seed=2)], W) == 0  # as before M83


def test_before_enrollment_any_face_is_taken():
    selector = DriverSelector(LandmarkConfig())
    assert selector.choose([driver_at(LIMIT + 5.0, seed=2)], W) == 0
    selector = enrolled()
    selector.set_anchor(None)  # "Đổi tài xế": the largest face again until the new driver enrolls
    assert selector.choose([driver_at(LIMIT + 5.0, seed=2)], W) == 0


# ---------------------------------------------------------------- block 3: on the device and in the browser


class Model:
    """Stand-in for MediaPipe's FaceLandmarker: answers with the given faces (pixels)."""

    def __init__(self, faces):
        self.result = SimpleNamespace(
            face_landmarks=[[SimpleNamespace(x=x / W, y=y / H, z=z / W) for x, y, z in f] for f in faces],
            face_blendshapes=None,
        )

    def detect(self, image):
        return self.result


def detect(selector: DriverSelector, faces):
    detector = FaceLandmarkDetector.__new__(FaceLandmarkDetector)  # no model file, no MediaPipe
    detector.config, detector.image_mode = selector.config, True
    detector._mp = SimpleNamespace(Image=lambda **kw: None, ImageFormat=SimpleNamespace(SRGB=0))
    detector._landmarker = Model(faces)
    detector.selector = selector
    image = np.zeros((H, W, 3), np.uint8)
    return detector.detect(PreprocessedFrame(image, image[:, :, 0], 128.0, False, 1.0, 7, 0.5))


def test_device_reports_no_face_for_a_passenger_alone():
    selector = enrolled()
    assert detect(selector, [driver_at(LIMIT + 1.0, seed=2)]) is None
    lm = detect(selector, [driver_at(LIMIT + 1.0, seed=2), driver_at(0.1)])
    assert lm is not None and lm.num_faces == 2
    assert face_center_size(lm.points, W)[0][0] == pytest.approx((SEAT[0] + 0.1 * IOD) / W, abs=1e-4)


def seated(face: np.ndarray, cx: float, scale: float = 0.6) -> np.ndarray:
    """The bridge tests' face, further from the camera (smaller), with its nose at cx."""
    out = (face - face[1]) * scale
    out[:, :2] += (cx, H / 2)
    return out


def test_browser_passenger_alone_while_driving_is_face_lost_not_a_sleeping_driver():
    agent = WebAgent("web-an", "trip-web-1", scenario="highway_night")
    driver = seated(synthetic_face(), 150.0)
    passenger_asleep = seated(synthetic_face(ear=0.05), 500.0)
    center, size = face_center_size(driver, W)
    agent.selector.set_anchor(DriverAnchor(face_shape(driver), center, size))
    assert (500.0 - 150.0) / (size * W) > LIMIT  # the other seat is outside the limit

    state, t, f = run(agent, 12, points=driver)
    assert state["measures"]["face"] and state["level"] == 0
    # The driver is hidden (a phone held up, the sun visor); the passenger sleeps in full view.
    state, t, f = run(agent, 4, t0=t, frame0=f, points=passenger_asleep, blink=(0.9, 0.9))
    assert not state["measures"]["face"] and state["measures"]["ear"] is None
    assert state["unavailable"] and state["level"] == 0  # before M83: L3 microsleep
    state, _, _ = run(agent, 1, t0=t, frame0=f, points=driver)
    assert state["measures"]["face"] and not state["unavailable"]
    assert [e["reasons"] for e in events_of(agent)] == [["monitoring_unavailable"], ["monitoring_restored"]]


def test_browser_with_the_limit_off_reads_the_passenger_as_the_driver(monkeypatch):
    # What M83 closes, kept runnable: the same sequence without the limit is a false L3.
    th = load_thresholds()
    th["landmarks"]["driver_max_distance"] = 0.0
    monkeypatch.setattr("edge_agent.web.bridge.load_thresholds", lambda: th)
    agent = WebAgent("web-an", "trip-web-1", scenario="highway_night")
    driver = seated(synthetic_face(), 150.0)
    center, size = face_center_size(driver, W)
    agent.selector.set_anchor(DriverAnchor(face_shape(driver), center, size))
    _, t, f = run(agent, 12, points=driver)
    state, _, _ = run(agent, 4, t0=t, frame0=f, points=seated(synthetic_face(ear=0.05), 500.0), blink=(0.9, 0.9))
    assert state["level"] == 3 and "microsleep" in state["reasons"]


# ---------------------------------------------------------------- block 1: the same image again


def textured(seed: int = 0, shape=(72, 128, 3)) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, 256, shape, dtype=np.uint8)


def camera(**cfg) -> FrameSource:
    return FrameSource(0, CaptureConfig(**cfg))  # not started: `_repeats` alone, no thread


def test_the_same_image_is_a_repeat_and_one_changed_pixel_is_not():
    src, image = camera(), textured()
    assert not src._repeats(image)  # nothing to compare with
    assert src._repeats(image.copy()) and src._repeats(image.copy())
    noisy = image.copy()
    noisy[8, 16, 1] ^= 1  # sensor noise on one compared pixel
    assert not src._repeats(noisy)
    assert src._repeats(noisy.copy())


def test_the_capture_reusing_its_buffer_is_not_a_repeat():
    src, buffer = camera(), textured()
    assert not src._repeats(buffer)
    buffer[:] = textured(1)  # OpenCV may write the next frame into the same array
    assert not src._repeats(buffer)


def test_an_image_of_one_single_value_is_never_a_repeat():
    # A covered lens gives the same black frame for good: block 6's quality check names that one.
    src = camera()
    for value in (0, 0, 0, 255, 255):
        assert not src._repeats(np.full((72, 128, 3), value, np.uint8))


def test_only_a_camera_is_checked_and_zero_turns_it_off(tmp_path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"")
    image = textured()
    for src in (FrameSource(str(video), CaptureConfig()), camera(frozen_stride=0)):
        assert not src._repeats(image) and not src._repeats(image.copy())  # a video may stand still


def test_an_image_of_another_size_is_not_a_repeat():
    src = camera()
    assert not src._repeats(textured())
    assert not src._repeats(textured(shape=(36, 64, 3)))


class StillCamera:
    """Stands in for cv2.VideoCapture: `live` frames that differ, then the last one again and again."""

    def __init__(self, live: int, seed: int = 0, still: np.ndarray | None = None):
        self.live, self.seed, self.i = live, seed, 0
        self.still = textured(seed + 10_000) if still is None else still

    def isOpened(self):  # noqa: N802 - mirrors OpenCV API
        return True

    def read(self):
        time.sleep(0.002)
        self.i += 1
        return True, (textured(self.seed + self.i) if self.i <= self.live else self.still.copy())

    def get(self, prop):
        return 0.0

    def set(self, prop, value):
        return True

    def release(self):
        pass


def wait_for(condition, seconds: float = 3.0) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.01)
    return False


def test_frozen_camera_is_lost_and_reopened_and_frames_resume():
    opened = []

    def factory(_src):
        opened.append(StillCamera(live=5 if not opened else 10**9, seed=1000 * len(opened)))
        return opened[-1]

    config = CaptureConfig(frame_timeout_s=0.1, reconnect_interval_s=0.05)
    src = FrameSource(0, config, capture_factory=factory)
    with src:
        assert wait_for(lambda: src.lost) and src.freezes == 1
        assert wait_for(lambda: src.reconnects == 1 and not src.lost)
        assert src.read(timeout=1.0) is not None  # frames flow again
        assert src.freezes == 1 and not src.ended


def test_frozen_camera_hands_no_frames_on_and_stays_lost_while_the_image_is_the_same():
    still = textured(7)
    lock, opened = threading.Lock(), []

    def factory(_src):
        with lock:
            opened.append(StillCamera(live=3 if not opened else 0, still=still))
            return opened[-1]

    config = CaptureConfig(frame_timeout_s=0.1, reconnect_interval_s=0.02)
    src = FrameSource(0, config, capture_factory=factory)
    with src:
        assert wait_for(lambda: src.lost)
        while src.read(timeout=0.05) is not None:  # what was handed on before it was found frozen
            pass
        seen_back = False
        assert wait_for(lambda: src.reconnects >= 3)  # reopened again and again, the image never differs
        for _ in range(20):
            seen_back |= not src.lost
            assert src.read(timeout=0.01) is None
        assert not seen_back and src.freezes == 1 and src.reopen_attempts >= 3


def test_a_short_repeat_is_not_a_lost_camera():
    class Stutter(StillCamera):  # every frame is handed over three times, as a camera slower than the loop
        def read(self):
            time.sleep(0.002)
            self.i += 1
            return True, textured(self.i // 3)

    src = FrameSource(0, CaptureConfig(frame_timeout_s=0.2), capture_factory=lambda _s: Stutter(0))
    with src:
        seen = 0
        deadline = time.monotonic() + 0.6
        while time.monotonic() < deadline:
            seen += src.read(timeout=0.05) is not None
            assert not src.lost
        assert seen > 20 and src.freezes == 0


def test_the_browser_gets_the_stride_from_the_yaml():
    settings = json.loads(WebAgent("web-an", "trip-web-1", scenario="highway_night").settings())
    cfg = CaptureConfig.from_dict(load_thresholds()["capture"])
    assert settings["capture"]["frozen_stride"] == cfg.frozen_stride == CaptureConfig().frozen_stride > 0
