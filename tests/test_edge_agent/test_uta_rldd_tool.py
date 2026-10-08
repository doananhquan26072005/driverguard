"""M53: UTA-RLDD tool (tools/uta_rldd.py). Fake sequences and fake rows, no video, no dataset."""

import json

import numpy as np
import pytest

from edge_agent.config import load_thresholds
from tools import uta_rldd as U  # noqa: N812
from tools.seq_eval import COLUMNS, resample_trace

FPS = 20


def test_label_fold_and_subject_come_from_the_path():
    assert U.parse_video("Fold3_part2/Fold3_part2/32/10_1.mp4") == (3, "32", 10, 1)
    assert U.parse_video("Fold1_part1/Fold1_part1/01/0.MOV") == (1, "01", 0, 0)
    assert U.parse_video("Fold1_part1/Fold1_part1/01/5.m4v") == (1, "01", 5, 0)
    assert U.parse_video("Fold1_part1/Fold1_part1/01/notes.mp4") is None  # not a label
    assert U.parse_video("somewhere/01/10.mp4") is None  # no fold in the path
    assert U.parse_video("Fold1_part1/Fold1_part1/01/105.mp4") is None


def test_discover_keeps_labelled_videos_and_names_the_rest(tmp_path):
    for rel in ("Fold1_part1/Fold1_part1/01/0.mov", "Fold1_part1/Fold1_part1/01/10.MP4", "Fold2_part1/x/13/readme.txt"):
        f = tmp_path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"x")
    (tmp_path / "Fold1_part1/Fold1_part1/01/extra.mp4").write_bytes(b"x")
    videos, skipped = U.discover(tmp_path)
    assert [v.key for v in videos] == ["F1_S01_0", "F1_S01_10"]
    assert skipped == ["Fold1_part1/Fold1_part1/01/extra.mp4"]


def test_sign_test_is_exact_and_two_sided():
    assert U.sign_test(0, 0) is None
    assert U.sign_test(5, 5) == pytest.approx(1.0)
    assert U.sign_test(10, 0) == pytest.approx(2 / 2**10)
    assert U.sign_test(0, 10) == U.sign_test(10, 0)


def row(subject, label, **over):
    base = {
        "key": f"{subject}_{label}", "fold": 1, "subject": subject, "label": label, "frames": 12000, "dur_s": 600.0,
        "warm_s": 30.0, "score_s": 570.0, "win": 57, "score_mean": 5.0, "score_p90": 10.0, "score_max": 20.0,
        "max_closed_s": 0.3, "first_drowsy_s": float("nan"), "alerts": "[]", "blink_timed": 0,
        "a_drowsy": 0, "a_drowsy_l2": 0, "a_drowsy_l3": 0, "a_dis": 0, "a_other": 0, "a_drowsy_warm": 0, "a_dis_warm": 0,
        "a_other_warm": 0, "fps": 25.0,
        "drowsy_win_l1": 0, "drowsy_win_l2": 0, "drowsy_win_l3": 0, "dis_win_l1": 0, "dis_win_l2": 0, "dis_win_l3": 0,
    }  # fmt: skip
    return base | over


def test_a_recording_in_two_files_counts_as_one_video_of_the_subject():
    rows = [
        row("F3_S32", 10, key="a", score_s=300.0, score_mean=20.0, a_drowsy=2, win=30, score_max=50.0),
        row("F3_S32", 10, key="b", score_s=100.0, score_mean=60.0, a_drowsy=1, win=10, score_max=90.0),
        row("F3_S32", 0),
    ]
    merged = U.by_subject(rows, 10)["F3_S32"]
    assert merged["a_drowsy"] == 3 and merged["win"] == 40 and merged["score_s"] == 400.0
    assert merged["score_mean"] == pytest.approx(30.0)  # weighted by the scored seconds
    assert merged["score_max"] == 90.0
    assert U.by_subject(rows, 0)["F3_S32"]["key"] == "F3_S32_0"


def test_metrics_count_false_alarms_on_awake_videos_only():
    rows = []
    for i in range(4):
        s = f"F1_S{i:02d}"
        rows.append(row(s, 0, a_drowsy=1 if i == 0 else 0, drowsy_win_l1=3 if i == 0 else 0, score_mean=2.0 + i))
        rows.append(row(s, 10, a_drowsy=2 if i < 3 else 0, a_drowsy_l2=1 if i < 2 else 0, score_mean=30.0 + i))
        rows.append(row(s, 5, a_drowsy=1 if i == 1 else 0))
    m = U.metrics(rows)
    assert m["subjects"] == 4 and m["fa"] == 1  # alerts on `10` and `5` are not false alarms
    assert m["awake_h"] == pytest.approx(4 * 570 / 3600)
    assert m["fa_per_h"] == pytest.approx(1 / m["awake_h"])
    assert m["far_l1"] == pytest.approx(3 / (4 * 57)) and m["subjects_far_gt0"] == 1
    assert m["auc_mean"] == 1.0 and (m["pairs_higher"], m["pairs_lower"]) == (4, 0)
    assert (m["v10_alerted"], m["v10_l2plus"], m["v5_alerted"], m["v0_alerted"]) == (3, 2, 1, 1)


def test_metrics_pair_only_subjects_with_both_levels():
    rows = [row("A", 0), row("A", 10, score_mean=9.0), row("B", 0), row("C", 10)]
    m = U.metrics(rows)
    assert m["pairs"] == 1 and m["v0"] == 2 and m["v10"] == 2


def fake_trace(seconds=120.0, closed=(), fps=FPS):
    """Eyes open, facing the camera; `closed` = (start s, end s) stretches with the eyes shut."""
    n = round(seconds * fps)
    t = np.arange(n) / fps
    cols = {k: np.full(n, np.nan) for k in COLUMNS}
    cols |= {"t": t, "face": np.ones(n), "reliable": np.ones(n), "ear": np.full(n, 0.30), "mar": np.full(n, 0.10)}
    cols |= {"pitch": np.zeros(n), "yaw": np.zeros(n), "blink": np.full(n, 0.05), "brow": np.full(n, 0.1)}
    cols |= {
        "ear_l": np.full(n, 0.30),
        "ear_r": np.full(n, 0.30),
        "is_ir": np.zeros(n),
        "face_bright": np.full(n, 120.0),
    }
    for a, b in closed:
        inside = (t >= a) & (t < b)
        cols["ear"][inside] = 0.05
        cols["blink"][inside] = 0.9
    return {"fps": float(fps), "n": n, "cols": cols, "events": [], "alerts": []}


def test_summary_splits_the_start_up_stretch_from_the_rest():
    th = load_thresholds()
    quiet = U.summarize(U.replay_plus(fake_trace(), th), th)
    assert quiet["a_drowsy"] == 0 and quiet["a_drowsy_warm"] == 0 and quiet["drowsy_win_l1"] == 0
    assert quiet["win"] == 9 and quiet["score_s"] == pytest.approx(90.0)  # 120 s - 30 s, 10 s windows
    # two long closures: one in the first 30 s (start-up, counted apart), one after
    s = U.summarize(U.replay_plus(fake_trace(closed=((15.0, 19.0), (70.0, 74.0))), th), th)
    assert s["a_drowsy_warm"] >= 1 and s["a_drowsy"] >= 1 and s["a_drowsy_l3"] >= 1
    assert s["drowsy_win_l3"] >= 1 and s["max_closed_s"] > 3.0
    assert s["first_drowsy_s"] < 30.0
    assert all(lv == 3 and "microsleep" in rs for _, lv, rs in json.loads(s["alerts"]) if lv == 3)
    assert s["a_all"] == len(json.loads(s["alerts"]))


def test_plain_replay_gives_the_same_decisions_as_the_one_with_extra_columns():
    th = load_thresholds()
    tr = fake_trace(closed=((70.0, 74.0),))
    a = U.summarize(U.replay_plus(tr, th, extras=True), th)
    b = U.summarize(U.replay_plus(tr, th, extras=False), th)
    assert "term_perclos" in a and "term_perclos" not in b
    for k in ("alerts", "a_drowsy", "drowsy_win_l1", "score_mean", "score_p90"):
        assert a[k] == b[k]


def test_make_thresholds_refuses_unknown_keys_and_broken_rules():
    th = load_thresholds()
    assert U.make_thresholds(th, ["risk.drowsy.l1=45"])["risk"]["drowsy"]["l1"] == 45
    assert th["risk"]["drowsy"]["l1"] != 45  # the base is not touched
    with pytest.raises(KeyError):
        U.make_thresholds(th, ["risk.drowsy.nope=1"])
    with pytest.raises(ValueError):
        U.make_thresholds(th, ["risk.drowsy.l1=95"])  # L1 above L2


def test_every_grid_configuration_is_valid_and_leaves_microsleep_alone():
    th = load_thresholds()
    grid = U.default_grid()
    assert grid[0] == ("baseline", [])
    for _, sets in grid:
        U.make_thresholds(th, sets)
        assert not any("microsleep_l3_s" in a or "microsleep_min_s" in a or "microsleep_deep.ear" in a for a in sets)


def test_awake_profile_goes_to_every_video_of_the_subject():
    items = [(U.Video(f"F1_S01_{lb}", 1, "01", lb, 0, "", 1.0), None) for lb in (0, 5, 10)]
    items.append((U.Video("F1_S02_10", 1, "02", 10, 0, "", 1.0), None))  # no `0` video: left to learn
    own = {
        "F1_S01_0": {"ear_open": 0.31},
        "F1_S01_5": {"ear_open": 0.25},
        "F1_S01_10": None,
        "F1_S02_10": {"ear_open": 0.2},
    }
    assert U.awake_profiles(items, own) == {k: {"ear_open": 0.31} for k in ("F1_S01_0", "F1_S01_5", "F1_S01_10")}


def test_reports_render_from_replayed_rows():
    th = load_thresholds()
    rows = []
    for subject in ("F1_S01", "F1_S02"):
        for label, closed in ((0, ()), (5, ()), (10, ((70.0, 74.0),))):
            summary = U.summarize(U.replay_plus(fake_trace(closed=closed), th), th)
            rows.append({"key": f"{subject}_{label}", "fold": 1, "subject": subject, "label": label, **summary})
    text = U.baseline_report(rows, th, "title")
    assert "## 2. Alerts on awake videos" in text and "| F1_S01 |" in text
    assert "2/2 subjects" in text  # both drowsy videos got a drowsiness alert
    assert "resampled by person (2 people," in text
    assert "| score_mean |" in U.signals_report(rows, "signals")
    grid = U.grid_report([{"group": "baseline", "config": "baseline", **U.metrics(rows), "error": ""}], "grid")
    assert "| baseline | baseline |" in grid
    assert "95% upper, by person" in grid and "95% upper, wider" in grid


def test_tradeoff_report_reads_the_current_point_and_marks_rows_under_one_per_hour():
    def row(l1, fa, hi_wide, alerted):
        return {
            "config": f"risk.drowsy.l1={l1}", "error": "", "subjects": 24, "awake_h": 4.0, "fa": fa,
            "fa_per_h": fa / 4.0, "fa_per_h_lo": 0.1, "fa_per_h_hi": hi_wide, "fa_per_h_hi_wide": hi_wide,
            "v10": 24, "v10_alerted": alerted, "v10_l2plus": 12, "v10_l3": 12,
        }  # fmt: skip

    dev = [row(40, 5, 3.0, 14), row(50, 2, 1.9, 12)]
    test = {**row(40, 4, 2.5, 15), "fa_per_h_person_lo": 0.0, "fa_per_h_person_hi": 3.0}
    text = U.tradeoff_report(dev, test, 40.0, "title")
    assert "**1.00 false alarms per hour**" in text and "**15 / 24**" in text
    assert "the upper bound is not" in text  # point estimate 1.0, upper bound 2.5
    assert "| 40 (current) | 5 |" in text and "| 50 | 2 |" in text
    assert text.count("| yes |") == 1 and text.count("| no |") == 1  # only l1 = 50 is at or under 1.0 / h
    assert "risk.drowsy.l1=50 (12 / 24)" in text


def test_minute_means_cover_whole_minutes_after_the_start_up_only():
    t = np.arange(0.0, 190.0, 1.0)  # 190 s: start-up 30 s, then two whole minutes and 40 s left over
    score = np.where(t < 60, 10.0, 50.0)
    assert U.minute_means(t, score, 30.0) == [30.0, 50.0]  # 30-90 s (half and half), 90-150 s
    assert U.minute_means(np.array([]), np.array([]), 30.0) == []


def test_score_bands_count_minutes_per_label_and_keep_the_top_score_in_the_last_band():
    bands = U.score_bands({0: [5.0, 10.0, 45.0], 5: [30.0], 10: [45.0, 100.0, 99.0]}, 20.0)
    assert [(b["lo"], b["hi"]) for b in bands] == [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)]
    assert [(b[0], b[5], b[10]) for b in bands] == [(2, 0, 0), (0, 1, 0), (1, 0, 1), (0, 0, 0), (0, 0, 2)]


def test_report_has_a_score_band_table_from_minute_scores():
    th = load_thresholds()
    rows = []
    for subject in ("F1_S01", "F1_S02"):
        for label, closed in ((0, ()), (5, ()), (10, ((70.0, 74.0),))):
            summary = U.summarize(U.replay_plus(fake_trace(closed=closed), th), th)
            rows.append({"key": f"{subject}_{label}", "fold": 1, "subject": subject, "label": label, **summary})
    text = U.baseline_report(rows, th, "title")
    assert "## 4b. What a drowsy_score band means" in text and "← L1" in text


def test_metrics_count_every_branch_and_the_start_up_stretch_apart():
    """The PRD counts every alert of every branch; the headline rate counts one branch after the start-up."""
    rows = [
        row("F1_S01", 0, a_drowsy=1, a_drowsy_warm=1, a_dis=2, a_dis_warm=1, a_other=1, a_other_warm=1),
        row("F1_S02", 0),
        row("F1_S01", 10, a_drowsy_warm=1),  # alerted only inside the start-up stretch
        row("F1_S02", 10, a_drowsy=1),
    ]
    m = U.metrics(rows)
    assert m["fa"] == 1 and m["fa_whole"] == 2  # drowsiness branch: after the start-up / whole video
    assert m["fa_any"] == 4 and m["fa_any_whole"] == 7  # every branch
    assert m["awake_h"] == pytest.approx(2 * 570 / 3600) and m["whole_h"] == pytest.approx(2 * 600 / 3600)
    assert (m["v10_alerted"], m["v10_alerted_late"]) == (2, 1)  # the same video counted with both rules
    assert (m["v0_alerted"], m["v0_alerted_late"]) == (1, 1)


def test_fps_groups_keep_slow_videos_in_the_count_and_report_them_apart():
    rows = [
        row("F1_S01", 0, fps=30.0, a_drowsy=1),
        row("F1_S02", 0, fps=12.0, a_drowsy=3, a_dis_warm=1),
        row("F1_S02", 10, fps=12.0, a_drowsy_warm=1),
        row("F1_S03", 10, fps=15.0),  # exactly the minimum is inside the working range
    ]
    inside, below = U.fps_groups(rows, 15.0)
    assert (inside["group"], below["group"]) == ("≥ 15 FPS", "< 15 FPS")
    assert (inside["videos"], inside["v0"], inside["fa"], inside["v10"], inside["v10_alerted"]) == (2, 1, 1, 1, 0)
    assert (below["videos"], below["v0"], below["fa"], below["v10"], below["v10_alerted"]) == (2, 1, 3, 1, 1)
    assert below["fa_any_whole"] == 4 and below["awake_h"] == pytest.approx(570 / 3600)
    assert inside["fa"] + below["fa"] == U.metrics(rows)["fa"]  # nothing is dropped from the headline


def test_report_shows_every_branch_rows_and_the_frame_rate_groups():
    th = load_thresholds()
    rows = []
    for subject in ("F1_S01", "F1_S02"):
        for label, closed in ((0, ()), (5, ()), (10, ((70.0, 74.0),))):
            summary = U.summarize(U.replay_plus(fake_trace(closed=closed), th), th)
            rows.append({"key": f"{subject}_{label}", "fold": 1, "subject": subject, "label": label, **summary})
    text = U.baseline_report(rows, th, "title")
    assert "| All branches, whole video |" in text and "| Drowsiness branch, whole video |" in text
    assert "the PRD target counts every alert" in text
    assert "| ≥ 15 FPS |" in text and "| < 15 FPS |" in text


def test_reading_the_held_out_subjects_is_logged_and_reading_dev_is_not():
    assert U.reads_test_subjects("report", "test") and U.reads_test_subjects("compare", "all")
    assert U.reads_test_subjects("tradeoff", "dev") and U.reads_test_subjects("personal", "dev")
    assert not U.reads_test_subjects("report", "dev") and not U.reads_test_subjects("grid", "test")


def test_test_read_log_appends_one_line_per_run_under_a_header(tmp_path):
    log = tmp_path / "reads.tsv"
    U.log_test_read("report", "test", ["report", "--split", "test"], log)
    U.log_test_read("tradeoff", "dev", ["tradeoff"], log)
    lines = log.read_text(encoding="utf-8").splitlines()
    assert lines[0].split("\t")[:2] == ["time_utc", "commit"] and len(lines) == 3
    first = lines[1].split("\t")
    assert first[4:] == ["report", "test", "report --split test"] and len(first) == 7
    assert lines[2].split("\t")[4] == "tradeoff"


def test_main_on_the_test_split_writes_the_log_before_scoring(tmp_path, monkeypatch):
    log = tmp_path / "reads.tsv"
    monkeypatch.setattr(U, "TEST_LOG", log)
    monkeypatch.setattr(U, "load_items", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("stop here")))
    with pytest.raises(RuntimeError):
        U.main(["report", "--split", "test", "--workers", "1"])
    assert len(log.read_text(encoding="utf-8").splitlines()) == 2  # a run that fails still looked


# ---------------------------------------------------------------- M75: the same video at a lower frame rate


def test_a_resampled_trace_keeps_real_frames_with_their_own_times():
    tr = fake_trace(seconds=60.0, closed=((20.0, 23.0),), fps=30.0)
    slow = resample_trace(tr, 10.0)
    assert slow["n"] == 600 and slow["fps"] == pytest.approx(10.0) and slow["source_fps"] == 30.0
    assert slow["n"] / slow["fps"] == pytest.approx(60.0)  # still the duration of the video
    assert np.array_equal(slow["cols"]["t"], tr["cols"]["t"][::3])
    assert np.array_equal(slow["cols"]["ear"], tr["cols"]["ear"][::3])  # nothing interpolated
    assert tr["n"] == 1800  # the trace handed in is not touched


def test_a_rate_that_does_not_divide_the_recording_gives_unequal_gaps_and_the_right_average():
    slow = resample_trace(fake_trace(seconds=60.0, fps=30.0), 12.0)
    gaps = np.round(np.diff(slow["cols"]["t"]) * 30).astype(int)
    assert set(gaps) == {2, 3} and slow["fps"] == pytest.approx(12.0, abs=0.05)


def test_a_trace_cannot_be_resampled_faster_than_it_was_recorded():
    tr = fake_trace(seconds=10.0, fps=30.0)
    assert resample_trace(tr, 60.0)["n"] == tr["n"]
    assert resample_trace(tr, 60.0, jitter_cv=0.3)["n"] <= tr["n"]


def test_uneven_waits_repeat_with_the_seed_and_keep_the_rate():
    tr = fake_trace(seconds=120.0, fps=30.0)
    a, b, other = (resample_trace(tr, 10.0, 0.3, seed=s) for s in (0, 0, 1))
    assert np.array_equal(a["cols"]["t"], b["cols"]["t"])
    assert not np.array_equal(a["cols"]["t"], other["cols"]["t"])
    gaps = np.diff(a["cols"]["t"])
    assert a["fps"] == pytest.approx(10.0, rel=0.05) and gaps.min() > 0 and gaps.max() > 1.5 * gaps.min()


def test_an_offset_moves_the_grid_and_alerts_of_the_recording_move_to_a_kept_frame():
    tr = fake_trace(seconds=10.0, fps=30.0)
    tr["alerts"], tr["events"] = [(100, 3, ("microsleep",))], [(299, "blink")]
    slow = resample_trace(tr, 10.0, offset_s=1 / 30)
    assert slow["cols"]["t"][0] == pytest.approx(1 / 30)
    (i, level, reasons), (j, event) = slow["alerts"][0], slow["events"][0]
    assert (level, reasons, event) == (3, ("microsleep",), "blink")
    assert slow["cols"]["t"][i] == pytest.approx(100 / 30) and j == slow["n"] - 1


def test_a_summary_times_alerts_by_the_time_of_their_frame():
    """A slowed trace has fewer frames: the frame number of an alert no longer gives its second."""
    th = load_thresholds()
    slow = resample_trace(fake_trace(closed=((15.0, 19.0), (70.0, 74.0)), fps=30.0), 10.0, jitter_cv=0.3)
    s = U.summarize(U.replay_plus(slow, th), th)
    times = [t for t, lv, _ in json.loads(s["alerts"]) if lv == 3]
    assert times == pytest.approx([16.5, 71.5], abs=0.4)
    assert (s["a_drowsy_warm"], s["a_drowsy_l3"]) == (1, 1) and s["dur_s"] == pytest.approx(120.0, abs=0.1)
    assert s["gap_p50"] == pytest.approx(0.1, abs=0.04) and s["gap_max"] > s["gap_p50"]


def test_the_fps_study_slows_only_fast_recordings_and_reports_every_loop(tmp_path):
    th = load_thresholds()
    th["eval"] = {**th["eval"], "fps_study_rates": [10], "fps_study_repeats": 2}
    items = []
    for subject, fps in (("01", 30.0), ("02", 30.0), ("03", 12.0)):  # the third camera is slow already
        for label, closed in ((0, ()), (10, ((70.0, 74.0),))):
            v = U.Video(f"F1_S{subject}_{label}", 1, subject, label, 0, "x.mp4", 1.0)
            U.save_trace(U.trace_file(tmp_path, v.key), fake_trace(closed=closed, fps=fps))
            items.append((v, U.trace_file(tmp_path, v.key)))
    runs, recorded = U.fps_study(items, th)
    assert list(runs) == [U.RECORDED, "10 FPS, even", "10 FPS, uneven"]
    assert [len(reps) for reps in runs.values()] == [1, 2, 2] and len(recorded) == 6
    every = [rows for reps in runs.values() for rows in reps]
    assert all(len(rows) == 4 and {r["subject"] for r in rows} == {"F1_S01", "F1_S02"} for rows in every)
    assert all(r["fps"] == pytest.approx(10.0, rel=0.05) for rows in runs["10 FPS, uneven"] for r in rows)
    even = runs["10 FPS, even"]
    assert even[0][0]["gap_p50"] == pytest.approx(0.1)
    assert all(r["a_drowsy_l3"] == 1 for r in even[1] if r["label"] == 10)
    text = U.fps_report(runs, recorded, th, "title")
    assert "| as recorded | 30.0 |" in text and "| 10 FPS, uneven | 10.0 |" in text
    assert "| 2 / 2 | 2 |" in text  # both `10` subjects alerted and at L3, at every loop
    assert "0 of 4 videos have another number" in text and "| < 15 FPS | 2 | 1 |" in text


def test_span_shows_one_number_when_every_run_agrees():
    assert (U._span([5, 5, 5]), U._span([4, 5, 6]), U._span([None]), U._span([1.5, 1.5], 2)) == (
        "5",
        "5.0 (4–6)",
        "–",
        "1.50",
    )
