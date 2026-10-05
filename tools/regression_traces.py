"""M34 - Regression test on traces: blocks 5, 7-12 replayed on a small fixed set, compared with pinned results.

Why: a change in block 7 once shifted an evaluation number slightly (blink AUC 0.624 -> 0.623) and no
unit test noticed; it was only seen by comparing reports by hand. Here a few dozen short videos, as
per-frame numbers only (EAR, MAR, pose, eyeBlink, brightness - never an image), live in the repo, and
tests/test_edge_agent/test_trace_regression.py replays the decision chain on them in CI. Any change
in events, alerts (frame, level, reasons) or drowsy_score is a red test.

    # once, on a machine that has the full traces of tools/seq_eval.py (data/ is not in the repo):
    python tools/regression_traces.py build

    # after an intended change of thresholds or logic: pin the new results, with the reason
    python tools/regression_traces.py update --reason "M32: third L1 in 10 min goes out as L2"

    # what the test runs
    python tools/regression_traces.py check

The fixture is tests/fixtures/regression/traces.npz (inputs) + expected.json (pinned results and the
log of updates). `update` belongs in the same commit as the change that caused it.
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from edge_agent.config import PROJECT_ROOT  # noqa: E402
from tools.seq_eval import replay  # noqa: E402

FIXTURE_DIR = PROJECT_ROOT / "tests/fixtures/regression"
TRACES = FIXTURE_DIR / "traces.npz"
EXPECTED = FIXTURE_DIR / "expected.json"

# What blocks 5, 7-12 read from a trace (tools/seq_eval.py replay, eye="block5"). Never an image.
INPUT_COLUMNS = "t face reliable ear mar pitch yaw p_cnn ear_l ear_r face_bright is_ir blink brow".split()
SOURCES = {"fl3d": "fl3d_v2.pkl", "yawdd": "yawdd_v2.pkl", "sust": "sust_v2.pkl"}  # under data/eval_traces/
PER_DATASET = {"fl3d": 8, "yawdd": 12, "sust": 16}
SCORE_POINTS = (0.25, 0.5, 0.75, 1.0)  # drowsy_score is pinned at these fractions of each video
SCORE_TOLERANCE = 0.05  # points of drowsy_score (0..100): float noise between platforms, not a change


# --------------------------------------------------------------------------- results of one video (pure)


def summarize(replayed: dict) -> dict[str, Any]:
    """What is pinned for one replayed video."""
    n, c = replayed["n"], replayed["cols"]
    frames = [min(n - 1, max(0, round(f * n) - 1)) for f in SCORE_POINTS]
    return {
        "frames": n,
        "events": dict(sorted(Counter(ev for _, ev in replayed["events"]).items())),
        "alerts": [[int(i), int(level), list(reasons)] for i, level, reasons in replayed["alerts"]],
        "max_level": int(np.nanmax(c["level"])) if n else 0,
        "drowsy_score": [round(float(c["drowsy_score"][i]), 3) for i in frames],
    }


def signatures(summary: dict[str, Any]) -> set[tuple]:
    """Kinds of behaviour a video shows; `select` wants each kind covered."""
    out: set[tuple] = {("event", ev) for ev in summary["events"]}
    out |= {("alert", level, tuple(reasons)) for _, level, reasons in summary["alerts"]}
    return out or {("quiet",)}


def select(summaries: dict[str, dict[str, Any]], count: int) -> list[str]:
    """`count` videos, shortest first: one per new kind of behaviour, then the shortest left."""
    by_length = sorted(summaries, key=lambda k: (summaries[k]["frames"], k))
    seen: set[tuple] = set()
    picked: list[str] = []
    for key in by_length:
        if len(picked) < count and not signatures(summaries[key]) <= seen:
            picked.append(key)
            seen |= signatures(summaries[key])
    picked += [k for k in by_length if k not in picked][: max(0, count - len(picked))]
    return sorted(picked)


def differences(expected: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    """Human-readable differences between pinned and replayed results of one video ([] = same)."""
    out = []
    for key in ("frames", "events", "alerts", "max_level"):
        if expected[key] != actual[key]:
            out.append(f"{key}: pinned {expected[key]}, now {actual[key]}")
    pinned, now = expected["drowsy_score"], actual["drowsy_score"]
    if len(pinned) != len(now) or any(abs(a - b) > SCORE_TOLERANCE for a, b in zip(pinned, now, strict=False)):
        out.append(f"drowsy_score at {list(SCORE_POINTS)} of the video: pinned {pinned}, now {now}")
    return out


# --------------------------------------------------------------------------- fixture file


def save_traces(traces: dict[str, dict], path: Path = TRACES) -> None:
    """Videos (name -> seq_eval trace) -> one compressed file: each input column concatenated, float32."""
    names = sorted(traces)
    arrays: dict[str, np.ndarray] = {
        "names": np.array(names),
        "lengths": np.array([traces[k]["n"] for k in names], dtype=np.int32),
        "fps": np.array([traces[k]["fps"] for k in names], dtype=np.float32),
    }
    for col in INPUT_COLUMNS:
        parts = [traces[k]["cols"].get(col, np.full(traces[k]["n"], np.nan)) for k in names]
        arrays[f"col_{col}"] = np.concatenate(parts).astype(np.float32)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **arrays)


def load_traces(path: Path = TRACES) -> dict[str, dict]:
    with np.load(path) as z:
        names, lengths, fps = [str(x) for x in z["names"]], z["lengths"], z["fps"]
        cols = {c: z[f"col_{c}"].astype(np.float64) for c in INPUT_COLUMNS}
    out, start = {}, 0
    for name, n, f in zip(names, lengths, fps, strict=True):
        out[name] = {"fps": float(f), "n": int(n), "cols": {c: v[start : start + n] for c, v in cols.items()}}
        start += int(n)
    return out


def replay_fixture(thresholds: dict[str, Any], traces: dict[str, dict] | None = None) -> dict[str, dict[str, Any]]:
    """Blocks 5, 7-12 on every fixture video -> its summary."""
    traces = load_traces() if traces is None else traces
    return {name: summarize(replay(tr, thresholds, "block5")) for name, tr in traces.items()}


def check(thresholds: dict[str, Any]) -> list[str]:
    """Differences between expected.json and a fresh replay, one line each ([] = the test passes)."""
    expected = json.loads(EXPECTED.read_text(encoding="utf-8"))["videos"]
    actual = replay_fixture(thresholds)
    out = [
        f"{name}: in {'the fixture' if name in actual else 'expected.json'} only"
        for name in set(expected) ^ set(actual)
    ]
    for name in sorted(set(expected) & set(actual)):
        out += [f"{name}: {d}" for d in differences(expected[name], actual[name])]
    return out


def write_expected(videos: dict[str, dict[str, Any]], reason: str, keep_log: bool) -> None:
    log = json.loads(EXPECTED.read_text(encoding="utf-8"))["updates"] if keep_log and EXPECTED.exists() else []
    log.append({"date": date.today().isoformat(), "reason": reason})
    doc = {
        "about": "Pinned results of tools/regression_traces.py. Do not edit by hand: run `update --reason`.",
        "updates": log,
        "videos": dict(sorted(videos.items())),
    }
    EXPECTED.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- CLI


def build(thresholds: dict[str, Any], source_dir: Path, reason: str) -> None:
    chosen: dict[str, dict] = {}
    for dataset, filename in SOURCES.items():
        traces = pickle.loads((source_dir / filename).read_bytes())
        traces = {k: v for k, v in traces.items() if not isinstance(v, str)}
        summaries = {k: summarize(replay(v, thresholds, "block5")) for k, v in traces.items()}
        for key in select(summaries, PER_DATASET[dataset]):
            chosen[f"{dataset}/{key}"] = traces[key]
        print(f"{dataset}: {PER_DATASET[dataset]} of {len(traces)} videos")
    save_traces(chosen)
    write_expected(replay_fixture(thresholds), reason, keep_log=False)  # from the stored float32 values
    frames = sum(v["n"] for v in chosen.values())
    print(f"{len(chosen)} videos, {frames} frames -> {TRACES} ({TRACES.stat().st_size / 1024:.0f} KB), {EXPECTED}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="pick the videos from the full traces and pin their results")
    b.add_argument("--source", default=str(PROJECT_ROOT / "data/eval_traces"))
    b.add_argument("--reason", default="fixture built")
    u = sub.add_parser("update", help="pin the current results of the fixture videos")
    u.add_argument("--reason", required=True, help="why the results changed (kept in expected.json)")
    sub.add_parser("check", help="replay and compare with the pinned results")
    args = p.parse_args(argv)
    from edge_agent.config import load_thresholds

    thresholds = load_thresholds()
    if args.cmd == "build":
        build(thresholds, Path(args.source), args.reason)
    elif args.cmd == "update":
        before = check(thresholds)
        write_expected(replay_fixture(thresholds), args.reason, keep_log=True)
        print(f"pinned; {len(before)} difference(s) from the previous results" + "".join(f"\n  {d}" for d in before))
    else:
        diffs = check(thresholds)
        print("\n".join(diffs) if diffs else "same as pinned")
        return 1 if diffs else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
