"""M101: the rule that decides risk.drowsy.l1 on DROZY (eval/splits/drozy_l1_rule.md), on made-up counts.

The rule was written before the run; these tests pin that tools/drozy.py applies it as written: the
labels from KSS, the three conditions that must hold before DROZY may decide at all, and the two that
must both hold to change 40 into 50. No DROZY number is used here.
"""

import pytest

from tools import drozy


def tally(**over):
    base = {
        "videos": 36, "awake_videos": 15, "drowsy_videos": 15, "between_videos": 6, "awake_hours": 2.4,
        "false_alarms": 8, "awake_alerted": 4, "drowsy_alerted": 10, "drowsy_l3": 6, "between_alerted": 2,
        "reliable_median": 0.95, "auc": 0.80,
    }  # fmt: skip
    return {**base, **over}


def row(key, label, a_drowsy=0, score=10.0, reliable=0.95, seconds=570.0, l3=0):
    subject, test = (int(x) for x in key.split("-"))
    return {
        "key": key, "subject": subject, "test": test, "kss": 3, "label": label, "a_drowsy": a_drowsy,
        "a_drowsy_l3": l3, "score_mean": score, "reliable": reliable, "score_s": seconds, "fps": 30.0,
    }  # fmt: skip


def test_the_rule_file_exists_and_names_what_the_tool_uses():
    text = drozy.RULE.read_text(encoding="utf-8")
    for phrase in (
        "KSS ≤ 4",
        "KSS ≥ 7",
        "= 40 và 50",
        "đường `web`",
        "≥ 80 %",
        "1,5 giờ",
        "ít nhất 8 video",
        "≥ 0,65",
        "F40 − F50 ≥ 3",
        "D50 ≥ D40 − 1",
    ):
        assert phrase in text, phrase
    assert (drozy.AWAKE_KSS_MAX, drozy.DROWSY_KSS_MIN, drozy.L1_VALUES, drozy.DECISION_PATH) == (4, 7, (40, 50), "web")
    assert (drozy.GATE_RELIABLE_MEDIAN, drozy.GATE_AWAKE_HOURS, drozy.GATE_DROWSY_VIDEOS, drozy.GATE_AUC) == (
        0.80,
        1.5,
        8,
        0.65,
    )


def test_labels_come_from_kss_and_a_missing_score_is_no_label():
    assert [drozy.label(k) for k in (1, 4, 5, 6, 7, 9)] == ["awake", "awake", "between", "between", "drowsy", "drowsy"]
    assert drozy.label(0) is None and drozy.label(None) is None  # test 7-1 did not happen
    table = drozy.kss_table("3 6 7\n\n2 3 4\n0 4 9\n")
    assert table[(1, 3)] == 7 and table[(2, 1)] == 2 and table[(3, 1)] == 0


def test_the_tally_counts_alerts_after_the_start_up_by_label():
    rows = [
        row("1-1", "awake", a_drowsy=2, score=4.0),
        row("2-1", "awake", score=1.0),
        row("1-3", "drowsy", a_drowsy=3, score=30.0, l3=1),
        row("2-3", "drowsy", score=2.0),
        row("3-2", "between", a_drowsy=1),
    ]
    t = drozy.tally(rows)
    assert (t["false_alarms"], t["awake_alerted"], t["drowsy_alerted"], t["drowsy_l3"], t["between_alerted"]) == (
        2,
        1,
        1,
        1,
        1,
    )
    assert t["awake_hours"] == pytest.approx(2 * 570 / 3600)
    assert t["auc"] == pytest.approx(0.75)  # (30 > 4, 30 > 1, 2 < 4, 2 > 1)


def test_auc_counts_ties_as_half_and_is_nothing_without_both_groups():
    assert drozy.auc([5.0], [5.0]) == 0.5
    assert drozy.auc([], [1.0]) is None


@pytest.mark.parametrize(
    "broken",
    [{"reliable_median": 0.79}, {"awake_hours": 1.4}, {"drowsy_videos": 7}, {"auc": 0.64}, {"auc": None}],
)
def test_a_failed_condition_means_drozy_does_not_decide_whatever_the_counts(broken):
    verdict = drozy.decide(tally(**broken), tally(false_alarms=0))  # 50 would look perfect
    assert verdict["decision"] == 40 and "cannot decide" in verdict["why"]
    assert "conditions" not in verdict and not all(verdict["gates"].values())


def test_fifty_needs_both_fewer_false_alarms_and_no_more_than_one_drowsy_video_lost():
    assert drozy.decide(tally(), tally(false_alarms=4, drowsy_alerted=9))["decision"] == 50
    assert drozy.decide(tally(), tally(false_alarms=4, drowsy_alerted=10))["decision"] == 50


@pytest.mark.parametrize(
    "at50",
    [
        {"false_alarms": 5, "drowsy_alerted": 10},  # not halved
        {"false_alarms": 4, "drowsy_alerted": 8},  # two drowsy videos lost
        {"false_alarms": 8, "drowsy_alerted": 10},  # no gain
    ],
)
def test_anything_else_keeps_forty(at50):
    assert drozy.decide(tally(), tally(**at50))["decision"] == 40


def test_halved_is_not_enough_when_fewer_than_three_alarms_go():
    assert drozy.decide(tally(false_alarms=4), tally(false_alarms=2))["decision"] == 40  # halved, only 2 fewer
    assert drozy.decide(tally(false_alarms=2), tally(false_alarms=0))["decision"] == 40
    assert drozy.decide(tally(false_alarms=3), tally(false_alarms=0))["decision"] == 50


def test_the_report_states_the_verdict_and_every_condition():
    rows40 = [row(f"{s}-1", "awake", a_drowsy=1, score=3.0, seconds=600.0) for s in range(1, 11)]
    rows40 += [row(f"{s}-3", "drowsy", a_drowsy=1, score=30.0) for s in range(1, 9)]
    rows50 = [{**r, "a_drowsy": 0 if r["label"] == "awake" else 1} for r in rows40]
    results = {p: {40: rows40, 50: rows50} for p in drozy.PATHS}
    text = drozy.report(results, {}, "Source: test.")
    assert "## Verdict: l1 = 50" in text and "both conditions of section 5 hold" in text
    assert text.count("| yes |") == 5 and "| no |" not in text
    assert "| web (decides) | 40 | 10, 1.67 h | 10 | 10 / 10 | 8 / 8 |" in text
