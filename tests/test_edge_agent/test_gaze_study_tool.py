"""tools/gaze_study.py: the pure parts (frame order, action intervals, per-driver reference)."""

import numpy as np

from tools import gaze_study as gs


def test_frames_come_in_recording_order(tmp_path):
    for n in (1, 2, 10, 100):
        (tmp_path / f"RGB2_SUB5ACT1F{n}.jpg").write_bytes(b"")
    (tmp_path / "notes.txt").write_text("x")
    assert [p.name for p in gs.frames_of(tmp_path)] == [f"RGB2_SUB5ACT1F{n}.jpg" for n in (1, 2, 10, 100)]


def fake_trace(n=300, fps=30.0):
    t = np.arange(n) / fps
    cols = {k: np.zeros(n) for k in ("ear", "blink", "look_down_l", "look_down_r", "iris_x_l", "iris_x_r")}
    cols |= {k: np.zeros(n) for k in ("pitch", "yaw", "eye_closed", "off_road", "phone_flag")}
    cols |= {"t": t, "face": np.ones(n), "iris_y_l": np.full(n, -0.07), "iris_y_r": np.full(n, -0.07)}
    cols["ear"][:] = 0.30
    cols["iris_y_l"][150:] = cols["iris_y_r"][150:] = 0.01  # the eyes drop in the second action
    cols["pitch"][150:] = 6.0
    return {"fps": fps, "n": n, "cols": cols, "labels": [("AC1", 0.0, 149 / fps), ("AC5", 150 / fps, 299 / fps)]}


def test_action_mask_covers_exactly_the_labelled_frames():
    tr = fake_trace()
    assert gs.action_mask(tr, 1).sum() == 150 and gs.action_mask(tr, 5).sum() == 150
    assert not gs.action_mask(tr, 12).any()


def test_signals_are_taken_against_the_drivers_own_safe_driving():
    f = gs.driver_frame(fake_trace())
    safe, text = gs.action_mask(fake_trace(), 1), gs.action_mask(fake_trace(), 5)
    assert np.allclose(f["iris_y"][safe], 0.0) and np.allclose(f["iris_y"][text], 0.08)
    assert np.allclose(f["pitch"][text], 6.0) and np.allclose(f["ear_ratio"], 1.0)


def test_a_driver_without_safe_driving_frames_is_left_out():
    tr = fake_trace()
    tr["labels"] = [("AC5", 0.0, 10.0)]
    assert gs.driver_frame(tr) is None
