"""M40: offline studies on traces (tools/trace_studies.py), the P80 PERCLOS measured next to the
current one (block 7), and the per-person / start-up tables of tools/eval.py. Fake numbers only."""

import numpy as np
import pytest

from edge_agent.analysis.drowsiness import DrowsinessAnalyzer, DrowsinessConfig
from edge_agent.config import load_thresholds
from edge_agent.perception.features import FrameFeatures
from tests.test_edge_agent.test_seq_eval_tool import fake_trace
from tools import eval as ev
from tools import seq_eval as se
from tools import trace_studies as ts
from tools.eval import Episode, Prediction
from tools.metrics import EvalConfig

FPS = 25
BASE = 0.28  # drowsiness.eye.baseline_init: the open-eye baseline of a short fake clip


def clip(ratios, seconds_each=4.0, **cols):
    """A replayed fake clip whose EAR is `ratio` x the baseline, one stretch per ratio."""
    ear = [r * BASE for r in ratios for _ in range(round(seconds_each * FPS))]
    tr = fake_trace(ear, FPS)
    for name, values in cols.items():
        tr["cols"][name] = np.asarray(values, dtype=float)
    return se.replay(tr, load_thresholds(), eye="trace")


# ---------------------------------------------------------------- block 7: P80 next to the current PERCLOS


def run_block7(ratios, seconds_each=20.0):
    a = DrowsinessAnalyzer(DrowsinessConfig())
    state, events, i = None, [], 0
    for r in ratios:
        for _ in range(round(seconds_each * FPS)):
            t = i / FPS
            state = a.update(FrameFeatures(i, t, True, 1.0, ear=r * BASE, mar=0.05, pitch=0.0, yaw=0.0, roll=0.0))
            events += state.events
            i += 1
    return state, events


def test_narrowed_eyes_count_for_the_current_perclos_but_not_for_p80():
    """EAR at 0.6 x baseline: below perclos_close_ratio (0.65), an opening of ~38 %: not P80."""
    state, _ = run_block7([1.0, 0.6])
    assert state.perclos_60s == pytest.approx(0.5, abs=0.02)
    assert state.perclos_p80_60s == 0.0
    assert state.perclos_p80_coverage_s == pytest.approx(state.perclos_coverage_s, abs=0.1)


def test_shut_eyes_count_for_both():
    state, _ = run_block7([1.0, 0.3])
    assert state.perclos_60s == pytest.approx(0.5, abs=0.02)
    assert state.perclos_p80_60s == pytest.approx(0.5, abs=0.02)


def test_p80_is_measured_only():
    """The same eyes with and without the P80 measurement in play raise the same events."""
    _, events = run_block7([1.0, 0.3])
    assert events.count("perclos_high") == 1  # from the current definition; P80 adds none
    cfg = DrowsinessConfig(perclos_p80_aperture=0.99)  # a setting under which P80 calls open eyes closed
    a = DrowsinessAnalyzer(cfg)
    events = []
    for i in range(40 * FPS):  # until the baseline is learnt (10 s), EAR 0.9 x the initial one is "closed" for it
        s = a.update(FrameFeatures(i, i / FPS, True, 1.0, ear=0.9 * BASE, mar=0.05, pitch=0.0, yaw=0.0, roll=0.0))
        events += s.events
    assert s.perclos_p80_60s > cfg.perclos_drowsy and s.perclos_60s == 0.0
    assert "perclos_high" not in events  # above the event threshold, and still no event


def test_cnn_frames_are_unknown_to_p80():
    a = DrowsinessAnalyzer(DrowsinessConfig())
    for i in range(20 * FPS):
        f = FrameFeatures(i, i / FPS, True, 1.0, ear=0.3 * BASE, mar=0.05, pitch=0.0, yaw=0.0, roll=0.0, p_closed=0.9)
        s = a.update(f)
    assert s.perclos_60s > 0.9  # block 5 said closed
    assert s.perclos_p80_coverage_s == 0.0 and s.perclos_p80_60s == 0.0  # a probability is not an opening


# ---------------------------------------------------------------- helpers


def test_run_filter_drops_short_runs():
    flags = np.array([1, 1, 0, 1, 1, 1, 1, 0, 1], dtype=bool)
    assert list(ts.run_filter(flags, 3)) == [False, False, False, True, True, True, True, False, False]
    assert list(ts.run_filter(flags, 1)) == list(flags)


def test_brightness_bins():
    edges = [60, 100, 140]
    assert [ts.brightness_bin(v, edges) for v in (10, 60, 99.9, 120, 140, 250)] == [
        "< 60",
        "60–100",
        "60–100",
        "100–140",
        "≥ 140",
        "≥ 140",
    ]
    assert ts.brightness_bin(float("nan"), edges) == "unknown"
    assert ts.bin_order(edges) == ["< 60", "60–100", "100–140", "≥ 140", "unknown"]
    assert tuple(EvalConfig.from_dict(load_thresholds()["eval"]).brightness_bins) == (60, 100, 140)


def test_yawdd_names_give_person_eyewear_and_action():
    m = se.yawdd_meta("Mirror/Male_mirror Avi Videos/13-MaleGlasses-Yawning.avi")
    assert m == {"subject": "M13-glasses", "eyewear": "glasses", "action": "yawning"}
    assert se.yawdd_meta("Mirror/Female_mirror/7-FemaleSunGlasses-Talking.avi")["eyewear"] == "sunglasses"
    assert se.yawdd_meta("x/2-FemaleNoGlasses-TalkingYawning.avi")["action"] == "yawning"
    assert se.yawdd_meta("x/6-MaleGlassesBeard-Normal.avi") == {
        "subject": "M6-glasses",
        "eyewear": "glasses",
        "action": "normal",
    }
    assert se.yawdd_meta("drowsiness/d_1.mp4") is None
    assert ts.is_negative("yawdd", "x/2-FemaleNoGlasses-Talking.avi") is True
    assert ts.is_negative("sust", "drowsiness/d_1.mp4") is False
    assert ts.is_negative("fl3d", "P1042751") is None


# ---------------------------------------------------------------- PERCLOS definitions on a trace


def test_closed_masks_tell_the_definitions_apart():
    th = load_thresholds()
    tr = clip([1.0, 0.6, 0.4, 1.0])
    m = ts.closed_masks(tr, th)
    n = 4 * FPS
    narrowed, shut = slice(n + 5, 2 * n - 5), slice(2 * n + 5, 3 * n - 5)
    assert m["p50_ear"][narrowed].all() and not m["p80"][narrowed].any()  # 0.6 x: P50 only
    assert m["p50_ear"][shut].all() and m["p80"][shut].all()  # 0.4 x: below 0.48 x too
    f = ts.clip_fractions(tr, th)
    assert f["p50_ear"] == pytest.approx(0.5, abs=0.03) and f["p80"] == pytest.approx(0.25, abs=0.03)
    assert f["cnn_share"] == 0.0


def test_p80_without_blinks_keeps_long_closures_only():
    th = load_thresholds()
    blink = round(0.2 * FPS)
    ratios = [1.0] * (5 * FPS) + [0.3] * blink + [1.0] * (5 * FPS) + [0.3] * (2 * FPS) + [1.0] * (5 * FPS)
    tr = se.replay(fake_trace([r * BASE for r in ratios], FPS), th, eye="trace")
    m = ts.closed_masks(tr, th)
    assert m["p80"].sum() == blink + 2 * FPS
    assert m["p80_noblink"].sum() == 2 * FPS


def test_cnn_frames_count_for_the_current_definition_only():
    th = load_thresholds()
    n = 8 * FPS
    tr = fake_trace([0.3 * BASE] * n, FPS, p_closed=[0.9] * n)
    m = ts.closed_masks(se.replay(tr, th, eye="trace"), th)
    assert m["cnn"].all() and m["current"].all()
    assert not m["p80"].any() and not m["ear_known"].any()


# ---------------------------------------------------------------- fake enrollment


def test_fake_profile_is_the_median_of_the_good_frames():
    th = load_thresholds()
    n = 20 * FPS
    tr = fake_trace([0.31] * n, FPS)
    tr["cols"]["yaw"] = np.full(n, 12.0)
    tr["cols"]["pitch"] = np.full(n, -4.0)
    tr["cols"]["mar"] = np.full(n, 0.07)
    tr["cols"]["blink"] = np.full(n, 0.1)
    tr["cols"]["ear"][: 2 * FPS] = 0.05  # a blink-like dip that the eyeBlink column flags
    tr["cols"]["blink"][: 2 * FPS] = 0.9
    p = ts.fake_profile(tr, th)
    assert p == {"ear_open": pytest.approx(0.31), "mar_closed": 0.07, "road_yaw": 12.0, "road_pitch": -4.0}
    tr["cols"]["mar"][:] = 0.6  # mouth never closed: nothing to enroll from
    assert ts.fake_profile(tr, th) is None


def test_replay_with_a_profile_uses_the_enrolled_road_pose():
    """A camera 40 deg to the side: self-learnt calibrates on the clip; an enrolled pose of 0 calls it off road."""
    th = load_thresholds()
    n = 12 * FPS
    tr = fake_trace([0.30] * n, FPS)
    tr["cols"]["yaw"] = np.full(n, 40.0)
    assert se.replay(tr, th, eye="trace")["alerts"] == []
    wrong = {"ear_open": 0.30, "mar_closed": 0.05, "road_yaw": 0.0, "road_pitch": 0.0}
    assert [rs for _, _, rs in se.replay(tr, th, eye="trace", profile=wrong)["alerts"]] == [("off_road",)]
    right = {**wrong, "road_yaw": 40.0}
    out = se.replay(tr, th, eye="trace", profile=right)
    assert out["alerts"] == [] and out["cols"]["ear_base"][-1] == pytest.approx(0.30, abs=0.03)


# ---------------------------------------------------------------- reports run end to end on tiny data


def tiny_sust():
    return {
        "drowsiness/d_1.mp4": clip([1.0, 0.4, 1.0], 3.0, face_bright=np.full(9 * FPS, 50.0)),
        "not drowsiness/n_1.mp4": clip([1.0, 1.0, 1.0], 3.0, face_bright=np.full(9 * FPS, 120.0)),
        "not drowsiness/n_2.mp4": clip([1.0, 0.6, 1.0], 3.0, face_bright=np.full(9 * FPS, 150.0)),
    }


def tiny_yawdd():
    def person(number, yaw):
        n = 15 * FPS
        return {
            f"Mirror/Female_mirror/{number}-FemaleNoGlasses-{action}.avi": clip(
                [1.0], 15.0, yaw=np.full(n, yaw), blink=np.full(n, 0.1), face_bright=np.full(n, 110.0)
            )
            for action in ("Normal", "Talking", "Yawning")
        }

    return {**person(1, 0.0), **person(2, 20.0)}


def test_perclos_report_on_tiny_traces():
    text = ts.perclos_report({"sust": tiny_sust()}, load_thresholds(), workers=1)
    for part in ("## 1.", "## 2.", "## 3.", "## 4.", "P80-equivalent (0.48)", "zpad006"):
        assert part in text
    assert "| sust | not drowsy (2) | P80: opening < 20 %, EAR frames only | 0.0% |" in text


def test_lighting_report_bins_by_face_brightness():
    text = ts.lighting_report({"sust": tiny_sust()}, load_thresholds(), workers=1)
    rows = {line.split("|")[1].strip(): line for line in text.splitlines() if line.startswith("| ")}
    assert set(rows) >= {"< 60", "100–140", "≥ 140"}
    assert "Do not compare across datasets" in text


def test_personal_report_leaves_the_enrollment_clip_out():
    text = ts.personal_report({"yawdd": tiny_yawdd()}, load_thresholds(), workers=1)
    assert "4 clips of 2 people scored" in text  # Talking + Yawning of each; the Normal clips gave the baselines
    for setting in ("fixed common eye baseline", "self-learnt", "fake-enrolled"):
        assert f"| all | {setting}" in text


def test_glance_report_counts_clips_over_each_threshold():
    n = 30 * FPS
    looking_away = np.where((np.arange(n) / FPS) % 2.0 < 1.5, 50.0, 0.0)
    looking_away[: 8 * FPS] = 0.0  # start-up calibration sees the road
    data = {"yawdd": {"a": clip([1.0], 30.0, yaw=looking_away), "b": clip([1.0], 30.0)}}
    text = ts.glance_report(data, load_thresholds(), workers=1)
    row = next(line for line in text.splitlines() if line.startswith("| yawdd"))
    cells = [c.strip() for c in row.split("|")[1:-1]]
    assert cells[1] == "2" and cells[4] == "1 (50%)" and cells[-1] == "1 (50%)"


# ---------------------------------------------------------------- tools/eval.py: per person, start-up apart


def test_subject_column_is_optional(tmp_path):
    p = tmp_path / "labels.csv"
    p.write_text("video,behavior,start_s,end_s\na.mp4,yawn,1,4\n", encoding="utf-8")
    assert ev.read_subjects(p) == {}
    p.write_text(
        "video,behavior,start_s,end_s,subject\na.mp4,yawn,1,4,an\nb.mp4,none,,,an\nc.mp4,none,,,\n", encoding="utf-8"
    )
    assert ev.read_subjects(p) == {"a.mp4": "an", "b.mp4": "an"}
    assert ev.read_labels(p)[1] == ["a.mp4", "b.mp4", "c.mp4"]  # the extra column does not disturb the labels


def test_false_positives_of_the_start_up_are_counted_apart():
    preds = [Prediction("v", "off_road", 5.0, 2), Prediction("v", "off_road", 100.0, 2)]
    preds += [Prediction("v", ev.ALERT, 5.0, 2), Prediction("v", ev.ALERT, 100.0, 2)]
    s = {x.behavior: x for x in ev.score([], preds, {"v": 3600.0}, warmup_s=30.0)}
    assert (s["off_road"].fp, s["off_road"].fp_warmup) == (2, 1)
    assert s["off_road"].warmup_h == pytest.approx(30 / 3600)
    assert s[ev.ALERT].fp_warmup == 1
    plain = {x.behavior: x for x in ev.score([], preds, {"v": 3600.0})}
    assert plain["off_road"].fp == 2 and plain["off_road"].warmup_h == 0.0  # off by default
    cfg = EvalConfig(window_s=10, warmup_s=30, positive_frac=0.5, min_level=1)
    text = ev.report(list(s.values()), {"v": 3600.0}, 1.0, None, cfg)
    assert "## False positives: start-up apart" in text
    row = next(line for line in text.splitlines() if line.startswith("| off_road | 1 |"))
    assert "| 1 | 0.99 |" in row  # the other one, on the remaining 59.5 minutes
    assert "start-up apart" not in ev.report(list(plain.values()), {"v": 3600.0}, 1.0, None, cfg)


def test_an_episode_in_the_start_up_takes_its_time_out():
    eps = [Episode("v", "yawn", 10.0, 20.0)]
    s = {x.behavior: x for x in ev.score(eps, [Prediction("v", "yawn", 12.0)], {"v": 60.0}, 1.0, warmup_s=30.0)}
    assert s["yawn"].tp == 1 and s["yawn"].fp_warmup == 0
    assert s["yawn"].warmup_h == pytest.approx((30 - 12) / 3600)  # 9-21 s is the episode ± 1 s


def test_per_person_table_shows_who_gets_the_false_alerts():
    durations = {"a1": 600.0, "a2": 600.0, "b1": 600.0, "c1": 600.0}
    subjects = {"a1": "an", "a2": "an", "b1": "binh"}  # c1 has no subject: its own person
    eps = [Episode("b1", "yawn", 100.0, 105.0)]
    preds = [Prediction("a1", ev.ALERT, 50.0, 2), Prediction("a1", "off_road", 50.0, 2)]
    preds += [Prediction("a2", ev.ALERT, 70.0, 2), Prediction("a2", "off_road", 70.0, 2)]
    preds += [Prediction("b1", ev.ALERT, 102.0, 1), Prediction("b1", "yawn", 102.0)]
    rows = ev.score_by_subject(eps, preds, durations, subjects)
    assert [r.subject for r in rows] == ["an", "binh", "c1"]
    an, binh, c1 = rows
    assert (an.videos, an.alerts, an.false_alerts, an.false_by) == (2, 2, 2, {"off_road": 2})
    assert an.fp_per_hour == pytest.approx(6.0) and an.fp_ci_low < 6.0 < an.fp_ci_high
    assert (binh.false_alerts, binh.caught, binh.episodes) == (0, 1, 1)
    assert (c1.videos, c1.alerts) == (1, 0)
    text = ev.report(ev.score(eps, preds, durations), durations, 1.0, None, None, rows)
    assert "## Per person" in text and "3 people. False alerts: 2 in all, from 1 of them" in text
    assert "| an | 2 | 0.33 | 2 | 2 | 6.0 (" in text


def test_per_person_windows_use_that_persons_videos_only():
    cfg = EvalConfig(window_s=10, warmup_s=30, positive_frac=0.5, min_level=1)
    drowsy = [0] * 120
    drowsy[45] = 1
    levels = {
        "a": {"drowsy": drowsy, "distraction": [0] * 120},
        "b": {"drowsy": [0] * 120, "distraction": [0] * 120},
    }
    rows = ev.score_by_subject([], [], {"a": 120.0, "b": 120.0}, {"a": "an", "b": "binh"}, 1.0, levels, cfg)
    by = {r.subject: r.windows for r in rows}
    assert (by["an"].awake, by["an"].false_alarms) == (9, 1)
    assert (by["binh"].awake, by["binh"].false_alarms) == (9, 0)
