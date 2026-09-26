"""M7: frame-label matching, AUC and the blocks 7-12 replay of tools/seq_eval.py (fake traces, no model)."""

from collections import Counter

import numpy as np
import pytest

from edge_agent.config import load_thresholds
from tools import seq_eval as se
from tools.seq_eval import Run


def test_label_runs_join_small_gaps_only():
    labels = {0: "alert", 1: "alert", 2: "microsleep", 3: "microsleep", 6: "microsleep", 20: "microsleep"}
    runs = se.label_runs(labels, max_gap=2)
    assert runs == [Run("alert", 0, 1), Run("microsleep", 2, 6), Run("microsleep", 20, 20)]
    assert runs[1].seconds(25) == pytest.approx(5 / 25)


def test_label_at_nearest_within_gap():
    labels = {10: "alert", 20: "microsleep"}
    assert se.label_at(labels, 10, 0) == "alert"
    assert se.label_at(labels, 12, 2) == "alert"
    assert se.label_at(labels, 15, 2) is None  # unlabelled stretch


def test_classify_predictions_hit_false_other():
    labels = (
        {i: "alert" for i in range(0, 50)}
        | {i: "microsleep" for i in range(50, 75)}
        | {i: "yawning" for i in range(100, 150)}
    )
    positive = [Run("microsleep", 50, 74)]
    c = se.classify_predictions([45, 60, 10, 120, 300], positive, labels, tol=5, max_gap=2)
    assert c == Counter({"hit": 2, "fp": 1, "other": 2})  # 45 in tolerance; 120 yawning; 300 unlabelled


def test_detected_delay_and_miss():
    r = Run("microsleep", 100, 150)
    assert se.detected(r, [90, 125, 140], tol=5) == 25
    assert se.detected(r, [95], tol=5) == -5
    assert se.detected(r, [10, 200], tol=5) is None


def test_auc_perfect_chance_and_ties():
    assert se.auc(np.array([2.0, 3.0]), np.array([0.0, 1.0])) == 1.0
    assert se.auc(np.array([0.0, 1.0]), np.array([2.0, 3.0])) == 0.0
    assert se.auc(np.array([1.0, 1.0]), np.array([1.0, 1.0])) == 0.5
    assert se.auc(np.array([np.nan, 2.0]), np.array([1.0])) == 1.0  # NaN dropped
    assert se.auc(np.array([]), np.array([1.0])) is None


def test_prf_counts():
    m = se.prf(np.array([True, True, False, False]), np.array([True, False, True, False]))
    assert (m["tp"], m["fp"], m["fn"], m["tn"]) == (1, 1, 1, 1)
    assert m["precision"] == m["recall"] == m["fpr"] == 0.5


def test_set_threshold_parses_and_rejects_unknown():
    th = load_thresholds()
    se.set_threshold(th, "drowsiness.microsleep_mask.talk_swing=0.12")
    assert th["drowsiness"]["microsleep_mask"]["talk_swing"] == 0.12
    with pytest.raises(KeyError):
        se.set_threshold(th, "drowsiness.eye.not_a_key=1")


def fake_trace(ear: list[float], fps: float = 25.0, p_closed: list[float] | None = None) -> dict:
    n = len(ear)
    nan = np.full(n, np.nan)
    cols = {c: nan.copy() for c in se.COLUMNS}
    cols |= {
        "t": np.arange(n) / fps,
        "face": np.ones(n),
        "reliable": np.ones(n),
        "ear": np.array(ear),
        "mar": np.full(n, 0.05),
        "pitch": np.zeros(n),
        "yaw": np.zeros(n),
        "p_closed": nan.copy() if p_closed is None else np.array(p_closed),
        "p_cnn": nan.copy() if p_closed is None else np.array(p_closed),
    }
    return {"fps": fps, "n": n, "cols": cols, "events": [], "alerts": []}


def test_replay_ear_microsleep_reaches_l3():
    # 12 s eyes open (EAR 0.30), then 2 s firmly shut (EAR 0.08): microsleep event and L3
    fps = 25
    ear = [0.30] * (12 * fps) + [0.08] * (2 * fps) + [0.30] * fps
    out = se.replay(fake_trace(ear, fps), load_thresholds(), eye="ear")
    assert any(e == "microsleep" for _, e in out["events"])
    assert max(lv for _, lv, _ in out["alerts"]) == 3


def test_replay_eye_source_switch():
    # EAR says open all along, the CNN says closed for 2 s: only the "cnn" replay sees it
    fps = 25
    n = 15 * fps
    p = [0.05] * (12 * fps) + [0.95] * (2 * fps) + [0.05] * fps
    tr = fake_trace([0.30] * n, fps, p)
    th = load_thresholds()
    assert not any(e == "microsleep" for _, e in se.replay(tr, th, eye="ear")["events"])
    assert any(e == "microsleep" for _, e in se.replay(tr, th, eye="cnn")["events"])
