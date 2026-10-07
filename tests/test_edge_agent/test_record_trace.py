"""M39: tools/record_trace.py. Labels from key presses, time to alert, false alarms, the report, and
that a saved trace holds numbers only. Fake traces replayed through blocks 7-12; no camera, no model."""

import pickle

import numpy as np
import pytest

from edge_agent.config import load_thresholds
from tests.test_edge_agent.test_seq_eval_tool import fake_trace
from tools import record_trace as rt
from tools import seq_eval as se

FPS = 25


def recording(seconds=40, closed=(), yaw=(), phone=(), kind=None, mar=None, labels=(), tags=None):
    """A replayed fake recording: eyes shut in `closed` spans, head turned in `yaw` spans, a phone in
    the driver zone in `phone` spans (held as `kind`)."""
    n = seconds * FPS
    t = np.arange(n) / FPS
    inside = lambda spans: np.any([(t >= a) & (t < b) for a, b in spans], axis=0) if spans else np.zeros(n, bool)  # noqa: E731
    tr = fake_trace(list(np.where(inside(closed), 0.08, 0.30)), FPS)
    tr["cols"]["yaw"] = np.where(inside(yaw), 50.0, 0.0)
    tr["cols"]["phone_flag"] = inside(phone).astype(float)
    code = np.nan if kind is None else se.PHONE_KIND_CODES[kind]
    tr["cols"]["phone_kind"] = np.where(inside(phone), code, np.nan)
    if mar is not None:
        tr["cols"]["mar"] = np.asarray(mar, dtype=float)
    out = se.replay(tr, load_thresholds(), eye="ear")
    out["labels"] = sorted(labels, key=lambda x: x[1])
    out["tags"] = tags or {}
    return out


# ---------------------------------------------------------------- labels


def test_first_press_starts_a_label_the_next_one_ends_it():
    keys = rt.LabelKeys()
    assert keys.press("e", 5.0) == "eyes_closed"
    assert keys.press("y", 6.0) == "yawn"  # two labels may be on at once
    assert sorted(keys.open) == ["eyes_closed", "yawn"]
    keys.press("e", 8.0)
    keys.press("e", 20.0)  # a second spell of the same label
    assert keys.press("z", 21.0) is None  # not a label key
    assert keys.close(30.0) == [("eyes_closed", 5.0, 8.0), ("yawn", 6.0, 30.0), ("eyes_closed", 20.0, 30.0)]


def test_every_key_has_an_expected_answer_or_is_quiet():
    assert set(rt.KEYS.values()) == set(rt.EXPECTED)
    assert set(rt.QUIET) == {"talking", "awake_still", "mirror_check"}


def test_script_labels_for_a_video_file():
    assert rt.parse_script("yawn@12-15.5, eyes_closed@5-8") == [("eyes_closed", 5.0, 8.0), ("yawn", 12.0, 15.5)]
    with pytest.raises(ValueError, match="unknown label"):
        rt.parse_script("sneeze@1-2")
    with pytest.raises(ValueError, match="end must be after start"):
        rt.parse_script("yawn@5-5")


def test_tags_are_key_value():
    assert rt.parse_tags(["mask=medical", "light = day"]) == {"mask": "medical", "light": "day"}
    with pytest.raises(ValueError):
        rt.parse_tags(["mask"])


# ---------------------------------------------------------------- time to alert, false alarms


def test_time_to_alert_of_a_closed_eye_spell():
    tr = recording(closed=[(15.0, 18.0)], labels=[("eyes_closed", 15.0, 18.0)])
    (row,) = rt.time_to_alert(tr, tolerance_s=1.0)
    l3_s = load_thresholds()["risk"]["microsleep_l3_s"]
    assert row["label"] == "eyes_closed" and row["duration"] == 3.0
    assert row["delay"] == pytest.approx(l3_s, abs=0.3)  # L3 as soon as the closure is long enough


def test_a_missed_action_has_no_delay():
    tr = recording(labels=[("eyes_closed", 15.0, 18.0), ("talking", 20.0, 25.0)])  # eyes never closed
    rows = rt.time_to_alert(tr, tolerance_s=1.0)
    assert [(r["label"], r["delay"]) for r in rows] == [("eyes_closed", None)]  # talking expects nothing


def test_off_road_and_phone_answers_are_matched_by_reason():
    tr = recording(
        yaw=[(12.0, 17.0)],
        phone=[(25.0, 31.0)],
        kind="text",
        labels=[("look_side", 12.0, 17.0), ("phone_text", 25.0, 31.0)],
    )
    rows = {r["label"]: r["delay"] for r in rt.time_to_alert(tr, tolerance_s=1.0)}
    assert 2.0 <= rows["look_side"] <= 3.0  # risk.distraction.off_road_s + the alert's confirmation
    assert 1.0 <= rows["phone_text"] <= 2.5
    fas, exposure = rt.false_alarms(tr, tolerance_s=1.0)
    assert fas == [] and exposure == pytest.approx(40 - 7 - 8, abs=0.1)


def test_an_alert_outside_every_label_is_a_false_alarm():
    tr = recording(yaw=[(12.0, 17.0)], labels=[("awake_still", 10.0, 20.0)])
    fas, exposure = rt.false_alarms(tr, tolerance_s=1.0)
    assert [(lv, rs) for _, lv, rs in fas] == [(2, ("off_road",))]
    assert exposure == pytest.approx(40.0, abs=0.1)  # a quiet label takes no time out


def test_an_alert_with_the_wrong_reason_inside_a_label_is_a_false_alarm():
    tr = recording(closed=[(15.0, 18.0)], labels=[("look_side", 14.0, 19.0)])
    fas, _ = rt.false_alarms(tr, tolerance_s=1.0)
    assert [rs for _, _, rs in fas] == [("microsleep",)]


def test_percentile_of_nothing_is_none():
    assert rt.percentile([], 95) is None
    assert rt.percentile([1.0, 2.0, 3.0], 50) == 2.0


# ---------------------------------------------------------------- mouth numbers


def test_reversals_count_real_swings_only():
    still = np.full(100, 0.05) + np.tile([0.0, 0.01], 50)  # jitter below the swing
    assert rt.reversals(still, 0.08) == 0
    assert rt.reversals(np.array([0.05] * 10 + [0.6] * 10), 0.08) == 0  # mouth opens once
    assert rt.reversals(np.array([0.05] * 10 + [0.6] * 10 + [0.05] * 10), 0.08) == 1  # a yawn and back
    talking = np.tile([0.05, 0.25], 10)
    assert rt.reversals(talking, 0.08) == 18
    assert rt.reversals(np.array([np.nan, np.nan]), 0.08) == 0


# ---------------------------------------------------------------- report


def test_report_has_every_table_and_the_numbers_of_the_recordings():
    n = 40 * FPS
    noisy = 0.05 + 0.2 * (np.arange(n) % 6 < 3)  # a mouth that "moves" all the time (e.g. under a mask)
    traces = {
        "bare": recording(
            closed=[(15.0, 18.0)],
            phone=[(25.0, 31.0)],
            kind="call",
            labels=[("awake_still", 2.0, 10.0), ("eyes_closed", 15.0, 18.0), ("phone_call", 25.0, 31.0)],
            tags={"mask": "none"},
        ),
        "masked": recording(
            closed=[(15.0, 18.0)],
            mar=noisy,
            labels=[("awake_still", 2.0, 10.0), ("eyes_closed", 15.0, 18.0)],
            tags={"mask": "medical"},
        ),
    }
    text = rt.report(traces, load_thresholds())
    for heading in ("## 1.", "## 2.", "## 3.", "## 4.", "## 5.", "## 6."):
        assert heading in text
    assert "| phone_call | alert phone | 1 | 1 (100%)" in text
    table = [line.split("|") for line in text.splitlines() if line.startswith("|")]
    rows = {cells[1].strip(): [c.strip() for c in cells[2:-1]] for cells in table}
    assert rows["eyes_closed ≥ 1.5 s"][1:3] == ["2", "1 (50%)"]  # the masked one never reached L3
    assert rows["none"][8:10] == ["1", "1 (100%)"]
    assert rows["medical"][8:10] == ["1", "0 (0%)"]  # the closed spell was hidden ...
    assert rows["medical"][10] == "100%"  # ... because the talking mask was on throughout
    assert float(rows["medical"][3]) > 100 and float(rows["none"][3]) == 0  # MAR reversals / min while still
    assert rows["call"][:3] == ["150", "100%", "150"]


def test_report_of_recordings_without_labels():
    text = rt.report({"plain": recording()}, load_thresholds())
    assert "no labelled action yet" in text and "No `phone_call` / `phone_text` label recorded yet." in text


# ---------------------------------------------------------------- only numbers are saved


def test_saved_file_holds_numbers_only_and_recordings_add_up(tmp_path):
    path = tmp_path / "own.pkl"
    a = recording(labels=[("awake_still", 1.0, 5.0)], tags={"mask": "none"})
    rt.save(path, "first", a, overwrite=False)
    rt.save(path, "second", recording(), overwrite=False)
    with pytest.raises(SystemExit):
        rt.save(path, "first", a, overwrite=False)
    data = pickle.loads(path.read_bytes())
    assert sorted(data) == ["first", "second"]
    for tr in data.values():
        assert all(col.ndim == 1 and col.dtype.kind == "f" for col in tr["cols"].values())
    assert sorted(rt.load([str(path)])) == ["first", "second"]


def test_a_trace_with_an_image_is_refused(tmp_path):
    tr = recording()
    tr["cols"]["face_crop"] = np.zeros((tr["n"], 32, 32))
    with pytest.raises(ValueError, match="not a 1-D float array"):
        rt.save(tmp_path / "x.pkl", "bad", tr, overwrite=False)
    tr = recording()
    tr["preview"] = b"\xff\xd8\xff"
    with pytest.raises(ValueError, match="unexpected trace fields"):
        rt.save(tmp_path / "x.pkl", "bad", tr, overwrite=False)
    assert not (tmp_path / "x.pkl").exists()


def test_tracer_columns_cover_what_the_recordings_need():
    for col in (
        "look_down_l",
        "look_down_r",
        "jaw_open",
        "mouth_close",
        "iris_y_l",
        "phone_x1",
        "face_y2",
        "phone_kind",
    ):
        assert col in se.COLUMNS
    assert len(se.COLUMNS) == len(set(se.COLUMNS))


def test_iris_offsets_follow_the_iris():
    points = np.zeros((478, 3), dtype=np.float32)
    for side, (iris, outer, inner) in se.IRIS.items():
        x0 = 100.0 if side == "r" else 300.0
        points[outer, :2] = (x0, 200.0)
        points[inner, :2] = (x0 + (40.0 if side == "r" else -40.0), 200.0)
        points[iris, :2] = (x0 + (20.0 if side == "r" else -20.0), 200.0)
    centred = se.iris_offsets(points)
    assert all(abs(v) < 1e-6 for v in centred.values()) and len(centred) == 4
    for iris, _, _ in se.IRIS.values():
        points[iris, 1] += 8.0  # eyes looking down: the iris moves down in the image
    down = se.iris_offsets(points)
    assert down["iris_y_l"] == pytest.approx(0.2) and down["iris_y_r"] == pytest.approx(0.2)
    assert se.iris_offsets(points[:468]) == {}  # a model without iris landmarks


def test_replay_uses_the_traced_phone_flag_and_kind():
    tr = recording(phone=[(25.0, 31.0)], kind="text")
    assert [rs for _, _, rs in tr["alerts"]] == [("phone",)]
    old = recording()
    del old["cols"]["phone_flag"], old["cols"]["phone_kind"]  # a trace made before M39
    assert se.replay(old, load_thresholds(), eye="ear")["alerts"] == []
