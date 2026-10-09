"""M98: a dark colour image is not an infrared one (audit 08/10, A1 H1; decision 13A of 09/10).

Block 2 called a 3-channel frame infrared when the mean difference between its channels was under
preprocess.ir_channel_diff_max (2.0 of 255). A colour camera's difference shrinks with the light: on the
self-recorded sessions it is 6-20 % of the brightness, and at a face brightness of 10-11 the flag was on
for 98-100 % of the frames. Block 5 then handed the eyes to the CNN (device) or to eyeBlink on every
frame (page), exactly where M54 had given them to EAR, and enrollment refused the dark cabin.
Now the difference must also be small against the brightness, and the camera's kind is held over time.
Fake images and numbers, no video, no model.
"""

import numpy as np
import pytest

from edge_agent.capture.frame_source import Frame
from edge_agent.config import load_thresholds
from edge_agent.perception.preprocess import IrLatch, PreprocessConfig, Preprocessor, looks_infrared
from edge_agent.web.bridge import WebAgent
from tests.test_edge_agent.test_web_bridge import H, W, synthetic_face

TH = load_thresholds()
CFG = PreprocessConfig.from_dict(TH["preprocess"])
BEFORE = PreprocessConfig.from_dict({**TH["preprocess"], "ir_channel_rel_max": 0})  # the absolute limit alone


def colour(brightness: float, tint: float = 0.15) -> np.ndarray:
    """A colour image (BGR) whose channels lie `tint` of its brightness apart (webcam: 6-20 %)."""
    bgr = np.array([brightness * (1 - tint), brightness, brightness * (1 + tint)])
    return np.broadcast_to(np.round(bgr).astype(np.uint8), (48, 64, 3)).copy()


def grey(brightness: float, noise: int = 0) -> np.ndarray:
    """An infrared / grayscale camera as 3 channels; `noise`: one channel off by that much on every 4th pixel."""
    image = np.full((48, 64, 3), round(brightness), np.uint8)
    image[::2, ::2, 2] += noise
    return image


# ---------------------------------------------------------------- one frame


def test_the_keys_come_from_the_yaml():
    assert (CFG.ir_channel_diff_max, CFG.ir_channel_rel_max, CFG.ir_switch_s) == (2.0, 0.03, 2.0)
    assert PreprocessConfig() == CFG  # the defaults are the YAML's


@pytest.mark.parametrize("brightness", [6, 8, 10, 12, 20, 35])
def test_a_dark_colour_image_is_colour_at_every_brightness_the_sessions_reached(brightness):
    image = colour(brightness, tint=0.10)
    assert not Preprocessor(CFG).is_ir_image(image)
    if brightness <= 12:  # the audit's finding: under the absolute limit alone these were infrared
        assert Preprocessor(BEFORE).is_ir_image(image)


@pytest.mark.parametrize("brightness", [4, 10, 40, 120, 220])
def test_a_grayscale_camera_is_infrared_at_any_light(brightness):
    assert Preprocessor(CFG).is_ir_image(grey(brightness))
    assert Preprocessor(CFG).is_ir_image(np.full((48, 64), brightness, np.uint8))  # one channel


def test_a_little_chroma_noise_on_a_grayscale_camera_is_still_infrared_in_normal_light():
    assert Preprocessor(CFG).is_ir_image(grey(120, noise=4))  # mean difference 0.5 of 120


def test_the_two_numbers_decide_and_an_unmeasured_brightness_asks_only_the_absolute_limit():
    assert looks_infrared(CFG, 0.0, 10.0) and looks_infrared(CFG, 0.0, 0.0)
    assert not looks_infrared(CFG, 1.0, 10.0)  # 10 % of the brightness: a colour camera in the dark
    assert looks_infrared(CFG, 1.0, 100.0)  # 1 %: noise
    assert not looks_infrared(CFG, 2.5, 200.0)  # over the absolute limit, whatever the light
    assert looks_infrared(CFG, 1.0, None)  # a page older than the scene numbers: as before M98
    assert looks_infrared(BEFORE, 1.0, 10.0)


# ---------------------------------------------------------------- the camera's kind over time


def test_the_first_frame_decides_and_a_stray_frame_does_not_change_the_kind():
    latch = IrLatch(CFG)
    assert latch.update(0.0, False) is False
    assert latch.update(0.1, True) is False  # one frame that looks infrared (a black frame, a flash)
    assert latch.update(0.2, False) is False


def test_the_kind_changes_after_the_frames_said_so_for_ir_switch_s_without_a_break():
    latch, t = IrLatch(CFG), 0.0
    latch.update(t, False)
    for _ in range(int(CFG.ir_switch_s * 30) - 1):
        t += 1 / 30
        assert latch.update(t, True) is False
    assert latch.update(t + 0.1, False) is False  # a break: the count starts again
    t += 0.2
    for _ in range(int(CFG.ir_switch_s * 30) + 2):
        t += 1 / 30
        kind = latch.update(t, True)
    assert kind is True  # the camera switched its IR filter


def test_time_that_does_not_move_forward_starts_again():
    """Single images (tools/dataset.py hands every image over at t = 0) and a new video are judged afresh."""
    pre = Preprocessor(CFG)
    assert pre(Frame(image=grey(120), frame_id=0, timestamp=0.0)).is_ir
    assert not pre(Frame(image=colour(120), frame_id=0, timestamp=0.0)).is_ir
    assert pre(Frame(image=grey(120), frame_id=0, timestamp=0.0)).is_ir


def test_block_2_keeps_the_kind_through_a_dark_stretch_of_a_colour_camera():
    pre, kinds = Preprocessor(CFG), []
    for i in range(300):  # 10 s: daylight, then a tunnel so dark that single frames lose their colour
        dark = 90 <= i < 120
        image = np.zeros((48, 64, 3), np.uint8) if dark else colour(100)
        kinds.append(pre(Frame(image=image, frame_id=i, timestamp=i / 30)).is_ir)
    assert not any(kinds)  # 1 s of black frames is shorter than ir_switch_s


def test_a_one_channel_frame_is_infrared_whatever_the_latch_says():
    pre = Preprocessor(CFG)
    assert not pre(Frame(image=colour(100), frame_id=0, timestamp=0.0)).is_ir
    assert pre(Frame(image=np.full((48, 64), 90, np.uint8), frame_id=1, timestamp=0.1)).is_ir


# ---------------------------------------------------------------- the page (same numbers, same rule)


def page_frames(scene_brightness, channel_diff, face_brightness, frames=90):
    """The page's agent on frames with these pixel numbers. Returns how often block 5 took over from EAR."""
    agent = WebAgent("web-an", "trip-m98", scenario="highway_night")
    points = synthetic_face().ravel()
    for i in range(frames):
        t = i / 30
        agent.frame(
            t, i, W, H, points, 1, (0.05, 0.05), channel_diff, face_brightness, None, scene_brightness, 40.0, 140.0
        )
    return agent.eye_state.runs


def test_the_page_does_not_take_a_dark_colour_frame_for_infrared():
    # a dark cabin: scene 12, the channels 1.2 apart (10 %). EAR decides, as M54 meant for a dark face.
    assert page_frames(scene_brightness=12.0, channel_diff=1.2, face_brightness=11.0) == 0


def test_before_m98_the_same_frames_gave_every_frame_to_eye_blink(monkeypatch):
    th = load_thresholds()
    th["preprocess"]["ir_channel_rel_max"] = 0
    monkeypatch.setattr("edge_agent.web.bridge.load_thresholds", lambda: th)
    assert page_frames(scene_brightness=12.0, channel_diff=1.2, face_brightness=11.0) == 90


def test_the_page_still_takes_a_grayscale_camera_for_infrared():
    assert page_frames(scene_brightness=90.0, channel_diff=0.0, face_brightness=90.0) == 90
    assert page_frames(scene_brightness=8.0, channel_diff=0.0, face_brightness=8.0) == 90  # and in the dark
