"""M7: event matching / metrics of tools/eval.py and statistics of tools/benchmark.py (no video)."""

import json

import pytest

from edge_agent.config import load_thresholds
from edge_agent.context.can_sim import CanSimulator, scenario_from_dict
from edge_agent.decision.pipeline import DecisionPipeline
from edge_agent.perception.features import FrameFeatures
from edge_agent.perception.phone_detector import PhoneDetection
from tools import benchmark
from tools import eval as ev
from tools.eval import ALERT, Episode, Prediction


def by_behavior(scores):
    return {s.behavior: s for s in scores}


# ---------------------------------------------------------------- matching


def test_match_tp_fp_duplicates_and_delay():
    eps = [Episode("v", "yawn", 10, 14), Episode("v", "yawn", 30, 33)]
    tp, fp, dup, delays = ev.match(eps, [11.5, 12.0, 20.0, 29.5], tolerance_s=1.0)
    assert (tp, fp, dup) == (2, 1, 1)  # 12.0 duplicates the first episode, 20.0 is outside
    assert delays == [1.5, -0.5]  # 29.5 is inside the tolerance before the start


def test_tolerance_edges():
    eps = [Episode("v", "nod", 10, 11)]
    assert ev.match(eps, [8.9], 1.0)[:2] == (0, 1)
    assert ev.match(eps, [9.0], 1.0)[:2] == (1, 0)
    assert ev.match(eps, [12.0], 1.0)[:2] == (1, 0)


def test_score_metrics_and_fp_per_hour():
    eps = [Episode("a", "phone", 10, 20), Episode("a", "phone", 100, 110), Episode("b", "yawn", 5, 9)]
    preds = [
        Prediction("a", "phone", 12, 2),  # TP
        Prediction("a", "phone", 300, 2),  # FP
        Prediction("b", "phone", 50, 2),  # FP in the other video
        Prediction("b", "yawn", 6),  # TP
        Prediction("a", ALERT, 12, 2),  # alert on a labelled episode
        Prediction("b", ALERT, 50, 2),  # alert outside every episode
    ]
    s = by_behavior(ev.score(eps, preds, {"a": 1800.0, "b": 1800.0}))  # 1 hour in total
    phone = s["phone"]
    assert (phone.tp, phone.fp, phone.episodes) == (1, 2, 2)
    assert phone.precision == pytest.approx(1 / 3) and phone.recall == pytest.approx(0.5)
    assert phone.f1 == pytest.approx(2 * (1 / 3) * 0.5 / (1 / 3 + 0.5))
    # false positives per hour over the time where one can happen: 1 h minus the 2 phone episodes ± 1 s
    assert phone.exposure_h == pytest.approx((3600 - 24) / 3600)
    assert phone.fp_per_hour == pytest.approx(2 / ((3600 - 24) / 3600))
    assert phone.fp_ci_low == pytest.approx(0.2422 / phone.exposure_h, rel=1e-3)  # exact Poisson, k = 2
    assert phone.fp_ci_high == pytest.approx(7.2247 / phone.exposure_h, rel=1e-3)
    assert s["yawn"].precision == 1.0 and s["yawn"].recall == 1.0 and s["yawn"].fp_per_hour == 0.0
    assert s["nod"].precision is None and s["nod"].recall is None  # nothing labelled, nothing predicted
    alert = s[ALERT]
    assert (alert.tp, alert.fp) == (1, 1) and alert.recall is None
    assert alert.exposure_h == pytest.approx((3600 - 24 - 6) / 3600)  # every episode ± 1 s left out
    assert s[f"{ALERT} L2"].fp == 1 and s[f"{ALERT} L1"].predictions == 0


def test_negative_clip_counts_driving_time():
    s = by_behavior(ev.score([], [Prediction("neg", "phone", 3, 2)], {"neg": 7200.0}))
    assert s["phone"].fp == 1 and s["phone"].fp_per_hour == pytest.approx(0.5)
    assert s["phone"].precision == 0.0


def test_report_is_markdown():
    text = ev.report(ev.score([], [], {"v": 60.0}), {"v": 60.0}, 1.0)
    assert "| microsleep |" in text and "**all alerts**" in text and "**all alerts L3**" in text
    assert "95% CI" in text


def test_window_far_mar_from_recorded_levels():
    from tools.metrics import EvalConfig

    cfg = EvalConfig(window_s=10, warmup_s=30, positive_frac=0.5, min_level=1)
    eps = [Episode("v", "microsleep", 60.0, 80.0)]
    drowsy = [0] * 120
    for sec in (45, 62, 63):  # one false call while awake, the episode's first window caught
        drowsy[sec] = 1
    levels = {"v": {"drowsy": drowsy, "distraction": [0] * 120}}
    rows = dict(ev.window_rows(eps, {"v": 120.0}, levels, cfg, tolerance_s=1.0))
    d = rows["Drowsiness, level ≥ L1"]
    # windows from 30 s: 30-40, 40-50 awake (1 false), 50-60 touches the widened episode -> skipped,
    # 60-70, 70-80 drowsy (70-80 missed), 80-90 skipped, 90-100, 100-110, 110-120 awake
    assert (d.awake, d.false_alarms, d.drowsy, d.misses, d.skipped) == (5, 1, 2, 1, 2)
    assert rows["Drowsiness, level ≥ L2"].misses == 2
    assert rows["Distraction, level ≥ L1"].drowsy == 0  # no distraction label: awake windows only
    text = ev.report(ev.score(eps, [], {"v": 120.0}), {"v": 120.0}, 1.0, list(rows.items()), cfg)
    assert "## FAR / MAR on windows" in text and "| Drowsiness, level ≥ L1 | 5 | 20.0%" in text


# ---------------------------------------------------------------- files


def test_read_labels(tmp_path):
    p = tmp_path / "labels.csv"
    p.write_text("video,behavior,start_s,end_s\na.mp4,yawn,1,4\nb.mp4,none,,\na.mp4,phone,10,12\n", encoding="utf-8")
    episodes, videos = ev.read_labels(p)
    assert videos == ["a.mp4", "b.mp4"]
    assert [e.behavior for e in episodes] == ["yawn", "phone"]
    p.write_text("video,behavior,start_s,end_s\na.mp4,sleepy,1,4\n", encoding="utf-8")
    with pytest.raises(ValueError):
        ev.read_labels(p)


def test_frames_to_episodes():
    eps = ev.frames_to_episodes("0011100022\n20", fps=10, mapping={"1": "yawn", "2": "off_road"}, video="v")
    assert [(e.behavior, e.start_s, e.end_s) for e in eps] == [("yawn", 0.2, 0.5), ("off_road", 0.8, 1.1)]
    assert ev.frames_to_episodes("0110", 10, {"1": "yawn"}, "v", min_s=0.5) == []


def test_score_cli_roundtrip(tmp_path, capsys):
    labels = tmp_path / "labels.csv"
    labels.write_text("video,behavior,start_s,end_s\nv.mp4,microsleep,10,12\n", encoding="utf-8")
    preds = tmp_path / "p.json"
    ev.save_predictions(preds, [Prediction("v.mp4", "microsleep", 11.0)], {"v.mp4": 120.0})
    out, js = tmp_path / "r.md", tmp_path / "r.json"
    assert (
        ev.main(["score", "--labels", str(labels), "--predictions", str(preds), "--out", str(out), "--json", str(js)])
        == 0
    )
    assert "| microsleep | 1 | 1 | 1 | 0 |" in out.read_text(encoding="utf-8")
    assert json.loads(js.read_text(encoding="utf-8"))[0]["recall"] == 1.0


# ---------------------------------------------------------------- predictions from the real decision chain


def test_decision_chain_predictions_are_scored():
    """Fake 30 FPS sequence: phone 5-12 s, eyes closed 20-22 s, yawn 30-34 s -> each detected once."""
    pipeline = DecisionPipeline(load_thresholds())
    can = CanSimulator(scenario_from_dict({"start_clock": "15:00", "timeline": [{"t": 0, "speed_kmh": 60}]}))
    preds = []
    for i in range(40 * 30):
        t = i / 30
        ear = 0.08 if 20 <= t < 22 else 0.30
        mar = 0.8 if 30 <= t < 34 else 0.05
        f = FrameFeatures(i, t, True, 1.0, ear=ear, mar=mar, pitch=0.0, yaw=0.0, roll=0.0)
        preds += ev.predictions_from_result("clip", t, pipeline.step(f, 5 <= t < 12, can.sample(t)))
    labels = [Episode("clip", "phone", 5, 12), Episode("clip", "microsleep", 20, 22), Episode("clip", "yawn", 30, 34)]
    s = by_behavior(ev.score(labels, preds, {"clip": 40.0}))
    for b in ("phone", "microsleep", "yawn"):
        assert (s[b].tp, s[b].fp) == (1, 0), b
    assert s[ALERT].fp == 0 and s[ALERT].tp >= 2  # phone L2 and microsleep L3 alerts


# ---------------------------------------------------------------- benchmark helpers


def test_summarize():
    s = benchmark.summarize([10.0] * 95 + [50.0] * 5)
    assert s["n"] == 100 and s["p50_ms"] == 10.0 and s["max_ms"] == 50.0
    assert s["p95_ms"] == pytest.approx(10.0 + 0.05 * 40, abs=2.1)
    assert s["fps"] == pytest.approx(1000 / 12.0)


def det(x):
    return PhoneDetection((x, 0.0, x + 10.0, 10.0), 0.9)


def test_iou_and_agreement():
    assert benchmark.iou((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0
    assert benchmark.iou((0, 0, 10, 10), (20, 20, 30, 30)) == 0.0
    ref = [(det(0),), (det(0), det(50)), ()]
    other = [(det(1),), (det(50),), (det(90),)]
    assert benchmark.agreement(ref, other) == (2, 1, 1)


def test_time_calls_skips_warmup():
    ms, outs = benchmark.time_calls(lambda x: x * 2, [1, 2, 3, 4], warmup=1)
    assert outs == [2, 4, 6, 8] and len(ms) == 3
