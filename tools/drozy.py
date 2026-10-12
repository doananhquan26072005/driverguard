"""DROZY for one question: risk.drowsy.l1 40 or 50, by the rule written down before the run (M101).

DROZY (ULg Multimodality Drowsiness Database): 14 subjects, up to 3 psychomotor vigilance tests of
10 min each, a fixed near-infrared camera (Kinect v2), one self-rated KSS score per test. The subjects
sit at a screen, they do not drive. The rule, the labels and what the result may be used for are in
eval/splits/drozy_l1_rule.md; this tool applies it and changes no threshold.

    python tools/drozy.py trace --workers 8          # blocks 2-12 once per video -> data/eval_traces/drozy/
    python tools/drozy.py l1 --out eval/results/drozy_l1.md

Traces hold numbers per frame only, never an image. The functions that label and decide are pure.
"""

from __future__ import annotations

import argparse
import sys
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from edge_agent.config import load_thresholds  # noqa: E402
from tools import uta_rldd  # noqa: E402
from tools.regression_traces import path_thresholds  # noqa: E402

DROZY_DIR = ROOT / "data" / "drozy" / "DROZY"
TRACE_DIR = ROOT / "data" / "eval_traces" / "drozy"
RULE = ROOT / "eval" / "splits" / "drozy_l1_rule.md"

# eval/splits/drozy_l1_rule.md, sections 2-5. Written before the run; not thresholds of the product.
AWAKE_KSS_MAX = 4
DROWSY_KSS_MIN = 7
L1_VALUES = (40, 50)
DECISION_PATH = "web"
PATHS = ("web", "device")
GATE_RELIABLE_MEDIAN = 0.80
GATE_AWAKE_HOURS = 1.5
GATE_DROWSY_VIDEOS = 8
GATE_AUC = 0.65
SLOW_FPS = 20.0  # tests recorded at 15 FPS (a recording bug of the dataset) are reported apart


def kss_table(text: str) -> dict[tuple[int, int], int]:
    """KSS.txt: one line per subject, one column per test. 0 = no score (test 7-1 did not happen)."""
    out = {}
    for subject, line in enumerate((ln for ln in text.splitlines() if ln.strip()), start=1):
        for test, value in enumerate(line.split(), start=1):
            out[(subject, test)] = int(value)
    return out


def label(kss: int | None) -> str | None:
    """awake / drowsy by the rule; "between" for KSS 5-6; None without a score."""
    if not kss:
        return None
    if kss <= AWAKE_KSS_MAX:
        return "awake"
    return "drowsy" if kss >= DROWSY_KSS_MIN else "between"


def videos(root: Path = DROZY_DIR) -> list[dict[str, Any]]:
    """The DROZY videos with their subject, test number and KSS score."""
    kss = kss_table((root / "KSS.txt").read_text(encoding="utf-8"))
    out = []
    for path in sorted((root / "videos_i8").glob("*.mp4")):
        subject, test = (int(x) for x in path.stem.split("-"))
        out.append(
            {"key": path.stem, "path": path, "subject": subject, "test": test, "kss": kss.get((subject, test)) or None}
        )
    return sorted(out, key=lambda v: (v["subject"], v["test"]))


def _replay_job(args: tuple[str, str, dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    key, path, thresholds = args
    tr = uta_rldd.load_trace(path)
    # block 5 decided again from the traced inputs with these thresholds: the path under test
    return key, uta_rldd.summarize(uta_rldd.replay_plus(tr, thresholds, False, None, "block5"), thresholds)


def run_rows(items: list[dict[str, Any]], thresholds: dict[str, Any], pool: Any = None) -> list[dict[str, Any]]:
    """Replay the stored trace of every video with these thresholds; one result row per video."""
    jobs = [(v["key"], str(uta_rldd.trace_file(TRACE_DIR, v["key"])), thresholds) for v in items]
    done = dict(pool.map(_replay_job, jobs, chunksize=1) if pool is not None else map(_replay_job, jobs))
    return [
        {**{k: v[k] for k in ("key", "subject", "test", "kss")}, "label": label(v["kss"]), **done[v["key"]]}
        for v in items
    ]


def auc(drowsy: list[float], awake: list[float]) -> float | None:
    """Chance that a drowsy video scores higher than an awake one (ties count half)."""
    pairs = [(d, a) for d in drowsy for a in awake if np.isfinite(d) and np.isfinite(a)]
    if not pairs:
        return None
    return float(np.mean([1.0 if d > a else 0.5 if d == a else 0.0 for d, a in pairs]))


def tally(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """What the rule counts on one configuration's rows (alerts of the drowsiness branch after the start-up)."""
    by = {name: [r for r in rows if r["label"] == name] for name in ("awake", "drowsy", "between")}
    hours = sum(r["score_s"] for r in by["awake"]) / 3600.0
    return {
        "videos": len(rows),
        "awake_videos": len(by["awake"]),
        "drowsy_videos": len(by["drowsy"]),
        "between_videos": len(by["between"]),
        "awake_hours": hours,
        "false_alarms": sum(r["a_drowsy"] for r in by["awake"]),
        "awake_alerted": sum(r["a_drowsy"] > 0 for r in by["awake"]),
        "drowsy_alerted": sum(r["a_drowsy"] > 0 for r in by["drowsy"]),
        "drowsy_l3": sum(r["a_drowsy_l3"] > 0 for r in by["drowsy"]),
        "between_alerted": sum(r["a_drowsy"] > 0 for r in by["between"]),
        "reliable_median": float(np.median([r["reliable"] for r in rows])) if rows else float("nan"),
        "auc": auc([r["score_mean"] for r in by["drowsy"]], [r["score_mean"] for r in by["awake"]]),
    }


def decide(at40: dict[str, Any], at50: dict[str, Any]) -> dict[str, Any]:
    """The rule of eval/splits/drozy_l1_rule.md on the two tallies of the decision path. Pure."""
    gates = {
        "G1 reliable face, median >= 80 %": at40["reliable_median"] >= GATE_RELIABLE_MEDIAN,
        "G2 >= 1.5 h awake and >= 8 drowsy videos": (
            at40["awake_hours"] >= GATE_AWAKE_HOURS and at40["drowsy_videos"] >= GATE_DROWSY_VIDEOS
        ),
        "G3 AUC of the mean score >= 0.65": at40["auc"] is not None and at40["auc"] >= GATE_AUC,
    }
    if not all(gates.values()):
        return {"gates": gates, "decision": 40, "why": "DROZY cannot decide (a condition of section 4 fails): keep 40"}
    f40, f50 = at40["false_alarms"], at50["false_alarms"]
    fewer = f50 <= f40 / 2 and f40 - f50 >= 3
    kept = at50["drowsy_alerted"] >= at40["drowsy_alerted"] - 1
    conditions = {
        "1 false alarms at least halved and at least 3 fewer": fewer,
        "2 at most one drowsy video loses its alert": kept,
    }
    if fewer and kept:
        return {"gates": gates, "conditions": conditions, "decision": 50, "why": "both conditions of section 5 hold"}
    return {
        "gates": gates,
        "conditions": conditions,
        "decision": 40,
        "why": "a condition of section 5 does not hold: keep 40",
    }


def _f(v: float | None, d: int = 2) -> str:
    return "–" if v is None or not np.isfinite(v) else f"{v:.{d}f}"


def report(results: dict[str, dict[int, list[dict[str, Any]]]], thresholds: dict[str, Any], source: str) -> str:
    """The Markdown report: both values of risk.drowsy.l1 and the verdict of the pre-declared rule."""
    tallies = {p: {v: tally(rows) for v, rows in by.items()} for p, by in results.items()}
    verdict = decide(tallies[DECISION_PATH][40], tallies[DECISION_PATH][50])
    lines = [
        "# DriverGuard - DROZY: risk.drowsy.l1 40 or 50, by a rule written before the run (M101)",
        "",
        f"Rule: `eval/splits/drozy_l1_rule.md`. {source}",
        "",
        "DROZY: 14 subjects at a screen (not driving), fixed near-infrared camera, one KSS score per 10 min test. "
        f"awake = KSS <= {AWAKE_KSS_MAX}, drowsy = KSS >= {DROWSY_KSS_MIN}; KSS 5-6 is listed apart. Blocks 7-12 "
        "replayed on per-frame numbers (no image kept) at l1 = 40 and 50 and nothing else. False alarms = "
        "drowsiness-branch alerts on awake videos after the 30 s start-up. The decision is taken on the `web` "
        "path (block 5 reads eyeBlink, as #/live); `device` (the eye CNN) is shown beside it.",
        "",
        f"## Verdict: l1 = {verdict['decision']}",
        "",
        f"{verdict['why']}.",
        "",
        "| Condition | Holds |",
        "|---|---|",
    ]
    for name, ok in {**verdict["gates"], **verdict.get("conditions", {})}.items():
        lines.append(f"| {name} | {'yes' if ok else 'no'} |")
    lines += [
        "",
        "## The counts",
        "",
        "| Path | l1 | Awake videos, hours | False alarms | Awake videos with one | Drowsy videos with an alert | reaching L3 "
        "| KSS 5-6 videos with an alert | AUC of the mean score | Reliable face, median |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for path in PATHS:
        for value in L1_VALUES:
            t = tallies[path][value]
            lines.append(
                f"| {path}{' (decides)' if path == DECISION_PATH else ''} | {value} | {t['awake_videos']}, "
                f"{_f(t['awake_hours'])} h | {t['false_alarms']} | {t['awake_alerted']} / {t['awake_videos']} | "
                f"{t['drowsy_alerted']} / {t['drowsy_videos']} | {t['drowsy_l3']} | "
                f"{t['between_alerted']} / {t['between_videos']} | {_f(t['auc'], 3)} | {_f(100 * t['reliable_median'], 1)} % |"
            )
    rows = results[DECISION_PATH][40]
    slow = [r for r in rows if r["fps"] < SLOW_FPS]
    lines += [
        "",
        f"Recorded at 15 FPS (kept in every number above): {len(slow)} of {len(rows)} videos; on the `web` path at "
        f"l1 = 40 they hold {sum(r['a_drowsy'] for r in slow if r['label'] == 'awake')} of the "
        f"{tallies[DECISION_PATH][40]['false_alarms']} false alarms.",
        "",
        "## Per video (`web` path)",
        "",
        "| Video | KSS | Label | FPS | Reliable face | Mean drowsy_score | Drowsiness alerts at 40 | at 50 | L3 at 40 |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    at50 = {r["key"]: r for r in results[DECISION_PATH][50]}
    for r in rows:
        lines.append(
            f"| {r['key']} | {r['kss'] or '–'} | {r['label'] or '–'} | {_f(r['fps'], 0)} | {_f(100 * r['reliable'], 1)} % | "
            f"{_f(r['score_mean'], 1)} | {r['a_drowsy']} | {at50[r['key']]['a_drowsy']} | {r['a_drowsy_l3']} |"
        )
    lines += [
        "",
        "## What this is not",
        "",
        "Not driving data, not the product's colour camera, 14 people, one run. A vote on `l1`, not a measurement "
        "of the PRD target. Nothing in `config/thresholds.yaml` was changed by this tool.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point (see the module doc). Returns the process exit code."""
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("study", choices=("trace", "l1"))
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--out", help="l1: where the report goes (default: printed)")
    args = p.parse_args(argv)
    base = load_thresholds()
    items = videos()
    pool = ProcessPoolExecutor(args.workers, mp_context=get_context("spawn")) if args.workers > 1 else None
    try:
        if args.study == "trace":
            TRACE_DIR.mkdir(parents=True, exist_ok=True)
            todo = [v for v in items if not uta_rldd.trace_file(TRACE_DIR, v["key"]).exists()]
            jobs = [(v["key"], str(v["path"]), str(uta_rldd.trace_file(TRACE_DIR, v["key"])), base, 60.0) for v in todo]
            for info in pool.map(uta_rldd._trace_job, jobs, chunksize=1) if pool else map(uta_rldd._trace_job, jobs):
                print(
                    f"[drozy] {info['key']}: {info.get('frames', 0)} frames, face {info.get('face', '–')} {info['error']}",
                    flush=True,
                )
            return 0
        if not RULE.exists():
            raise SystemExit(f"{RULE} is missing: the rule comes before the numbers")
        missing = [v["key"] for v in items if not uta_rldd.trace_file(TRACE_DIR, v["key"]).exists()]
        if missing:
            raise SystemExit(f"no trace for {missing}: run `python tools/drozy.py trace` first")
        results: dict[str, dict[int, list[dict[str, Any]]]] = {}
        for path in PATHS:
            results[path] = {}
            for value in L1_VALUES:
                th = uta_rldd.make_thresholds(path_thresholds(path, base), [f"risk.drowsy.l1={value}"])
                results[path][value] = run_rows(items, th, pool)
                print(f"[drozy] {path} l1={value}: {tally(results[path][value])}", file=sys.stderr, flush=True)
        from tools.metrics import provenance

        text = report(results, base, provenance([uta_rldd.trace_file(TRACE_DIR, items[0]["key"])]))
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
            print(f"[drozy] wrote {args.out}")
        else:
            print(text)
        return 0
    finally:
        if pool is not None:
            pool.shutdown()


if __name__ == "__main__":
    sys.exit(main())
