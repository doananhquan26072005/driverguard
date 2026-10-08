"""M40 - Offline studies on the traces that already exist (tools/seq_eval.py). Nothing here changes
what the agent does: blocks 7-12 are replayed on per-frame numbers, no video is read again.

    python tools/trace_studies.py perclos  --out eval/results/perclos_p80.md
    python tools/trace_studies.py lighting --out eval/results/lighting.md
    python tools/trace_studies.py personal --out eval/results/personalization.md
    python tools/trace_studies.py glance   --out eval/results/glance_ratio.md

- perclos: what `perclos_60s` measures against the P80 definition of the literature (frames closed
  under each definition, how well each separates drowsy from alert, and what the events / alerts
  would be with the P80-equivalent EAR threshold). Thresholds are not changed.
- lighting: the existing results split by face brightness (`eval.brightness_bins`) and, for YawDD,
  by eyewear (from the file names). Groups of different datasets are different people and cameras:
  compare inside a dataset only.
- personal: does a per-driver baseline lower false alarms? YawDD is the only set here whose file
  names carry a person: the "enrolled" values are taken from that person's Normal clip
  (`eval.fake_enroll_s`), which is then left out of the scores, and the other clips are replayed
  with a fixed common eye baseline, the self-learnt one (what every evaluation used so far), and
  the fake-enrolled one.
- glance: how high `off_road_ratio` (M38, measured only) gets on drivers who are not distracted,
  i.e. how many false alarms a rule on it would raise at each threshold.

Traces are read from data/eval_traces/ (not in the repo: built once with `seq_eval.py trace`).
"""

from __future__ import annotations

import argparse
import copy
import pickle
import sys
from collections import Counter, defaultdict
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from edge_agent.config import PROJECT_ROOT  # noqa: E402
from tools.metrics import EvalConfig, ci_text, rate_ci  # noqa: E402
from tools.seq_eval import (  # noqa: E402
    auc,
    detected,
    label_runs,
    load_fl3d_labels,
    prf,
    replay,
    set_threshold,
    trace_seconds,
    yawdd_meta,
)

TRACE_DIR = PROJECT_ROOT / "data/eval_traces"
TRACE_FILES = {"fl3d": "fl3d_v2.pkl", "yawdd": "yawdd_v2.pkl", "sust": "sust_v2.pkl"}
DATASET_NOTE = {
    "fl3d": "FL3D / NITYMED: night driving, acted, 25 FPS, frame labels",
    "yawdd": "YawDD mirror camera: parked car, daylight, clip labels",
    "sust": "SUST-DDD: phone camera, real driving, 10 s clips, clip labels",
}


# --------------------------------------------------------------------------- shared helpers (pure)


def _f(v: float | None, d: int = 2) -> str:
    return "–" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:.{d}f}"


def _p(v: float | None, d: int = 1) -> str:
    return "–" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v * 100:.{d}f}%"


def _share(num: float, den: float) -> float | None:
    return num / den if den > 0 else None


def seconds(tr: dict) -> float:
    return trace_seconds(tr) if tr["fps"] else 0.0


def is_negative(dataset: str, key: str) -> bool | None:
    """True: the clip shows no drowsiness (an alert there is a false alarm). None: not decided by the clip."""
    if dataset == "sust":
        return not key.startswith("drowsiness/")
    if dataset == "yawdd":
        meta = yawdd_meta(key)
        return None if meta is None else meta["action"] != "yawning"
    return None


def run_filter(flags: np.ndarray, min_frames: int) -> np.ndarray:
    """Keep only runs of True at least `min_frames` long (drop fast blinks from a closed-frame mask)."""
    out = np.zeros(len(flags), dtype=bool)
    start = None
    for i, v in enumerate(list(flags) + [False]):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start >= min_frames:
                out[start:i] = True
            start = None
    return out


def brightness_bin(value: float, edges: Sequence[float]) -> str:
    """ "< 60", "60–100", ..., "≥ 140" for the bin `value` falls in; "unknown" for NaN."""
    if np.isnan(value):
        return "unknown"
    edges = sorted(edges)
    if value < edges[0]:
        return f"< {edges[0]:g}"
    for lo, hi in zip(edges, edges[1:]):
        if value < hi:
            return f"{lo:g}–{hi:g}"
    return f"≥ {edges[-1]:g}"


def bin_order(edges: Sequence[float]) -> list[str]:
    edges = sorted(edges)
    return [f"< {edges[0]:g}"] + [f"{a:g}–{b:g}" for a, b in zip(edges, edges[1:])] + [f"≥ {edges[-1]:g}", "unknown"]


def load_traces(names: Sequence[str], limit: int | None = None) -> dict[str, dict[str, dict]]:
    out = {}
    for name in names:
        path = TRACE_DIR / TRACE_FILES[name]
        if not path.exists():
            print(f"[studies] {path} missing: {name} left out", file=sys.stderr)
            continue
        data = {k: v for k, v in pickle.loads(path.read_bytes()).items() if not isinstance(v, str) and v["n"] > 0}
        if limit:
            keys = sorted(data)
            data = {k: data[k] for k in keys[:: max(1, len(keys) // limit)][:limit]}
        out[name] = data
    return out


def _job(args: tuple[str, dict, dict[str, Any], dict[str, float] | None]) -> tuple[str, dict]:
    key, tr, thresholds, profile = args
    return key, replay(tr, thresholds, "trace", profile=profile)


def replay_many(
    traces: dict[str, dict],
    thresholds: dict[str, Any],
    workers: int,
    profiles: dict[str, dict[str, float]] | None = None,
) -> dict[str, dict]:
    jobs = [(k, v, thresholds, (profiles or {}).get(k)) for k, v in traces.items()]
    if workers <= 1:
        return dict(map(_job, jobs))
    from multiprocessing import get_context

    with get_context("spawn").Pool(workers) as pool:
        return dict(pool.imap_unordered(_job, jobs, chunksize=8))


def what_if(thresholds: dict[str, Any], *assignments: str) -> dict[str, Any]:
    th = copy.deepcopy(thresholds)
    for a in assignments:
        set_threshold(th, a)
    return th


def alert_count(tr: dict, reasons: Sequence[str] | None = None) -> int:
    return sum(1 for _, _, rs in tr["alerts"] if reasons is None or any(r in reasons for r in rs))


# --------------------------------------------------------------------------- 1. PERCLOS definitions


def closed_masks(tr: dict, thresholds: dict[str, Any]) -> dict[str, np.ndarray]:
    """Per-frame closed flags under each PERCLOS definition, and which frames each one can judge.

    known: block 7 judged the eye (face reliable, pose in range). cnn: block 5 decided that frame.
    - current: what `perclos_60s` counts (EAR < perclos_close_ratio x baseline, CNN frames by
      probability, yawn / talking-masked frames skipped);
    - p50_ear: the same EAR test on EAR frames only, nothing masked;
    - p80: eye opening below `perclos_p80_aperture` on EAR frames only;
    - p80_noblink: p80 without closures shorter than `blink_max_s` (a variant in the literature).
    """
    c = tr["cols"]
    d = thresholds["drowsiness"]
    known = ~np.isnan(c["eye_closed"])
    cnn = known & ~np.isnan(c["p_closed"])
    ear_ok = known & ~cnn & ~np.isnan(c["ear"])
    ratio = np.divide(c["ear"], c["ear_base"], out=np.full(tr["n"], np.nan), where=c["ear_base"] > 0)
    ref = float(d["blink_closed_ref_ratio"])
    p80_ratio = ref + float(d["perclos_p80_aperture"]) * (1.0 - ref)  # not enrolled: closed EAR = ref x baseline
    masked = c["masked"] == 1
    cur_known = (ear_ok | cnn) & ~(masked & bool(d["perclos_use_mask"]))
    cur = np.where(cnn, c["p_closed"] >= float(d["eye"]["cnn_closed"]), ratio < float(d["perclos_close_ratio"]))
    p80 = ear_ok & (ratio < p80_ratio)
    min_frames = max(1, round(float(d["blink_max_s"]) * tr["fps"]))
    return {
        "known": known,
        "cnn": cnn,
        "current": cur_known & cur,
        "current_known": cur_known,
        "p50_ear": ear_ok & (ratio < float(d["perclos_close_ratio"])),
        "p80": p80,
        "p80_noblink": run_filter(p80, min_frames),
        "ear_known": ear_ok,
    }


DEFINITIONS = (
    ("current", "current_known", "current `perclos_60s` (EAR < 0.65 x baseline, or CNN; mask on)"),
    ("p50_ear", "ear_known", "same EAR test, EAR frames only, no mask"),
    ("p80", "ear_known", "P80: opening < 20 %, EAR frames only"),
    ("p80_noblink", "ear_known", "P80 without closures shorter than a blink"),
)


def clip_fractions(tr: dict, thresholds: dict[str, Any]) -> dict[str, float]:
    """Whole-clip closed fraction under each definition (NaN without judged frames), and CNN coverage."""
    m = closed_masks(tr, thresholds)
    out = {name: float(m[name].sum() / m[den].sum()) if m[den].sum() else np.nan for name, den, _ in DEFINITIONS}
    out["cnn_share"] = float(m["cnn"].sum() / m["known"].sum()) if m["known"].sum() else np.nan
    return out


def perclos_report(data: dict[str, dict[str, dict]], thresholds: dict[str, Any], workers: int) -> str:
    d = thresholds["drowsiness"]
    ref = float(d["blink_closed_ref_ratio"])
    p80_ratio = ref + float(d["perclos_p80_aperture"]) * (1.0 - ref)
    drowsy_thr = float(d["perclos_drowsy"])
    th_p80 = what_if(thresholds, f"drowsiness.perclos_close_ratio={p80_ratio:.4f}")
    lines = [
        "# DriverGuard - PERCLOS: the current definition against P80",
        "",
        "Blocks 7-12 replayed on the stored traces (`tools/trace_studies.py perclos`). No threshold was changed.",
        "",
        f"- **Current** `perclos_60s`: a frame is closed when EAR < {d['perclos_close_ratio']} x the open-eye baseline "
        f'(an opening below ~{(float(d["perclos_close_ratio"]) - ref) / (1 - ref) * 100:.0f} %, close to "P50"); frames '
        f"block 5 decided count on p_closed ≥ {d['eye']['cnn_closed']}; frames masked for yawning / talking are skipped.",
        f"- **P80** (the definition PERCLOS has in the literature): opening below "
        f"{float(d['perclos_p80_aperture']) * 100:.0f} %, i.e. EAR < {p80_ratio:.2f} x baseline without enrollment "
        f"(closed EAR taken as {ref} x baseline). EAR frames only: a CNN probability is not an opening.",
        "",
        "## 1. Share of frames closed under each definition",
        "",
        "Whole-clip fraction (the clips are shorter than, or about as long as, the 60 s window). Median and p90 over "
        f"the clips; last column: clips whose fraction is at or above `perclos_drowsy` ({drowsy_thr}).",
        "",
        "| Dataset | Clips | Definition | Median | p90 | Clips ≥ threshold |",
        "|---|---|---|---:|---:|---:|",
    ]
    replayed: dict[str, dict[str, dict]] = {}
    fractions: dict[str, dict[str, dict[str, float]]] = {}
    for name, traces in data.items():
        replayed[name] = replay_many(traces, thresholds, workers)
        fractions[name] = {k: clip_fractions(tr, thresholds) for k, tr in replayed[name].items()}
        groups: list[tuple[str, Callable[[str], bool]]] = [("all", lambda k: True)]
        if name == "sust":
            groups = [
                ("not drowsy", lambda k: is_negative("sust", k) is True),
                ("drowsy", lambda k: not is_negative("sust", k)),
            ]
        if name == "yawdd":
            groups = [
                ("normal / talking", lambda k: is_negative("yawdd", k) is True),
                ("yawning", lambda k: is_negative("yawdd", k) is False),
            ]
        for gname, keep in groups:
            keys = [k for k in fractions[name] if keep(k)]
            for col, _, text in DEFINITIONS:
                v = np.array([fractions[name][k][col] for k in keys])
                v = v[~np.isnan(v)]
                if len(v) == 0:
                    continue
                lines.append(
                    f"| {name} | {gname} ({len(v)}) | {text} | {_p(float(np.median(v)))} | "
                    f"{_p(float(np.percentile(v, 90)))} | {int(np.sum(v >= drowsy_thr))} ({_p(float(np.mean(v >= drowsy_thr)))}) |"
                )
    lines += [
        "",
        "Frames block 5 decided (not judged by P80), share of the judged frames: "
        + "; ".join(
            f"{name} {_p(float(np.nanmean([f['cnn_share'] for f in fr.values()])))} on average, "
            f"{_p(float(np.nanmax([f['cnn_share'] for f in fr.values()])))} in the worst clip"
            for name, fr in fractions.items()
        )
        + ".",
    ]

    # ---- separation
    lines += ["", "## 2. Does either definition separate drowsy from alert better?", ""]
    if "sust" in fractions:
        y = np.array([not is_negative("sust", k) for k in fractions["sust"]])
        lines += [
            f"SUST, per clip ({int(y.sum())} drowsy, {int((~y).sum())} not drowsy): AUC of the clip's closed fraction "
            "(0.5 = no information).",
            "",
            "| Definition | AUC | Median drowsy | Median not drowsy |",
            "|---|---:|---:|---:|",
        ]
        for col, _, text in DEFINITIONS:
            v = np.array([fractions["sust"][k][col] for k in fractions["sust"]])
            lines.append(
                f"| {text} | {_f(auc(v[y], v[~y]), 3)} | {_p(float(np.nanmedian(v[y])))} | {_p(float(np.nanmedian(v[~y])))} |"
            )
    if "fl3d" in replayed:
        try:
            labels = load_fl3d_labels()
        except OSError:
            labels = {}
        rows = defaultdict(list)
        for vid, tr in replayed["fl3d"].items():
            m = closed_masks(tr, thresholds)
            for frame, state in labels.get(vid, {}).items():
                if 0 <= frame < tr["n"]:
                    rows["label"].append(state)
                    for col, den, _ in DEFINITIONS:
                        rows[col].append(bool(m[col][frame]))
                        rows[den + ":" + col].append(bool(m[den][frame]))
        if rows:
            lab = np.array(rows["label"])
            pos, neg = lab == "microsleep", lab == "alert"
            lines += [
                "",
                f"FL3D, per labelled frame ({int(pos.sum())} `microsleep`, {int(neg.sum())} `alert`): a frame the "
                "definition cannot judge counts as not closed.",
                "",
                "| Definition | Microsleep frames closed (recall) | Alert frames closed (FPR) | Precision | Frames it can judge |",
                "|---|---:|---:|---:|---:|",
            ]
            for col, den, text in DEFINITIONS:
                pred = np.array(rows[col])
                sel = pos | neg
                r = prf(pred[sel], pos[sel])
                lines.append(
                    f"| {text} | {_p(r['recall'])} | {_p(r['fpr'])} | {_p(r['precision'])} | "
                    f"{_p(float(np.mean(np.array(rows[den + ':' + col])[sel])))} |"
                )

    # ---- running window: the two numbers the agent now reports side by side
    lines += [
        "",
        "## 3. The 60 s window as the agent computes it",
        "",
        "`perclos_60s` (current) and `perclos_p80_60s` (measured next to it since M40) on the frames where the "
        "current one is ready (`perclos_min_coverage_s` of eye data). Only clips long enough get there.",
        "",
        "| Dataset | Frames with a ready window | Current: median / p90 | P80: median / p90 | P80 eye-data seconds, median |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, trs in replayed.items():
        cur, p80, cov = [], [], []
        for tr in trs.values():
            ready = tr["cols"]["perclos_ready"] == 1
            cur.append(tr["cols"]["perclos"][ready])
            p80.append(tr["cols"]["perclos_p80"][ready])
            cov.append(tr["cols"]["perclos_p80_s"][ready])
        cur, p80, cov = np.concatenate(cur), np.concatenate(p80), np.concatenate(cov)
        if len(cur) == 0:
            lines.append(f"| {name} | 0 | – | – | – |")
            continue
        lines.append(
            f"| {name} | {len(cur)} | {_p(float(np.median(cur)))} / {_p(float(np.percentile(cur, 90)))} | "
            f"{_p(float(np.median(p80)))} / {_p(float(np.percentile(p80, 90)))} | {_f(float(np.median(cov)), 0)} |"
        )

    # ---- what the system would do with the P80-equivalent threshold
    lines += [
        "",
        f"## 4. What-if: the PERCLOS rule on the P80-equivalent threshold (`perclos_close_ratio` = {p80_ratio:.2f})",
        "",
        "Same thresholds otherwise (`perclos_drowsy`, `risk.drowsy.perclos_low / perclos_high` untouched), so this "
        "shows the direction, not a tuned result. CNN frames still count by probability here. Alerts per hour with an "
        "exact Poisson 95 % CI, on the clips where an alert is a false alarm (SUST not drowsy, YawDD normal / talking); "
        "FL3D has no such clips, all its alerts are listed.",
        "",
        "| Dataset | Clips | Hours | Setting | `perclos_high` events | `drowsy_score` alerts | All alerts | All alerts / hour (95% CI) |",
        "|---|---|---:|---|---:|---:|---:|---:|",
    ]
    for name, traces in data.items():
        alt = replay_many(traces, th_p80, workers)
        negative = [k for k in traces if is_negative(name, k) is True]
        keys, scope = (negative, "no drowsiness") if negative else (list(traces), "all")
        hours = sum(seconds(traces[k]) for k in keys) / 3600
        for label, run in (("current (0.65)", replayed[name]), (f"P80-equivalent ({p80_ratio:.2f})", alt)):
            events = sum(1 for k in keys for _, ev in run[k]["events"] if ev == "perclos_high")
            score = sum(alert_count(run[k], ("drowsy_score",)) for k in keys)
            total = sum(alert_count(run[k]) for k in keys)
            lines.append(
                f"| {name} | {scope} ({len(keys)}) | {hours:.2f} | {label} | {events} | {score} | {total} | "
                f"{ci_text(rate_ci(total, hours))} |"
            )
        if name == "sust":
            pos = [k for k in traces if is_negative(name, k) is False]
            for label, run in (("current (0.65)", replayed[name]), (f"P80-equivalent ({p80_ratio:.2f})", alt)):
                flagged = sum(alert_count(run[k]) > 0 for k in pos)
                lines.append(
                    f"| sust | drowsy ({len(pos)}) | {sum(seconds(traces[k]) for k in pos) / 3600:.2f} | {label} | "
                    f"{sum(1 for k in pos for _, ev in run[k]['events'] if ev == 'perclos_high')} | "
                    f"{sum(alert_count(run[k], ('drowsy_score',)) for k in pos)} | clips with an alert: {flagged} "
                    f"({_p(_share(flagged, len(pos)))}) | – |"
                )
    lines += [
        "",
        "## Reading it",
        "",
        "- These clips are short (SUST 10 s, YawDD ~20 s, FL3D ~30 s): the 60 s PERCLOS window rarely fills, so the "
        "PERCLOS rule seldom fires under either definition. A verdict on which definition detects drowsiness better "
        "needs long recordings of the same person awake and drowsy (UTA-RLDD).",
        "- If the thresholds are ever moved to P80, `perclos_drowsy` and `risk.drowsy.perclos_low / perclos_high` "
        "have to be tuned again on that data: they were set with the current definition.",
        "- Source: Abe T. PERCLOS-based technologies for detecting drowsiness: current evidence and future directions. "
        "SLEEP Advances 2023;4(1):zpad006. https://doi.org/10.1093/sleepadvances/zpad006",
    ]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- 2. lighting and eyewear


def video_stats(tr: dict, thresholds: dict[str, Any]) -> dict[str, float]:
    c = tr["cols"]
    known = ~np.isnan(c["eye_closed"])
    unavailable_s = float(thresholds["risk"]["unavailable"]["no_face_s"])
    bright = c["face_bright"][~np.isnan(c["face_bright"])]
    return {
        "bright": float(np.median(bright)) if len(bright) else np.nan,
        "seconds": seconds(tr),
        "frames": tr["n"],
        "face": float(np.nansum(c["face"])),
        "known": float(known.sum()),
        "cnn": float(np.sum(known & ~np.isnan(c["p_closed"]))),
        "unavailable": float(np.sum(c["no_face_s"] >= unavailable_s)) if unavailable_s > 0 else 0.0,
    }


def condition_rows(
    dataset: str, traces: dict[str, dict], thresholds: dict[str, Any], group_of: Callable[[str, dict], str]
) -> dict[str, dict[str, float]]:
    """Per group: minutes, coverage shares, false alarms on negative clips, detections on positive ones."""
    l3_s = float(thresholds["risk"]["microsleep_l3_s"])
    labels = load_fl3d_labels() if dataset == "fl3d" else {}
    out: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for key, tr in traces.items():
        st = video_stats(tr, thresholds)
        g = out[group_of(key, st)]
        g["videos"] += 1
        for k in ("seconds", "frames", "face", "known", "cnn", "unavailable"):
            g[k] += st[k]
        neg = is_negative(dataset, key)
        if neg is True:
            g["neg_clips"] += 1
            g["neg_s"] += st["seconds"]
            g["neg_alerts"] += alert_count(tr)
            g["neg_flagged"] += alert_count(tr) > 0
        elif neg is False:
            g["pos_clips"] += 1
            hit = alert_count(tr) > 0 if dataset == "sust" else any(ev == "yawn" for _, ev in tr["events"])
            g["pos_hit"] += hit
        if dataset == "fl3d" and key in labels:
            fps = tr["fps"]
            tol, gap = round(1.0 * fps), round(0.5 * fps)
            lb = labels[key]
            g["neg_s"] += sum(1 for s in lb.values() if s == "alert") / fps
            runs = label_runs(lb, gap)
            drowsy = [r for r in runs if r.label in ("microsleep", "yawning")]
            wide = round(3.0 * fps)
            for f, _, _ in tr["alerts"]:  # false = on an alert-labelled frame, away from every drowsy run
                near = any(r.start - wide <= f <= r.end + wide for r in drowsy)
                g["neg_alerts"] += (not near) and lb.get(f) == "alert"
            l3 = [f for f, lv, _ in tr["alerts"] if lv == 3]
            for r in runs:
                if r.label == "microsleep" and r.seconds(fps) >= l3_s:
                    g["pos_clips"] += 1
                    lo, hi = max(0, r.start - tol), min(tr["n"], r.end + tol + 1)
                    g["pos_hit"] += detected(r, l3, tol) is not None or bool(np.any(tr["cols"]["level"][lo:hi] >= 3))
    return out


def condition_table(dataset: str, rows: dict[str, dict[str, float]], order: Sequence[str]) -> list[str]:
    positive = {
        "fl3d": "microsleep runs reaching L3",
        "yawdd": "yawning clips with a yawn event",
        "sust": "drowsy clips with an alert",
    }
    lines = [
        f"| Group | Videos | Min | Face found | CNN-decided frames | Unavailable | False alarms / hour (95% CI) | Hours they are on | {positive[dataset][0].upper() + positive[dataset][1:]} |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name in [g for g in order if g in rows] + sorted(g for g in rows if g not in order):
        g = rows[name]
        hours = g["neg_s"] / 3600
        hit = (
            f"{int(g['pos_hit'])}/{int(g['pos_clips'])} ({_p(_share(g['pos_hit'], g['pos_clips']))})"
            if g["pos_clips"]
            else "–"
        )
        lines.append(
            f"| {name} | {int(g['videos'])} | {g['seconds'] / 60:.1f} | {_p(_share(g['face'], g['frames']))} | "
            f"{_p(_share(g['cnn'], g['known']))} | {_p(_share(g['unavailable'], g['frames']))} | "
            f"{ci_text(rate_ci(int(g['neg_alerts']), hours))} | {hours:.2f} | {hit} |"
        )
    return lines


def lighting_report(data: dict[str, dict[str, dict]], thresholds: dict[str, Any], workers: int) -> str:
    cfg = EvalConfig.from_dict(thresholds.get("eval"))
    edges = list(cfg.brightness_bins)
    low_light = thresholds["eye_state"]["low_light_brightness"]
    lines = [
        "# DriverGuard - results by lighting and eyewear",
        "",
        "Blocks 7-12 replayed on the stored traces (`tools/trace_studies.py lighting`); nothing was re-recorded. "
        "Face brightness = mean luminance (0-255) of the face before CLAHE, the number block 5 uses "
        f"(`eye_state.low_light_brightness` = {low_light}: below it EAR is not trusted and the eye CNN decides). "
        f"A video goes in the bin of its median face brightness (`eval.brightness_bins` = {edges}).",
        "",
        "**Do not compare across datasets.** Each dataset is other people, another camera and another kind of "
        'acting; a darker group in one dataset is not "the same drivers in less light". Inside a dataset the '
        "groups are still different people. The like-for-like answer, the same videos darkened / overexposed / "
        "blurred in RAM, is in eval/results/lighting_transforms.md (`tools/light_study.py`).",
        "",
        "False alarms: alerts on clips without drowsiness (SUST not drowsy, YawDD normal / talking; FL3D: alerts on "
        "frames labelled `alert`, more than 3 s from any microsleep / yawning run), per hour of such time, exact "
        "Poisson 95 % CI. Few minutes per group: most intervals are wide.",
    ]
    replayed = {name: replay_many(traces, thresholds, workers) for name, traces in data.items()}
    for name, traces in replayed.items():
        rows = condition_rows(name, traces, thresholds, lambda k, st: brightness_bin(st["bright"], edges))
        lines += ["", f"## {name}: by face brightness", "", DATASET_NOTE[name] + ".", ""]
        lines += condition_table(name, rows, bin_order(edges))
    if "fl3d" in replayed:
        labels = load_fl3d_labels()
        per_bin: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
        for vid, tr in replayed["fl3d"].items():
            c = tr["cols"]
            for frame, state in labels.get(vid, {}).items():
                if 0 <= frame < tr["n"] and state in ("microsleep", "alert"):
                    b = per_bin[brightness_bin(c["face_bright"][frame], edges)]
                    b["truth"].append(state == "microsleep")
                    b["pred"].append(c["eye_closed"][frame] == 1)
                    b["cnn"].append(not np.isnan(c["p_closed"][frame]))
        lines += [
            "",
            "### fl3d: eyes closed per frame, by the brightness of that frame",
            "",
            "Block 7 `eye_closed` against FL3D `microsleep` / `alert` frames. Frames, not videos, are binned here.",
            "",
            "| Face brightness | Frames | Precision | Recall | FPR | CNN-decided |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for b in [x for x in bin_order(edges) if x in per_bin]:
            truth, pred = np.array(per_bin[b]["truth"]), np.array(per_bin[b]["pred"])
            r = prf(pred, truth)
            lines.append(
                f"| {b} | {len(truth)} | {_p(r['precision'])} | {_p(r['recall'])} | {_p(r['fpr'])} | "
                f"{_p(float(np.mean(per_bin[b]['cnn'])))} |"
            )
    if "yawdd" in replayed:
        rows = condition_rows(
            "yawdd", replayed["yawdd"], thresholds, lambda k, st: (yawdd_meta(k) or {"eyewear": "unknown"})["eyewear"]
        )
        lines += [
            "",
            "## yawdd: by eyewear (from the file names)",
            "",
            "`NoGlasses` / `Glasses` / `SunGlasses` in the file name. The other datasets carry no such attribute.",
            "",
        ]
        lines += condition_table("yawdd", rows, ("no glasses", "glasses", "sunglasses"))
        by_reason: dict[str, Counter] = defaultdict(Counter)
        for key, tr in replayed["yawdd"].items():
            meta = yawdd_meta(key)
            if meta and meta["action"] != "yawning":
                for _, lv, rs in tr["alerts"]:
                    by_reason[meta["eyewear"]][f"L{lv} {','.join(rs)}"] += 1
        if by_reason:
            lines += [
                "",
                "False alarms by reason: "
                + "; ".join(
                    f"{g}: " + ", ".join(f"{r} {n}" for r, n in sorted(c.items())) for g, c in sorted(by_reason.items())
                )
                + ".",
            ]
    lines += [
        "",
        "## What is not covered",
        "",
        f"- Faces darker than the low-light threshold ({low_light}) are rare here: only the `< {edges[0]:g}` rows "
        "above, a few minutes in all (FL3D night clips are lit to 70-90). Infrared, backlight and glare: no video; "
        "`is_ir` is 0 on every trace of these datasets (not on dark colour video: the two dark own recordings "
        "read as infrared on 98-100 % of their frames).",
        "- Day / night per clip is not labelled in YawDD or SUST; FL3D is all night.",
        "- Sunglasses: YawDD has a few clips, but its labels are yawning only, so they say nothing about closed "
        "eyes behind dark lenses (NTHU-DDD is the set for that).",
    ]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- 3. per-driver baseline


def fake_profile(tr: dict, thresholds: dict[str, Any]) -> dict[str, float] | None:
    """What driver enrollment would have measured on the start of an awake clip: open-eye EAR,
    closed-mouth MAR and road pose as medians of the good frames (face reliable, eyes not shut,
    mouth closed) of the first `eval.fake_enroll_s`. None with less than a second of good frames."""
    cfg = EvalConfig.from_dict(thresholds.get("eval"))
    en = thresholds["enrollment"]
    c = tr["cols"]
    good = (c["t"] < cfg.fake_enroll_s) & (c["reliable"] == 1) & ~np.isnan(c["ear"]) & ~np.isnan(c["yaw"])
    good &= c["mar"] <= float(en["mar_closed_max"])
    blink = c.get("blink", np.full(tr["n"], np.nan))
    good &= np.isnan(blink) | (blink < float(en["eye_blink_shut"]))
    if good.sum() < tr["fps"]:
        return None
    d = thresholds["drowsiness"]["eye"]
    return {
        "ear_open": float(np.clip(np.median(c["ear"][good]), d["baseline_min"], d["baseline_max"])),
        "mar_closed": float(np.median(c["mar"][good])),
        "road_yaw": float(np.median(c["yaw"][good])),
        "road_pitch": float(np.median(c["pitch"][good])),
    }


def personal_scores(run: dict[str, dict], keys: Sequence[str]) -> dict[str, float]:
    s: dict[str, float] = defaultdict(float)
    for k in keys:
        tr, meta = run[k], yawdd_meta(k)
        events = Counter(ev for _, ev in tr["events"])
        s["false_microsleep"] += events["microsleep"]  # YawDD has no microsleep: every one is false
        if meta["action"] == "yawning":
            s["yawn_clips"] += 1
            s["yawn_hit"] += events["yawn"] > 0
        else:
            s["neg_clips"] += 1
            s["neg_s"] += seconds(tr)
            s["alerts"] += alert_count(tr)
            s["alerts_drowsy"] += alert_count(tr, ("microsleep", "drowsy_score", "trend"))
            s["alerts_off_road"] += alert_count(tr, ("off_road",))
            s["false_yawn"] += events["yawn"]
    return s


def personal_report(data: dict[str, dict[str, dict]], thresholds: dict[str, Any], workers: int) -> str:
    cfg = EvalConfig.from_dict(thresholds.get("eval"))
    traces = data.get("yawdd", {})
    by_subject: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for k in sorted(traces):
        meta = yawdd_meta(k)
        if meta:
            by_subject[meta["subject"]][meta["action"]].append(k)
    profiles: dict[str, dict[str, float]] = {}
    scored: list[str] = []
    skipped = 0
    for clips in by_subject.values():
        profile = None
        for k in clips.get("normal", []):
            profile = fake_profile(traces[k], thresholds)
            if profile is not None:
                source = k
                break
        if profile is None:
            skipped += 1
            continue
        for action, keys in clips.items():
            for k in keys:
                if k != source:  # the clip the baseline came from is never scored
                    profiles[k] = profile
                    scored.append(k)
    subset = {k: traces[k] for k in scored}
    settings = [
        ("fixed common eye baseline", what_if(thresholds, "drowsiness.eye.baseline_min_data_s=1000000"), None),
        ("self-learnt (as evaluated so far)", thresholds, None),
        ("fake-enrolled from the person's Normal clip", thresholds, profiles),
    ]
    runs = [(name, replay_many(subset, th, workers, prof)) for name, th, prof in settings]
    groups = [("all", scored)] + [
        (g, [k for k in scored if yawdd_meta(k)["eyewear"] == g]) for g in ("no glasses", "glasses", "sunglasses")
    ]
    lines = [
        "# DriverGuard - does a per-driver baseline lower false alarms? (YawDD)",
        "",
        "Blocks 7-12 replayed on the stored YawDD traces (`tools/trace_studies.py personal`). Driver enrollment (M9) "
        "never runs in the evaluations (the clips start at a simulated 60 km/h), so until now there was no number "
        "for it. Here its result is imitated: from the first "
        f"{cfg.fake_enroll_s:g} s (`eval.fake_enroll_s`) of a person's `Normal` clip, the medians of the good frames "
        "give the open-eye EAR, closed-mouth MAR and road pose, which are handed to blocks 7 and 8 the way a finished "
        "enrollment does. That clip is left out of every score below, in all three settings.",
        "",
        f"{len(scored)} clips of {len(by_subject) - skipped} people scored (left out: {skipped}, no Normal clip "
        "with a second of good frames). A person = gender + number + eyewear in the file name; whether the same "
        "number with and without glasses is one person was not checked.",
        "",
        "- **Fixed common eye baseline**: the open-eye EAR stays at `eye.baseline_init` for everyone (never learnt).",
        "- **Self-learnt**: the baseline is learnt during the clip (what every reported number used).",
        "- **Fake-enrolled**: the person's own values from their Normal clip, as described above.",
        "",
        "| Eyewear | Setting | Normal / talking clips | Hours | Alerts | of them drowsiness / off-road | Alerts / hour (95% CI) | False yawn events | False microsleep events | Yawning clips with a yawn event |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for gname, keys in groups:
        if not keys:
            continue
        for name, run in runs:
            s = personal_scores(run, keys)
            hours = s["neg_s"] / 3600
            lines.append(
                f"| {gname} | {name} | {int(s['neg_clips'])} | {hours:.2f} | {int(s['alerts'])} | "
                f"{int(s['alerts_drowsy'])} / {int(s['alerts_off_road'])} | {ci_text(rate_ci(int(s['alerts']), hours))} | "
                f"{int(s['false_yawn'])} | {int(s['false_microsleep'])} | "
                f"{int(s['yawn_hit'])}/{int(s['yawn_clips'])} ({_p(_share(s['yawn_hit'], s['yawn_clips']))}) |"
            )
    base, enrolled = runs[1][1], runs[2][1]
    changed = sorted(k for k in scored if base[k]["alerts"] != enrolled[k]["alerts"])
    lines += [
        "",
        f"Clips whose alerts differ between self-learnt and fake-enrolled: {len(changed)}"
        + (
            ": "
            + "; ".join(
                f"{Path(k).stem} ({len(base[k]['alerts'])} → {len(enrolled[k]['alerts'])})" for k in changed[:12]
            )
            if changed
            else ""
        )
        + ("; ..." if len(changed) > 12 else "")
        + ".",
        "",
        "## Reading it",
        "",
        "- YawDD is a parked car with clips of ~20 s: the false alarms here are almost all `off_road` at the start "
        "of a clip and yawn / microsleep events; PERCLOS and `drowsy_score` hardly ever get going. It can show "
        "whether the enrolled road pose and mouth baseline help; it cannot show the effect on drowsiness scoring.",
        "- The enrolled values come from another clip of the same person, not from the start of the scored clip: "
        "between two YawDD clips the person may sit differently, which a real enrollment at the start of the same "
        "trip would not suffer from. Extra `off_road` alerts with the enrolled road pose can come from that.",
        "- The CIs of the three settings overlap unless the counts differ a lot: with this little time a small "
        "difference is not a result.",
        "- FL3D and SUST file names carry no person, so they cannot be used. The main number has to come from "
        "UTA-RLDD (same person awake and drowsy, 10 min each).",
        '- Do not write "personalised" as a measured benefit in a report unless this table shows one.',
    ]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- 4. glance ratio on undistracted drivers


def glance_report(data: dict[str, dict[str, dict]], thresholds: dict[str, Any], workers: int) -> str:
    x = thresholds["distraction"]["glance"]
    marks = (0.2, 0.3, 0.4, 0.5, 0.6, 0.7)
    lines = [
        "# DriverGuard - off_road_ratio on drivers who are not distracted",
        "",
        "Blocks 7-12 replayed on the stored traces (`tools/trace_studies.py glance`). `off_road_ratio` (M38) is the "
        f"share of the last {x['window_s']} s spent looking off the road, once {x['min_coverage_s']} s of driving are in "
        'the window. It is only measured. None of these datasets labels distraction, so every clip counts as "not '
        'distracted": the table says how many clips a rule "ratio ≥ threshold" would have alerted on, i.e. its '
        "false-alarm side. Its detection side needs labelled glances (own recordings, DMD).",
        "",
        "| Dataset | Clips with a filled window | Hours | Highest ratio: median / p90 / max | "
        + " | ".join(f"Clips ≥ {m:g}" for m in marks)
        + " |",
        "|---|---:|---:|---:|" + "---:|" * len(marks),
    ]
    for name, traces in data.items():
        run = replay_many(traces, thresholds, workers)
        top, hours = [], 0.0
        for tr in run.values():
            if seconds(tr) < float(x["min_coverage_s"]):
                continue
            hours += seconds(tr) / 3600
            top.append(float(np.nanmax(tr["cols"]["off_road_ratio"])))
        if not top:
            lines.append(f"| {name} | 0 | – | – |" + " – |" * len(marks))
            continue
        v = np.array(top)
        lines.append(
            f"| {name} | {len(v)} | {hours:.2f} | {_f(float(np.median(v)))} / {_f(float(np.percentile(v, 90)))} / "
            f"{_f(float(v.max()))} | "
            + " | ".join(f"{int(np.sum(v >= m))} ({_p(float(np.mean(v >= m)), 0)})" for m in marks)
            + " |"
        )
    lines += [
        "",
        "SUST clips are 10 s, the minimum coverage: the window hardly ever fills there. FL3D drivers act drowsy: "
        "a dropped head is off the road too, so its ratios are not glances. YawDD is a parked car filmed from the "
        "mirror (people look around). None of them is normal driving with mirror checks, lane changes and "
        "junctions, which is where a glance rule would raise false alarms.",
    ]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- CLI


STUDIES = {
    "perclos": (perclos_report, ("fl3d", "yawdd", "sust")),
    "lighting": (lighting_report, ("fl3d", "yawdd", "sust")),
    "personal": (personal_report, ("yawdd",)),
    "glance": (glance_report, ("fl3d", "yawdd", "sust")),
}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("study", choices=sorted(STUDIES))
    p.add_argument("--out", default=None)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--limit", type=int, default=None, help="at most this many clips per dataset (a quick look)")
    p.add_argument("--set", action="append", default=[], help="what-if threshold applied to every replay")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = p.parse_args(argv)

    from edge_agent.config import load_thresholds

    thresholds = load_thresholds()
    for a in args.set:
        set_threshold(thresholds, a)
    fn, datasets = STUDIES[args.study]
    data = load_traces(datasets, args.limit)
    if not data:
        p.error(f"no traces under {TRACE_DIR}: build them with tools/seq_eval.py trace")
    text = fn(data, thresholds, args.workers)
    if args.set:
        head, _, rest = text.partition("\n\n")
        text = f"{head}\n\nWhat-if thresholds: {', '.join(args.set)}.\n\n{rest}"
    if args.limit:
        head, _, rest = text.partition("\n\n")
        text = f"{head}\n\nPARTIAL RUN: at most {args.limit} clips per dataset.\n\n{rest}"
    print(text)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
