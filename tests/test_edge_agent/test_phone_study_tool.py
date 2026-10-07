"""tools/phone_study.py: the pure parts (which frame the detector takes, which answer a frame sees,
how alerts are counted against the action labels), on made-up numbers."""

import numpy as np

from tools import phone_study as ps

FPS = 30.0


def times(seconds=10.0, jitter=0.002):
    i = np.arange(int(seconds * FPS))
    return i / FPS + jitter * np.sin(i * 12.9898)  # frames 33 ms apart, never exactly


def rate(t, taken):
    return (len(taken) - 1) / (t[taken[-1]] - t[taken[0]])


def test_the_pacer_runs_at_the_rate_asked_and_the_old_rule_below_it():
    t = times(20)
    assert abs(rate(t, ps.launches(t, ps.Schedule("new", 5, 0.09))) - 5.0) < 0.05
    # before M67: "at least 200 ms since the last run" often waits for the 7th frame
    assert rate(t, ps.launches(t, ps.Schedule("old", 5, 0.09, "legacy"))) < 4.8


def test_the_detector_never_takes_a_frame_while_its_answer_is_out():
    t = times(20)
    taken = ps.launches(t, ps.Schedule("slow", 10, 0.25))
    assert np.diff(t[taken]).min() >= 0.25 - 0.005
    assert ps.launches(t, ps.Schedule("off", 0, 0.1)) == []


def test_a_frame_sees_the_newest_answer_that_is_back_and_not_too_old():
    t = np.arange(40) / FPS
    taken = [0, 6, 30]  # 0.0 s, 0.2 s, 1.0 s
    used = ps.result_in_use(t, taken, latency_s=0.1, max_age_s=0.6)
    assert list(used[:3]) == [-1, -1, -1]  # the first answer is back at 0.1 s
    assert used[3] == 0 and used[8] == 0  # at 0.267 s the second one (0.2 + 0.1) is not back yet
    assert used[9] == 6
    assert used[24] == 6 and used[25] == -1  # 0.6 s after frame 6: too old from then on
    assert used[33] == 30
    ages = ps.ages_ms(t, used)
    assert ages.min() >= 100 - 1e-6 and ages.max() <= 600 + 1e-6


def test_a_shorter_period_makes_the_answers_younger():
    t = times(20)
    age = {}
    for name, fps, latency in (("5", 5, 0.095), ("10", 10, 0.02)):
        s = ps.Schedule(name, fps, latency)
        age[name] = np.percentile(ps.ages_ms(t, ps.result_in_use(t, ps.launches(t, s), latency, 0.6)), 95)
    assert 240 < age["5"] < 290 and 80 < age["10"] < 130


def fake_driver(n=900):
    """30 s: safe driving, a message (AC5) from 10 s to 15 s, a picture (AC9) from 20 s to 24 s."""
    t = np.arange(n) / FPS
    labels = [
        ("AC1", 0.0, 9.97),
        ("AC5", 10.0, 15.0),
        ("AC3", 15.03, 19.97),
        ("AC9", 20.0, 24.0),
        ("AC12", 24.03, 29.97),
    ]
    return {"fps": FPS, "n": n, "cols": {"t": t}, "labels": labels}


def test_alerts_are_counted_against_the_labels():
    tr = fake_driver()
    flag = np.zeros(tr["n"])
    flag[310:440] = 1.0  # the phone is seen during the message
    flag[100:110] = 1.0  # and for a moment in safe driving
    flag[:5] = np.nan  # no answer yet
    at = lambda s: int(round(s * FPS))  # noqa: E731
    alerts = [
        (at(12.0), 2, ("phone",)),  # in the message: the hit, 2 s after its start
        (at(15.5), 2, ("phone",)),  # just after it, within the tolerance: not a false alert
        (at(5.0), 2, ("phone",)),  # in safe driving: false
        (at(22.0), 2, ("phone",)),  # while taking a picture: counted apart
        (at(18.0), 2, ("off_road",)),  # another reason: not a phone alert
    ]
    sc = ps.Score()
    ps.score_driver(tr, flag, alerts, tol_s=1.0, sc=sc)
    assert (sc.sequences, sc.alerted, sc.false_alerts, sc.held_alerts) == (1, 1, 1, 1)
    assert sc.by_action[5] == [1, 1] and sc.by_action[7] == [0, 0]
    assert np.allclose(sc.latency_s, [2.0])
    assert sc.unknown == 5 and sc.frames == 900
    assert sc.pos_flagged == 130 and sc.neg_flagged == 10
    # negatives: everything except the message and the picture
    inside = ((tr["cols"]["t"] >= 10.0) & (tr["cols"]["t"] <= 15.0)).sum() + (
        (tr["cols"]["t"] >= 20.0) & (tr["cols"]["t"] <= 24.0)
    ).sum()
    assert abs(sc.negative_h - (900 - inside) / FPS / 3600) < 1e-9


def test_a_sequence_without_an_alert_is_a_miss():
    sc = ps.Score()
    ps.score_driver(fake_driver(), np.zeros(900), [], tol_s=1.0, sc=sc)
    assert (sc.sequences, sc.alerted, sc.false_alerts) == (1, 0, 0) and sc.latency_s == []


def test_boxes_are_grouped_per_frame_best_first_above_the_score():
    det = {
        "idx": np.array([3, 3, 7], dtype=np.int32),
        "boxes": np.array([[0, 0, 10, 10], [5, 5, 20, 20], [1, 1, 2, 2]], dtype=np.float32),
        "scores": np.array([0.4, 0.9, 0.2], dtype=np.float32),
    }
    per_frame = ps.boxes_of(det, 10, 0.35)
    assert [len(b) for b in per_frame] == [0, 0, 0, 2, 0, 0, 0, 0, 0, 0]  # the 0.2 box is below the score
    assert per_frame[3][0][4] > per_frame[3][1][4]


def test_the_phone_flag_uses_the_answer_in_use_and_the_current_face():
    from edge_agent.config import load_thresholds

    th = load_thresholds()
    n = 6
    cols = {"t": np.arange(n) / FPS}
    cols |= {
        "face_x1": np.full(n, 200.0),
        "face_y1": np.full(n, 100.0),
        "face_x2": np.full(n, 300.0),
        "face_y2": np.full(n, 220.0),
    }
    cols["face_x1"][5] = np.nan  # no face (and none remembered) on the last frame
    tr = {"fps": FPS, "n": n, "cols": cols}
    per_frame = [[] for _ in range(n)]
    per_frame[1] = [(330.0, 120.0, 360.0, 180.0, 0.8)]  # beside the face: in the driver zone
    per_frame[2] = [(600.0, 400.0, 630.0, 460.0, 0.8)]  # a passenger's: outside
    used = np.array([-1, 1, 1, 2, 1, 1])
    flag, kind = ps.phone_columns(tr, per_frame, used, th)
    assert np.isnan(flag[0]) and list(flag[1:]) == [1.0, 1.0, 0.0, 1.0, 0.0]
    assert kind[1] == 1.0 and np.isnan(kind[3])  # held at the ear: a call


def test_a_schedule_is_played_from_several_starting_frames_and_summed(monkeypatch):
    """One driver, a phone seen through the whole message: every start alerts once, none falsely."""
    from edge_agent.config import load_thresholds
    from tools import seq_eval

    tr = fake_driver()
    n = tr["n"]
    tr["cols"] |= {
        k: np.full(n, v) for k, v in (("face_x1", 200.0), ("face_y1", 100.0), ("face_x2", 300.0), ("face_y2", 220.0))
    }
    inside = np.flatnonzero((tr["cols"]["t"] >= 10.0) & (tr["cols"]["t"] <= 15.0))
    det = {
        "idx": inside.astype(np.int32),
        "boxes": np.tile(np.array([[330.0, 120.0, 360.0, 180.0]], dtype=np.float32), (len(inside), 1)),
        "scores": np.full(len(inside), 0.8, dtype=np.float32),
    }

    def fake_replay(played, thresholds):  # block 12 stand-in: an alert once the flag has been up for 1.7 s
        flag = np.nan_to_num(played["cols"]["phone_flag"])
        up = np.flatnonzero(flag > 0)
        return {"alerts": [(int(up[0] + 1.7 * FPS), 2, ("phone",))] if len(up) else []}

    monkeypatch.setattr(seq_eval, "replay", fake_replay)
    sc = ps.evaluate(
        {"D01": tr},
        {"D01": {"n": n, "models": {"640": det}}},
        ps.Schedule("s", 5, 0.095),
        load_thresholds(),
        1.0,
        starts=3,
    )
    assert (sc.sequences, sc.alerted, sc.false_alerts) == (3, 3, 0)
    assert sc.per_start == {0: [1, 0], 1: [1, 0], 2: [1, 0]}
    assert len(sc.ages) == 3 and sc.frames == 3 * n


def test_every_kth_frame_is_played_from_each_offset(monkeypatch):
    from edge_agent.config import load_thresholds
    from tools import seq_eval

    tr = fake_driver()
    n = tr["n"]
    tr["cols"] |= {
        k: np.full(n, v) for k, v in (("face_x1", 200.0), ("face_y1", 100.0), ("face_x2", 300.0), ("face_y2", 220.0))
    }
    # A phone box on every 6th frame only, inside the message: one offset of six sees it, the others never.
    idx = np.arange(300, 450, 6, dtype=np.int32)
    det = {
        "idx": idx,
        "boxes": np.tile(np.array([[330.0, 120.0, 360.0, 180.0]], dtype=np.float32), (len(idx), 1)),
        "scores": np.full(len(idx), 0.8, dtype=np.float32),
    }

    def fake_replay(played, thresholds):
        up = np.flatnonzero(np.nan_to_num(played["cols"]["phone_flag"]) > 0)
        return {"alerts": [(int(up[0] + 30), 2, ("phone",))] if len(up) else []}

    monkeypatch.setattr(seq_eval, "replay", fake_replay)
    rows = ps.every_kth({"D01": tr}, {"D01": {"n": n, "models": {"640": det}}}, 6, 3, load_thresholds(), 1.0)
    assert rows == [(1, 0), (0, 0), (0, 0), (0, 0), (0, 0), (0, 0)]
