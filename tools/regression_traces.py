"""M34 - Regression test on traces: blocks 5, 7-12 replayed on a small fixed set, compared with pinned results.

Why: a change in block 7 once shifted an evaluation number slightly (blink AUC 0.624 -> 0.623) and no
unit test noticed; it was only seen by comparing reports by hand. Here a few dozen short videos, as
per-frame numbers only (EAR, MAR, pose, eyeBlink, brightness - never an image), live in the repo, and
tests/test_edge_agent/test_trace_regression.py replays the decision chain on them in CI. Any change
in events, alerts (frame, level, reasons) or drowsy_score is a red test.

    # once, on a machine that has the full traces of tools/seq_eval.py (data/ is not in the repo):
    python tools/regression_traces.py build
    python tools/regression_traces.py build-extra     # the videos with phone and frame-quality columns

    # after an intended change of thresholds or logic: pin the new results, with the reason
    python tools/regression_traces.py update --reason "M32: third L1 in 10 min goes out as L2"

    # what the test runs
    python tools/regression_traces.py check

The fixture is tests/fixtures/regression/traces.npz + traces_phone_quality.npz (inputs) + expected.json
(pinned results and the log of updates). `update` belongs in the same commit as the change that caused it.

M86: every video is replayed on three paths (PATHS), because the product is the page and the first
fixture only pinned the device path. `web` is block 5 as the page runs it (eye_state.web_source: the
eyeBlink blendshape instead of the eye CNN). `web_ir` is the same with every frame taken for infrared,
which is also what a dark colour image looks like to block 2: eyeBlink then decides every frame. The
second file holds 3MDAD videos, the only traces with the phone flag and the frame-quality numbers, so
the phone branch and the "monitoring paused" gate are pinned too.
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
EXTRA_TRACES = FIXTURE_DIR / "traces_phone_quality.npz"
EXPECTED = FIXTURE_DIR / "expected.json"
PATHS = ("device", "web", "web_ir")  # expected.json: "videos" is the device path, "paths" the others

# What blocks 5, 7-12 read from a trace (tools/seq_eval.py replay, eye="block5"). Never an image.
INPUT_COLUMNS = "t face reliable ear mar pitch yaw p_cnn ear_l ear_r face_bright is_ir blink brow".split()
SOURCES = {"fl3d": "fl3d_v2.pkl", "yawdd": "yawdd_v2.pkl", "sust": "sust_v2.pkl"}  # under data/eval_traces/
PER_DATASET = {"fl3d": 8, "yawdd": 12, "sust": 16}
# The second file: what the phone branch (block 8), the quality gate (M43) and the gaze rule (M55) read.
EXTRA_COLUMNS = INPUT_COLUMNS + "phone_flag phone_kind scene_bright scene_contrast sharpness iris_y_l iris_y_r".split()
EXTRA_SOURCES = {"3mdad": "3mdad_day.pkl"}
EXTRA_PER_DATASET = {"3mdad": 8}
SCORE_POINTS = (0.25, 0.5, 0.75, 1.0)  # drowsy_score is pinned at these fractions of each video
SCORE_TOLERANCE = 0.05  # points of drowsy_score (0..100): float noise between platforms, not a change


# --------------------------------------------------------------------------- results of one video (pure)


def summarize(replayed: dict, paused: dict[str, int] | None = None) -> dict[str, Any]:
    """What is pinned for one replayed video. paused: frames without monitoring, by reason."""
    n, c = replayed["n"], replayed["cols"]
    frames = [min(n - 1, max(0, round(f * n) - 1)) for f in SCORE_POINTS]
    return {
        "frames": n,
        "events": dict(sorted(Counter(ev for _, ev in replayed["events"]).items())),
        "alerts": [[int(i), int(level), list(reasons)] for i, level, reasons in replayed["alerts"]],
        "max_level": int(np.nanmax(c["level"])) if n else 0,
        "drowsy_score": [round(float(c["drowsy_score"][i]), 3) for i in frames],
        "paused": dict(sorted((paused or {}).items())),
    }


def replay_summary(tr: dict, thresholds: dict[str, Any]) -> dict[str, Any]:
    """Blocks 5, 7-12 on one trace -> its summary, with the frames monitoring was paused on."""
    paused: Counter = Counter()

    def watch(_i: int, _pipeline: Any, result: Any) -> None:
        if result.risk.unavailable:
            paused[result.risk.unavailable_reason or "no_face"] += 1

    return summarize(replay(tr, thresholds, "block5", observe=watch), dict(paused))


def path_thresholds(path: str, thresholds: dict[str, Any]) -> dict[str, Any]:
    """The thresholds this path of the product runs with (PATHS, module docstring)."""
    if path == "device":
        return thresholds
    from edge_agent.web.bridge import web_thresholds

    return web_thresholds(base=thresholds)[0]


def path_trace(path: str, tr: dict) -> dict:
    """The video as this path sees it: on web_ir every frame is taken for infrared."""
    if path != "web_ir":
        return tr
    return {**tr, "cols": {**tr["cols"], "is_ir": np.ones(tr["n"])}}


def signatures(summary: dict[str, Any]) -> set[tuple]:
    """Kinds of behaviour a video shows; `select` wants each kind covered."""
    out: set[tuple] = {("event", ev) for ev in summary["events"]}
    out |= {("alert", level, tuple(reasons)) for _, level, reasons in summary["alerts"]}
    out |= {("paused", reason) for reason in summary.get("paused", {})}
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
    for key in ("frames", "events", "alerts", "max_level", "paused"):
        if expected.get(key) != actual[key]:
            out.append(f"{key}: pinned {expected.get(key)}, now {actual[key]}")
    pinned, now = expected["drowsy_score"], actual["drowsy_score"]
    if len(pinned) != len(now) or any(abs(a - b) > SCORE_TOLERANCE for a, b in zip(pinned, now, strict=False)):
        out.append(f"drowsy_score at {list(SCORE_POINTS)} of the video: pinned {pinned}, now {now}")
    return out


# --------------------------------------------------------------------------- fixture file


def save_traces(traces: dict[str, dict], path: Path = TRACES, columns: list[str] = INPUT_COLUMNS) -> None:
    """Videos (name -> seq_eval trace) -> one compressed file: each input column concatenated, float32."""
    names = sorted(traces)
    arrays: dict[str, np.ndarray] = {
        "names": np.array(names),
        "lengths": np.array([traces[k]["n"] for k in names], dtype=np.int32),
        "fps": np.array([traces[k]["fps"] for k in names], dtype=np.float32),
    }
    for col in columns:
        parts = [traces[k]["cols"].get(col, np.full(traces[k]["n"], np.nan)) for k in names]
        arrays[f"col_{col}"] = np.concatenate(parts).astype(np.float32)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **arrays)


def load_traces(path: Path = TRACES, columns: list[str] = INPUT_COLUMNS) -> dict[str, dict]:
    with np.load(path) as z:
        names, lengths, fps = [str(x) for x in z["names"]], z["lengths"], z["fps"]
        cols = {c: z[f"col_{c}"].astype(np.float64) for c in columns}
    out, start = {}, 0
    for name, n, f in zip(names, lengths, fps, strict=True):
        out[name] = {"fps": float(f), "n": int(n), "cols": {c: v[start : start + n] for c, v in cols.items()}}
        start += int(n)
    return out


def load_fixture() -> dict[str, dict]:
    """Every fixture video of both files (the second one is absent until `build-extra` has run)."""
    extra = load_traces(EXTRA_TRACES, EXTRA_COLUMNS) if EXTRA_TRACES.exists() else {}
    return {**load_traces(), **extra}


def replay_fixture(
    thresholds: dict[str, Any], traces: dict[str, dict] | None = None, paths: tuple[str, ...] = PATHS
) -> dict[str, dict[str, dict[str, Any]]]:
    """Blocks 5, 7-12 on every fixture video, on each path -> path -> video -> summary."""
    traces = load_fixture() if traces is None else traces
    out = {}
    for path in paths:
        th = path_thresholds(path, thresholds)
        out[path] = {name: replay_summary(path_trace(path, tr), th) for name, tr in traces.items()}
    return out


def pinned() -> dict[str, dict[str, dict[str, Any]]]:
    """expected.json as path -> video -> summary."""
    doc = json.loads(EXPECTED.read_text(encoding="utf-8"))
    return {"device": doc["videos"], **doc.get("paths", {})}


def check(thresholds: dict[str, Any], paths: tuple[str, ...] = PATHS) -> list[str]:
    """Differences between expected.json and a fresh replay, one line each ([] = the test passes)."""
    expected, actual = pinned(), replay_fixture(thresholds, paths=paths)
    out = []
    for path in paths:
        want, got = expected.get(path, {}), actual[path]
        out += [
            f"[{path}] {name}: in {'the fixture' if name in got else 'expected.json'} only"
            for name in sorted(set(want) ^ set(got))
        ]
        for name in sorted(set(want) & set(got)):
            out += [f"[{path}] {name}: {d}" for d in differences(want[name], got[name])]
    return out


def write_expected(results: dict[str, dict[str, dict[str, Any]]], reason: str, keep_log: bool) -> None:
    log = json.loads(EXPECTED.read_text(encoding="utf-8"))["updates"] if keep_log and EXPECTED.exists() else []
    log.append({"date": date.today().isoformat(), "reason": reason})
    doc = {
        "about": "Pinned results of tools/regression_traces.py. Do not edit by hand: run `update --reason`.",
        "updates": log,
        "videos": dict(sorted(results["device"].items())),
        "paths": {path: dict(sorted(v.items())) for path, v in results.items() if path != "device"},
    }
    EXPECTED.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- CLI


def build(thresholds: dict[str, Any], source_dir: Path, reason: str, extra: bool = False) -> None:
    """Pick the videos of one fixture file from the full traces and pin every result again.
    extra: the phone / quality file; the first file and its videos are left as they are."""
    sources, per_dataset = (EXTRA_SOURCES, EXTRA_PER_DATASET) if extra else (SOURCES, PER_DATASET)
    path, columns = (EXTRA_TRACES, EXTRA_COLUMNS) if extra else (TRACES, INPUT_COLUMNS)
    chosen: dict[str, dict] = {}
    for dataset, filename in sources.items():
        traces = pickle.loads((source_dir / filename).read_bytes())
        traces = {k: v for k, v in traces.items() if not isinstance(v, str)}
        summaries = {k: replay_summary(v, thresholds) for k, v in traces.items()}
        for key in select(summaries, per_dataset[dataset]):
            chosen[f"{dataset}/{key}"] = traces[key]
        print(f"{dataset}: {per_dataset[dataset]} of {len(traces)} videos")
    save_traces(chosen, path, columns)
    write_expected(replay_fixture(thresholds), reason, keep_log=extra)  # from the stored float32 values
    frames = sum(v["n"] for v in chosen.values())
    print(f"{len(chosen)} videos, {frames} frames -> {path} ({path.stat().st_size / 1024:.0f} KB), {EXPECTED}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="pick the videos from the full traces and pin their results")
    b.add_argument("--source", default=str(PROJECT_ROOT / "data/eval_traces"))
    b.add_argument("--reason", default="fixture built")
    x = sub.add_parser("build-extra", help="pick the videos with phone and frame-quality columns, pin every result")
    x.add_argument("--source", default=str(PROJECT_ROOT / "data/eval_traces"))
    x.add_argument("--reason", required=True)
    u = sub.add_parser("update", help="pin the current results of the fixture videos")
    u.add_argument("--reason", required=True, help="why the results changed (kept in expected.json)")
    sub.add_parser("check", help="replay and compare with the pinned results")
    args = p.parse_args(argv)
    from edge_agent.config import load_thresholds

    thresholds = load_thresholds()
    if args.cmd in ("build", "build-extra"):
        build(thresholds, Path(args.source), args.reason, extra=args.cmd == "build-extra")
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
