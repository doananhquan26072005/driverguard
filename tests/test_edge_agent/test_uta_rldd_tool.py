"""M53: UTA-RLDD tool (tools/uta_rldd.py). Fake sequences and fake rows, no video, no dataset."""

import json

import numpy as np
import pytest

from edge_agent.config import load_thresholds
from tools import uta_rldd as U  # noqa: N812
from tools.seq_eval import COLUMNS

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
    assert "| score_mean |" in U.signals_report(rows, "signals")
    grid = U.grid_report([{"group": "baseline", "config": "baseline", **U.metrics(rows), "error": ""}], "grid")
    assert "| baseline | baseline |" in grid
