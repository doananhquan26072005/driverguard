import numpy as np

from edge_agent.capture import Frame
from edge_agent.perception import PreprocessConfig, Preprocessor


def make_frame(image):
    return Frame(image=image, frame_id=7, timestamp=1.5)


def test_ir_single_channel_becomes_three_channels():
    pre = Preprocessor(PreprocessConfig(target_width=320))
    img = np.random.default_rng(0).integers(0, 255, (480, 640), dtype=np.uint8)
    out = pre(make_frame(img))
    assert out.is_ir
    assert out.image.shape == (240, 320, 3)
    assert out.gray.shape == (240, 320)
    assert out.scale == 0.5
    assert out.frame_id == 7 and out.timestamp == 1.5


def test_three_equal_channels_detected_as_ir():
    pre = Preprocessor()
    gray = np.random.default_rng(1).integers(0, 255, (100, 100), dtype=np.uint8)
    assert pre(make_frame(np.dstack([gray] * 3))).is_ir


def test_color_image_not_ir():
    pre = Preprocessor()
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[..., 2] = 200  # red
    out = pre(make_frame(img))
    assert not out.is_ir
    assert out.image.shape == (100, 100, 3)  # smaller than target: no upscale


def test_brightness_measured_before_clahe():
    pre = Preprocessor()
    dark = np.full((100, 100), 30, dtype=np.uint8)
    bright = np.full((100, 100), 220, dtype=np.uint8)
    assert abs(pre(make_frame(dark)).brightness - 30) < 1
    assert abs(pre(make_frame(bright)).brightness - 220) < 1


def test_clahe_increases_contrast_on_low_contrast_image():
    rng = np.random.default_rng(2)
    img = rng.integers(40, 60, (200, 200), dtype=np.uint8)
    on = Preprocessor(PreprocessConfig(clahe_enabled=True))(make_frame(img))
    off = Preprocessor(PreprocessConfig(clahe_enabled=False))(make_frame(img))
    assert on.gray.std() > off.gray.std()


def test_config_from_yaml_dict():
    cfg = PreprocessConfig.from_dict({"target_width": 480, "clahe": {"clip_limit": 3.0, "enabled": False}})
    assert cfg.target_width == 480
    assert cfg.clahe_clip_limit == 3.0
    assert not cfg.clahe_enabled
