"""tools/metrics.py: confidence intervals, exposure time, window FAR / MAR. Fake numbers only."""

import pytest

from tools.metrics import (
    EvalConfig,
    WindowCounts,
    ci_text,
    exposure_seconds,
    per_second_max,
    poisson_ci,
    rate_ci,
    union_length,
    wilson_ci,
    window_scores,
)


@pytest.mark.parametrize(
    ("k", "lo", "hi"),
    [(0, 0.0, 3.689), (1, 0.0253, 5.572), (3, 0.6187, 8.767), (10, 4.795, 18.39)],  # Garwood tables
)
def test_exact_poisson_ci(k, lo, hi):
    assert poisson_ci(k) == pytest.approx((lo, hi), abs=2e-3)


def test_rate_ci_matches_the_fl3d_example():
    rate, lo, hi = rate_ci(1, 26 / 60)  # 1 false alarm on 26 min (docs/improvements.md)
    assert (rate, lo, hi) == pytest.approx((2.31, 0.058, 12.86), abs=0.01)
    assert rate_ci(3, 0.0) == (None, None, None)
    assert ci_text((rate, lo, hi)) == "2.3 (0.06–12.9)"


def test_wilson_ci():
    assert wilson_ci(2, 50) == pytest.approx((0.04, 0.0110, 0.1346), abs=1e-4)
    assert wilson_ci(0, 0) == (None, None, None)
    assert wilson_ci(0, 10)[1] == 0.0


def test_union_and_exposure():
    assert union_length([(0, 10), (5, 15), (20, 25)], 0, 100) == 20
    assert union_length([(-5, 3), (98, 120)], 0, 100) == 5
    assert exposure_seconds(100, [(-1, 11), (50, 61)]) == 100 - 11 - 11


def test_per_second_max():
    assert per_second_max([0.1, 0.5, 1.2, 2.9], [0, 2, 1, 3], 3.0) == [2, 1, 3]


def test_windows_skip_warmup_and_borders():
    cfg = EvalConfig(window_s=10, warmup_s=30, positive_frac=0.5, min_level=1)
    c = window_scores(65.0, [], [(0, 65)], [0] * 65, cfg)
    assert (c.awake, c.skipped, c.warmup_s) == (3, 0, 30)  # 30-40, 40-50, 50-60; 60-65 too short
    short = window_scores(10.0, [], [(0, 10)], [1] * 10, cfg)  # a 10 s clip: nothing after start-up
    assert (short.awake, short.drowsy) == (0, 0)


def test_unlabelled_time_is_not_awake():
    cfg = EvalConfig(window_s=10, warmup_s=0, positive_frac=0.5, min_level=1)
    c = window_scores(40.0, [(10, 20)], [(0, 5), (30, 40)], [1] * 40, cfg)
    # 0-10 only 5 s known awake... and touches nothing -> awake (5 ≥ 5); 10-20 drowsy; 20-30 unlabelled; 30-40 awake
    assert (c.awake, c.drowsy, c.skipped) == (2, 1, 1)


def test_counts_add_up():
    a = WindowCounts(1, 10, 2, 5, 3, 30.0)
    a += WindowCounts(0, 5, 1, 5, 0, 30.0)
    assert (a.false_alarms, a.awake, a.misses, a.drowsy, a.skipped, a.warmup_s) == (1, 15, 3, 10, 3, 60.0)
    assert a.far[0] == pytest.approx(1 / 15) and a.mar[0] == pytest.approx(0.3)


def test_seq_eval_scores_yawdd_traces_like_the_dataset_tool():
    import numpy as np

    from edge_agent.config import load_thresholds
    from tools.seq_eval import yawdd_report

    def trace(n, events=(), alerts=(), drowsy=0):
        t = np.arange(n) / 10.0
        lv = np.full(n, float(drowsy))
        cols = {"t": t, "level": lv, "drowsy_level": lv, "distraction_level": np.zeros(n)}
        return {"n": n, "fps": 10.0, "cols": cols, "events": list(events), "alerts": list(alerts)}

    traces = {
        "Female_mirror/1-FemaleNoGlasses-Yawning.avi": trace(600, events=[(50, "yawn")]),  # 60 s, one yawn: hit
        "Female_mirror/1-FemaleNoGlasses-Normal.avi": trace(600, alerts=[(400, 2, ("off_road",))]),  # false alert
        "Female_mirror/1-FemaleNoGlasses-Other.avi": trace(100),  # not a class of the preset: skipped
    }
    text = yawdd_report(traces, load_thresholds())
    assert "2 videos, 2.0 min" in text
    assert "| yawn | 1 | 1 | 1 | 0 |" in text
    assert "| **all alerts** | 1 | 1 | 0 | 1 | 0 | 0.0% | – | – | 0.02 | 60.0 (" in text  # 1 per the 1-min Normal clip
    assert "| Drowsiness, level ≥ L1 | 3 | 0.0%" in text and "| 3 | 100.0%" in text  # Yawning clip: 3 windows missed
