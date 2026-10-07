"""tools/light_study.py (M46): the transforms are pure and in RAM, the report rows come from traces."""

from pathlib import Path

import numpy as np

from edge_agent.config import load_thresholds
from tools import light_study as ls
from tools.metrics import EvalConfig
from tools.seq_eval import COLUMNS

RNG = np.random.default_rng(0)
IMAGE = RNG.integers(0, 256, (48, 64, 3), dtype=np.uint8)


def test_gamma_darkens_and_keeps_black_and_white():
    out = ls.gamma(IMAGE, 2.2)
    assert out.dtype == np.uint8 and out.shape == IMAGE.shape and out.mean() < IMAGE.mean()
    ends = np.array([[[0, 255, 128]]], np.uint8)
    assert ls.gamma(ends, 3.5)[0, 0, 0] == 0 and ls.gamma(ends, 3.5)[0, 0, 1] == 255
    assert np.array_equal(ls.gamma(IMAGE, 1.0), IMAGE)


def test_gain_brightens_and_clips():
    out = ls.gain(IMAGE, 4.0)
    assert out.max() == 255 and out.mean() > IMAGE.mean() and out.dtype == np.uint8
    assert (out == 255).mean() > 0.5  # most pixels are washed out


def test_grey_has_three_equal_channels_so_block_2_calls_it_infrared():
    out = ls.grey(IMAGE)
    assert out.shape == IMAGE.shape and np.array_equal(out[..., 0], out[..., 1])
    from edge_agent.perception import PreprocessConfig, Preprocessor

    pre = Preprocessor(PreprocessConfig.from_dict(load_thresholds()["preprocess"]))
    assert pre.is_ir_image(out) and not pre.is_ir_image(IMAGE)


def test_blur_lowers_the_sharpness_block_6_measures():
    from edge_agent.perception.quality import laplacian_variance

    sharp = laplacian_variance(IMAGE[..., 1])
    assert laplacian_variance(ls.blur(IMAGE, 1.5, reference_width=64)[..., 1]) < 0.2 * sharp
    assert laplacian_variance(ls.blur(IMAGE, 1.5)[..., 1]) > 0.9 * sharp  # 64 px wide: a tenth of the sigma
    wide = np.repeat(np.repeat(IMAGE, 2, axis=0), 2, axis=1)  # twice the width: sigma scales with it
    assert ls.blur(wide, 3.0, reference_width=64).shape == wide.shape


def test_no_transform_writes_or_keeps_the_input():
    before = IMAGE.copy()
    for kind, value in ls.transforms(EvalConfig()).values():
        out = ls.apply(IMAGE, kind, value)
        assert out is IMAGE or not np.shares_memory(out, IMAGE) or kind == "none"
    assert np.array_equal(IMAGE, before)


def test_plan_comes_from_thresholds_and_starts_with_the_original():
    cfg = EvalConfig.from_dict(load_thresholds()["eval"])
    plan = ls.transforms(cfg)
    assert next(iter(plan)) == ls.ORIGINAL and plan["grey"] == ("grey", 0.0)
    assert len(plan) == 2 + len(cfg.light_gammas) + len(cfg.light_gains) + len(cfg.light_blur_sigmas)
    assert plan["gamma 2.2"] == ("gamma", 2.2) and plan["blur 3"] == ("blur", 3.0)


def test_pick_spaces_the_videos_and_balances_yawdd():
    videos = {f"v{i:02d}": Path(f"v{i:02d}.mp4") for i in range(20)}
    assert list(ls.pick(videos, 4, "fl3d")) == ["v00", "v05", "v10", "v15"]
    assert ls.pick(videos, None, "fl3d") is videos and ls.pick(videos, 50, "fl3d") is videos
    yaw = {f"m/{i}-MaleNoGlasses-{a}.avi": Path("x") for i in range(6) for a in ("Yawning", "Normal", "Talking")}
    chosen = list(ls.pick(yaw, 4, "yawdd"))
    assert len(chosen) == 4 and sum("Yawning" in k for k in chosen) == 2


def fake_trace(n=300, fps=30.0, **cols):
    c = {name: np.full(n, np.nan) for name in COLUMNS}
    c["face"][:] = 1
    c["eye_closed"][:] = 0
    c["unavailable"][:] = 0
    c["no_face_s"][:] = 0
    c["level"][:] = 0
    for name, value in cols.items():
        c[name][:] = value
    return {"fps": fps, "n": n, "cols": c, "events": [], "alerts": []}


def test_summary_row_and_table_from_traces():
    th = load_thresholds()
    key_yawn, key_normal = "m/1-MaleNoGlasses-Yawning.avi", "m/1-MaleNoGlasses-Normal.avi"
    good = {
        key_yawn: fake_trace(face_bright=120, sharpness=200),
        key_normal: fake_trace(face_bright=110, sharpness=180),
    }
    good[key_yawn]["events"] = [(40, "yawn")]
    dark = {key_yawn: fake_trace(face_bright=10, sharpness=3, unavailable=1), key_normal: fake_trace(face_bright=12)}
    dark[key_yawn]["unavailable_reasons"] = {"low_light": 300}
    dark[key_normal]["alerts"] = [(100, 3, ("microsleep",))]
    row = ls.summarise("yawdd", good, th)
    assert row["videos"] == 2 and row["pos"] == 1 and row["pos_hit"] == 1 and row["false_alerts"] == 0
    assert row["bright"] == 115 and row["unavailable"] == 0 and row["reasons"] == {}
    bad = ls.summarise("yawdd", dark, th)
    assert bad["pos_hit"] == 0 and bad["false_alerts"] == 1 and bad["unavailable"] == 0.5
    assert bad["reasons"] == {"low_light": 0.5}
    lines = ls.table("yawdd", {"original": row, "gamma 5": bad}, ["original", "gamma 5", "grey"])
    assert len(lines) == 4 and "low_light 50.0%" in lines[3] and "1/1 (100.0%)" in lines[2] and "[1]" in lines[3]
    text = ls.report({"yawdd": {"original": good, "gamma 5": dark}}, th, ["original", "gamma 5"])
    assert "## yawdd" in text and "No image is written" in text and "2 videos" in text
