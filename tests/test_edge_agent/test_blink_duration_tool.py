"""M35: the offline blink-duration prototype (tools/blink_duration.py). Fake sequences, no video, no dataset."""

import numpy as np
import pytest

from edge_agent.config import load_thresholds
from tools import blink_duration as bd
from tools.seq_eval import Run

FPS = 25


def aperture_with_dips(dips, seconds=10.0, fps=FPS):
    """Open eyes (1.0) with V-shaped dips: (start s, duration s, depth)."""
    t = np.arange(round(seconds * fps)) / fps
    a = np.ones_like(t)
    for start, duration, depth in dips:
        mid = start + duration / 2
        inside = (t >= start) & (t <= start + duration)
        a[inside] = depth + (1 - depth) * np.abs(t[inside] - mid) / (duration / 2)
    return t, a


def test_dip_duration_is_interpolated_between_frames():
    t, a = aperture_with_dips([(2.0, 0.4, 0.0)])
    (blink,) = bd.time_excursions(t, a, level=0.8, depth=0.5, max_s=1.5)
    # a V from 1 to 0 and back in 0.4 s is below 0.8 for 0.32 s: within a frame (40 ms) of the truth
    assert blink.duration == pytest.approx(0.32, abs=0.02)
    assert t[blink.frame] == pytest.approx(2.2, abs=0.04)


def test_shallow_dips_and_long_closures_are_not_blinks():
    t, a = aperture_with_dips([(1.0, 0.3, 0.7), (3.0, 0.3, 0.1), (5.0, 3.0, 0.0)])
    blinks = bd.time_excursions(t, a, level=0.8, depth=0.5, max_s=1.5)
    assert [round(t[b.frame]) for b in blinks] == [3]  # squint (0.7) and the 3 s closure are left out


def test_a_dip_touching_a_gap_or_the_end_is_not_measured():
    t, a = aperture_with_dips([(1.0, 0.4, 0.0), (9.8, 0.4, 0.0)])
    a[28:30] = np.nan  # the eye is not known while the first dip reopens
    assert bd.time_excursions(t, a, level=0.8, depth=0.5, max_s=1.5) == []


def test_ear_aperture_matches_block_7_when_not_enrolled():
    c = {"ear": np.array([0.30, 0.105, 0.2025]), "ear_base": np.full(3, 0.30)}
    assert bd.ear_aperture(c, closed_ref_ratio=0.35) == pytest.approx([1.0, 0.0, 0.5])


def test_blendshape_aperture_needs_a_real_closure():
    assert bd.blendshape_aperture(np.full(100, 0.05)) is None  # never closed: nothing to scale with
    blink = np.full(1000, 0.05)
    blink[100:110] = 0.9
    ap = bd.blendshape_aperture(blink)
    assert ap[0] == pytest.approx(1.0) and ap[105] == pytest.approx(0.0)


def test_near_and_far_from_a_microsleep():
    runs = [Run("microsleep", 500, 600)]
    blinks = [bd.Blink(f, 0.3) for f in (100, 260, 550, 840, 900)]
    near, far = bd.split_near_far(blinks, runs, fps=FPS, near_s=10.0)
    assert [b.frame for b in near] == [260, 550, 840] and [b.frame for b in far] == [100, 900]
    assert bd.seconds_to_nearest(550, runs, FPS) == 0


def test_microsleep_runs_ignore_other_labels():
    labels = {i: "alert" for i in range(50)} | {i: "microsleep" for i in range(50, 80)} | {90: "yawning"}
    assert bd.microsleep_runs(labels) == [Run("microsleep", 50, 79)]


def test_spearman_is_a_rank_correlation():
    x = np.array([1.0, 2.0, 3.0, 4.0])
    assert bd.spearman(x, x**3) == pytest.approx(1.0)
    assert bd.spearman(x, -x) == pytest.approx(-1.0)
    assert bd.spearman(x, np.ones(4)) is None and bd.spearman(x[:2], x[:2]) is None


def test_engine_blinks_come_from_block_7_on_a_fake_trace():
    """A trace of open eyes with three clean blinks: block 7 times them, duration >= reopening."""
    t, a = aperture_with_dips([(8.0, 0.24, 0.0), (12.0, 0.24, 0.0), (16.0, 0.24, 0.0)], seconds=20.0)
    n, base = len(t), 0.30
    ear = (0.35 + 0.65 * a) * base
    nan = np.full(n, np.nan)
    cols = {
        "t": t, "face": np.ones(n), "reliable": np.ones(n), "ear": ear, "ear_base": np.full(n, base),
        "mar": np.full(n, 0.05), "pitch": np.zeros(n), "yaw": np.zeros(n), "p_closed": nan, "p_cnn": nan,
        "ear_l": ear, "ear_r": ear, "face_bright": np.full(n, 140.0), "is_ir": np.zeros(n),
        "blink": 0.05 + 0.85 * (1 - a),
    }  # fmt: skip
    blinks = bd.engine_blinks({"fps": float(FPS), "n": n, "cols": cols, "events": [], "alerts": []}, load_thresholds())
    assert len(blinks) == 3
    assert all(b.reopen is not None and 0 < b.reopen <= b.duration < 0.5 for b in blinks)
