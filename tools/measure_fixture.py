"""Write frontend/src/live/measure.fixture.json: a few synthetic images and what the device measures
on them, so the page's measurements (frontend/src/live/measure.ts) are checked against the device's
on the same pixels (audit 08/10, A1 L4: three copies of the same arithmetic and no test across them).

The device's numbers come from the code the device runs: block 2 (`Preprocessor`), block 5
(`eye_state.face_brightness`) and block 6's quality stage (`quality.measure`). The page's own test
(measure.test.ts) reads the same file and must land within TOLERANCE of them; the tolerances say how
far the two are allowed to be apart, and why. tests/test_edge_agent/test_m88_missing_tests.py fails
when the file no longer matches the device's code.

The images are arithmetic patterns (a wave plus a texture), never a camera frame: no face, no person.

    python tools/measure_fixture.py            # rewrite the file
    python tools/measure_fixture.py --check    # exit 1 when it is out of date
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from edge_agent.capture.frame_source import Frame  # noqa: E402
from edge_agent.config import load_thresholds  # noqa: E402
from edge_agent.perception import quality  # noqa: E402
from edge_agent.perception.eye_state import face_brightness  # noqa: E402
from edge_agent.perception.landmarks import FaceLandmarks  # noqa: E402
from edge_agent.perception.preprocess import PreprocessConfig, Preprocessor  # noqa: E402

DEST = ROOT / "frontend" / "src" / "live" / "measure.fixture.json"
WIDTH, HEIGHT = 40, 30
BOX = (11.4, 6.2, 29.3, 25.6)  # a "face" box with fractional corners: both sides floor / ceil it
# How far the page may be from the device on these images: |page - device| <= abs + rel * device
# (0-255 scale; sharpness is a variance). Not zero, because the two do not do the same arithmetic:
#   - the device's luminance is OpenCV's Y, rounded to a whole number per pixel; the page keeps the
#     fraction. A mean moves by a fraction of a level; the Laplacian variance (sharpness) moves with
#     that rounding: measured here 1.0 on the dim image (10.4 on the device, 9.4 on the page, where
#     quality.blur_sharpness is 3) and 1.6 % on the textured one;
#   - the device's scene brightness is the mean of every pixel, the page's of every stride-th one;
#   - an image block 2 takes for infrared is read on its green channel, the page still weighs the
#     three channels (the "dim" image).
TOLERANCE = {
    "channel_diff": {"abs": 1e-6, "rel": 0.0},
    "face_brightness": {"abs": 0.5, "rel": 0.0},
    "scene_brightness": {"abs": 0.5, "rel": 0.0},
    "scene_contrast": {"abs": 0.5, "rel": 0.0},
    "sharpness": {"abs": 2.0, "rel": 0.02},
}


def pattern(gain: float, colour: bool) -> np.ndarray:
    """H x W x 3 RGB uint8: a slow wave with a fine texture on it, tinted unless `colour` is False."""
    y, x = np.mgrid[0:HEIGHT, 0:WIDTH].astype(np.float64)
    base = 110.0 + 70.0 * np.sin(x / 6.0) * np.cos(y / 5.0) + ((x * 31 + y * 17) % 23 - 11)
    tint = (1.15, 1.0, 0.8) if colour else (1.0, 1.0, 1.0)
    rgb = np.stack([base * k for k in tint], axis=-1) * gain
    return np.clip(np.round(rgb), 0, 255).astype(np.uint8)


# name -> image. "dim" is the colour image at a twelfth of the light: audit A1 H1's case.
IMAGES = {
    "colour": pattern(1.0, True),
    "dim": pattern(1.0 / 12.0, True),
    "gray": pattern(0.7, False),
}


def channel_diff(pre: Preprocessor, bgr: np.ndarray) -> float:
    """Block 2's IR test value. `is_ir_image` only says whether it is under the limit, so the limit is
    moved until it flips: the value comes from the device's code, not from a copy of it here."""
    lo, hi = 0.0, 255.0
    for _ in range(60):
        mid = (lo + hi) / 2.0
        # the absolute limit alone: the share of the brightness (M98) is another number of the fixture
        if Preprocessor(replace(pre.config, ir_channel_diff_max=mid, ir_channel_rel_max=0.0)).is_ir_image(bgr):
            hi = mid
        else:
            lo = mid
    return hi


def device_numbers(rgb: np.ndarray, thresholds: dict[str, Any]) -> dict[str, Any]:
    """What blocks 2, 5 and 6 measure on the image, with the box as the face."""
    cfg = PreprocessConfig.from_dict(thresholds["preprocess"])
    pre = Preprocessor(cfg)
    bgr = np.ascontiguousarray(rgb[..., ::-1])
    frame = pre(Frame(image=bgr, frame_id=0, timestamp=0.0))
    points = np.zeros((478, 3), dtype=np.float32)
    points[:, :2] = BOX[:2]
    points[-1, :2] = BOX[2:]
    lm = FaceLandmarks(
        points=points, image_width=WIDTH, image_height=HEIGHT, face_conf=1.0, num_faces=1, frame_id=0, timestamp=0.0
    )
    measured = quality.measure(frame, lm, cfg.sample_stride)
    # Blocks 5 and 6 each take the face's brightness themselves; they must agree before the page is asked to.
    assert abs(measured["face_brightness"] - face_brightness(frame, lm)) < 1e-9
    return {
        "is_ir": bool(frame.is_ir),
        "channel_diff": round(channel_diff(pre, bgr), 6),
        **{k: round(float(v), 6) for k, v in measured.items()},
    }


def fixture(thresholds: dict[str, Any] | None = None) -> dict[str, Any]:
    th = load_thresholds() if thresholds is None else thresholds
    return {
        "width": WIDTH,
        "height": HEIGHT,
        "box": list(BOX),
        "stride": PreprocessConfig.from_dict(th["preprocess"]).sample_stride,
        "ir_channel_diff_max": PreprocessConfig.from_dict(th["preprocess"]).ir_channel_diff_max,
        "ir_channel_rel_max": PreprocessConfig.from_dict(th["preprocess"]).ir_channel_rel_max,
        "tolerance": TOLERANCE,
        "images": {
            name: {"rgb": rgb.reshape(-1).tolist(), "device": device_numbers(rgb, th)} for name, rgb in IMAGES.items()
        },
    }


def render(thresholds: dict[str, Any] | None = None) -> str:
    return json.dumps(fixture(thresholds), separators=(",", ":")) + "\n"


if __name__ == "__main__":
    text = render()
    if "--check" in sys.argv[1:]:
        if not DEST.exists() or DEST.read_text(encoding="utf-8") != text:
            sys.exit(f"{DEST.relative_to(ROOT)} is out of date: run python tools/measure_fixture.py")
        print(f"{DEST.relative_to(ROOT)} matches the device's measurements")
    else:
        DEST.write_text(text, encoding="utf-8")
        print(f"wrote {DEST.relative_to(ROOT)}")
