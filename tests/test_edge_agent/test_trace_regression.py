"""M34: blocks 5, 7-12 replayed on the fixture traces must give the pinned results.

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
    return rt.load_traces()


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


def test_fixture_covers_every_level_and_the_main_events(traces):
    expected = json.loads(rt.EXPECTED.read_text(encoding="utf-8"))["videos"]
    assert set(expected) == set(traces) and len(traces) >= 30
    assert {name.split("/")[0] for name in traces} == set(rt.SOURCES)
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


def test_every_update_of_the_pinned_results_has_a_reason():
    updates = json.loads(rt.EXPECTED.read_text(encoding="utf-8"))["updates"]
    assert updates and all(u["date"] and len(u["reason"]) >= 10 for u in updates)


# ---------------------------------------------------------------- pure helpers, fake data


def summary(frames=100, events=None, alerts=None, scores=(0.0, 0.0, 0.0, 0.0)):
    return {
        "frames": frames,
        "events": events or {},
        "alerts": alerts or [],
        "max_level": max((a[1] for a in alerts or []), default=0),
        "drowsy_score": list(scores),
    }


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
