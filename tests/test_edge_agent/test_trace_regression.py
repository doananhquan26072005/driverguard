"""M34, M86: blocks 5, 7-12 replayed on the fixture traces must give the pinned results, on the device
path and on the two eye paths of the page (web, web_ir), with the phone flag and frame quality where
the trace has them.

A red test here means the decision chain changed what it does on real recordings (numbers only, no
image: tests/fixtures/regression/). If the change is intended, pin the new results in the same commit:

    python tools/regression_traces.py update --reason "<milestone>: <what changed and why>"
"""

import copy
import json

import numpy as np
import pytest

from edge_agent.config import load_thresholds
from tools import regression_traces as rt
from tools.seq_eval import set_threshold

HOW_TO_UPDATE = (
    "\nBlocks 5, 7-12 no longer give the pinned results on the fixture traces."
    '\nIntended? Run: python tools/regression_traces.py update --reason "<why>" and commit expected.json.\n'
)


@pytest.fixture(scope="module")
def traces():
    return rt.load_fixture()


def test_decision_chain_matches_the_pinned_results():
    diffs = rt.check(load_thresholds())
    assert not diffs, HOW_TO_UPDATE + "\n".join(diffs)


@pytest.mark.parametrize(
    "assignment",
    ["risk.microsleep_l3_s=3.0", "drowsiness.yawn.min_s=5.0", "risk.distraction.off_road_s=6.0", "risk.drowsy.l1=10"],
)
def test_a_changed_threshold_is_caught(assignment):
    th = copy.deepcopy(load_thresholds())
    set_threshold(th, assignment)
    assert rt.check(th), f"{assignment} changed nothing on the fixture: it does not cover that rule"


@pytest.mark.parametrize(
    ("assignment", "paths", "datasets"),
    [
        # the page's eye score: only the web paths read it, the device path must not move
        ("drowsiness.eye.blendshape_closed=0.8", {"web", "web_ir"}, None),
        ("drowsiness.eye.blendshape_open=0.2", {"web", "web_ir"}, None),
        # frame quality and the phone flag exist only in the 3MDAD traces
        ("quality.dark_face_brightness=0", set(rt.PATHS), {"3mdad"}),
        ("quality.blur_sharpness=40", set(rt.PATHS), {"3mdad"}),
        ("risk.distraction.phone_ratio=0.95", set(rt.PATHS), {"3mdad"}),
    ],
)
def test_a_changed_web_quality_or_phone_threshold_is_caught_where_it_applies(assignment, paths, datasets):
    th = copy.deepcopy(load_thresholds())
    set_threshold(th, assignment)
    diffs = rt.check(th)
    assert {d.split("]")[0][1:] for d in diffs} == paths, f"{assignment}: {diffs[:3]}"
    if datasets is not None:
        assert {d.split("] ")[1].split("/")[0] for d in diffs} == datasets


def test_the_three_paths_are_pinned_and_really_differ():
    pinned = rt.pinned()
    assert set(pinned) == set(rt.PATHS)
    assert all(set(pinned[p]) == set(pinned["device"]) for p in rt.PATHS)
    differs = lambda a, b: sum(bool(rt.differences(pinned[a][k], pinned[b][k])) for k in pinned[a])  # noqa: E731
    assert differs("device", "web") >= 5 and differs("web", "web_ir") >= 5  # else a path pins nothing new


def test_the_phone_and_quality_videos_show_what_they_are_there_for():
    extra = {k: v for k, v in rt.pinned()["device"].items() if k.startswith("3mdad/")}
    assert len(extra) == sum(rt.EXTRA_PER_DATASET.values())
    reasons = {r for v in extra.values() for _, _, rs in v["alerts"] for r in rs}
    paused = {r for v in extra.values() for r in v["paused"]}
    assert {"phone", "off_road"} <= reasons
    assert {"low_light", "bad_angle", "no_face"} <= paused  # quality gate, face partly out, face lost


def test_fixture_covers_every_level_and_the_main_events(traces):
    expected = json.loads(rt.EXPECTED.read_text(encoding="utf-8"))["videos"]
    assert set(expected) == set(traces) and len(traces) >= 30
    assert {name.split("/")[0] for name in traces} == set(rt.SOURCES) | set(rt.EXTRA_SOURCES)
    levels = {level for v in expected.values() for _, level, _ in v["alerts"]}
    events = {ev for v in expected.values() for ev in v["events"]}
    assert levels == {1, 2, 3}
    assert {"blink", "microsleep", "yawn", "nod", "perclos_high"} <= events
    assert sum(not v["alerts"] for v in expected.values()) >= 10  # quiet videos: a new false alert shows


def test_fixture_holds_numbers_only_and_stays_small():
    with np.load(rt.TRACES) as z:
        assert set(z.files) == {"names", "lengths", "fps"} | {f"col_{c}" for c in rt.INPUT_COLUMNS}
        total = int(z["lengths"].sum())
        for c in rt.INPUT_COLUMNS:  # one number per frame and column: no room for an image
            assert z[f"col_{c}"].dtype == np.float32 and z[f"col_{c}"].shape == (total,)
    assert rt.TRACES.stat().st_size < 1_000_000
    with np.load(rt.EXTRA_TRACES) as z:
        assert set(z.files) == {"names", "lengths", "fps"} | {f"col_{c}" for c in rt.EXTRA_COLUMNS}
        total = int(z["lengths"].sum())
        for c in rt.EXTRA_COLUMNS:
            assert z[f"col_{c}"].dtype == np.float32 and z[f"col_{c}"].shape == (total,)
    assert rt.EXTRA_TRACES.stat().st_size < 1_000_000


def test_every_update_of_the_pinned_results_has_a_reason():
    updates = json.loads(rt.EXPECTED.read_text(encoding="utf-8"))["updates"]
    assert updates and all(u["date"] and len(u["reason"]) >= 10 for u in updates)


# ---------------------------------------------------------------- pure helpers, fake data


def summary(frames=100, events=None, alerts=None, scores=(0.0, 0.0, 0.0, 0.0), paused=None):
    return {
        "frames": frames,
        "events": events or {},
        "alerts": alerts or [],
        "max_level": max((a[1] for a in alerts or []), default=0),
        "drowsy_score": list(scores),
        "paused": paused or {},
    }


def test_select_also_wants_a_video_of_each_reason_monitoring_paused():
    videos = {"a": summary(100), "b": summary(200), "dark": summary(900, paused={"low_light": 30})}
    assert rt.select(videos, 2) == ["a", "dark"]
    changed = rt.differences(videos["dark"], {**videos["dark"], "paused": {"low_light": 31}})
    assert [d.split(":")[0] for d in changed] == ["paused"]


def test_web_ir_takes_every_frame_for_infrared_and_only_the_web_paths_change_the_eye_source():
    th = load_thresholds()
    tr = {"n": 3, "cols": {"is_ir": np.zeros(3), "ear": np.ones(3)}}
    assert rt.path_trace("device", tr) is tr and rt.path_trace("web", tr) is tr
    assert rt.path_trace("web_ir", tr)["cols"]["is_ir"].tolist() == [1.0, 1.0, 1.0]
    assert tr["cols"]["is_ir"].tolist() == [0.0, 0.0, 0.0]  # the fixture trace itself is untouched
    assert rt.path_thresholds("device", th) is th
    for path in ("web", "web_ir"):
        assert rt.path_thresholds(path, th)["eye_state"]["source"] == th["eye_state"]["web_source"]


def test_select_takes_one_video_per_kind_of_behaviour_then_the_shortest():
    videos = {
        "quiet-long": summary(900),
        "quiet-short": summary(100),
        "yawn": summary(400, events={"yawn": 1}),
        "l3": summary(800, alerts=[[50, 3, ["microsleep"]]]),
        "l3-again": summary(850, alerts=[[60, 3, ["microsleep"]]]),
    }
    assert rt.select(videos, 3) == ["l3", "quiet-short", "yawn"]
    assert rt.select(videos, 4) == ["l3", "l3-again", "quiet-short", "yawn"]  # filled with the shortest left


def test_differences_name_what_changed_and_ignore_float_noise():
    pinned = summary(alerts=[[50, 3, ["microsleep"]]], events={"microsleep": 1}, scores=(0.0, 25.0, 25.0, 40.0))
    assert rt.differences(pinned, copy.deepcopy(pinned)) == []
    noisy = {**pinned, "drowsy_score": [0.0, 25.01, 24.99, 40.0]}
    assert rt.differences(pinned, noisy) == []
    later = {**pinned, "alerts": [[51, 3, ["microsleep"]]]}  # one frame later is a change
    assert [d.split(":")[0] for d in rt.differences(pinned, later)] == ["alerts"]
    drifted = {**pinned, "drowsy_score": [0.0, 25.0, 25.0, 40.2]}
    assert [d.split(" ")[0] for d in rt.differences(pinned, drifted)] == ["drowsy_score"]


def test_traces_survive_the_fixture_file(tmp_path):
    n = 5
    cols = {c: np.arange(n, dtype=float) / 7 for c in rt.INPUT_COLUMNS if c != "brow"}  # an old trace: no brow
    path = tmp_path / "t.npz"
    rt.save_traces({"b": {"fps": 25.0, "n": n, "cols": cols}, "a": {"fps": 30.0, "n": n, "cols": cols}}, path)
    back = rt.load_traces(path)
    assert list(back) == ["a", "b"] and back["a"]["fps"] == 30.0 and back["b"]["n"] == n
    assert back["b"]["cols"]["ear"] == pytest.approx(cols["ear"], abs=1e-6)
    assert np.isnan(back["b"]["cols"]["brow"]).all()
