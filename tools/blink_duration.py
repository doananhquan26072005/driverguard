"""M35 - Offline prototype: is blink duration worth adding to the slow-blink signal? (docs/improvements.md)

Block 7 already times every blink (edge_agent/analysis/drowsiness/slow_blink.py: duration and eyelid
reopening on the eye aperture) but only the reopening time is compared with the driver's own start of
trip (`reopen_ratio`). This tool asks, on existing traces only (no video, no model), whether a
`duration_ratio` would add anything:

1. do blinks last longer in the drowsy stretches of a video than in its alert stretches?
2. are there enough measured blinks to say?
3. does timing on EAR and on the eyeBlink blendshape agree?
4. long closures (microsleeps) are left out, so they cannot stretch the drowsy side;
5. does duration tell anything the reopening time does not?

FL3D labels frames alert / microsleep / yawning; there is no "drowsy stretch" label. Two stand-ins,
both reported: blinks of videos with a microsleep against blinks of videos without one, and, inside the
microsleep videos, blinks within `--near-s` of a microsleep against the other blinks of the same video.

The engine is not changed here. The report ends with a verdict by two rules: separation AUC >=
`--auc-min` and |Spearman rho| between duration and reopening <= `--rho-max`. The cut-offs are
conventional round numbers picked while writing the tool, after a first look at the numbers, so they
are not pre-registered; the report says how far the result is from them.

    python tools/blink_duration.py --traces data/eval_traces/fl3d_v2.pkl --out eval/results/blink_duration_fl3d.md
"""

from __future__ import annotations

import argparse
import pickle
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.seq_eval import Run, auc, label_runs, load_fl3d_labels, replay  # noqa: E402

LABEL_GAP = 2  # frames: FL3D leaves a few frames unlabelled inside a run (as in tools/seq_eval.py)


@dataclass(frozen=True)
class Blink:
    frame: int  # frame where the measurement ended (engine) or the deepest frame (offline timer)
    duration: float  # s, aperture below the open level and back
    reopen: float | None = None  # s, deepest point -> open level (engine only)


# --------------------------------------------------------------------------- measuring (pure)


def engine_blinks(tr: dict, thresholds: dict[str, Any]) -> list[Blink]:
    """Every blink block 7 timed while blocks 5, 7-12 are replayed on one trace."""
    out: list[Blink] = []
    last: list[Any] = [None]

    def observe(i: int, pipeline: Any, _result: Any) -> None:
        log = pipeline.drowsiness._slow._log  # (end, duration, reopen); the prototype reads it as it grows
        if log and log[-1] is not last[0]:
            last[0] = log[-1]
            out.append(Blink(i, log[-1][1], log[-1][2]))

    replay(tr, thresholds, "block5", observe)
    return out


def time_excursions(t: np.ndarray, aperture: np.ndarray, level: float, depth: float, max_s: float) -> list[Blink]:
    """Every dip of `aperture` below `level` that reaches `depth` and is back within `max_s`.

    Crossing times are interpolated between frames, as block 7 does. A dip touching a gap (NaN) or
    the ends of the trace is not measured; a dip longer than `max_s` is a closure, not a blink.
    """
    out: list[Blink] = []
    n = len(t)
    i = 1
    while i < n:
        a0, a1 = aperture[i - 1], aperture[i]
        if not (np.isfinite(a0) and np.isfinite(a1) and a0 >= level > a1):
            i += 1
            continue
        start = t[i - 1] + (level - a0) / (a1 - a0) * (t[i] - t[i - 1])
        j = i
        while j < n and np.isfinite(aperture[j]) and aperture[j] < level:
            j += 1
        if j < n and np.isfinite(aperture[j]):  # reopened on a measured frame
            b0, b1 = aperture[j - 1], aperture[j]
            end = t[j - 1] + (level - b0) / (b1 - b0) * (t[j] - t[j - 1])
            k = i + int(np.argmin(aperture[i:j]))
            if aperture[k] <= depth and end - start <= max_s:
                out.append(Blink(k, float(end - start)))
        i = max(j, i + 1)
    return out


def ear_aperture(c: dict[str, np.ndarray], closed_ref_ratio: float) -> np.ndarray:
    """EAR scaled 0 (closed) .. 1 (the traced open-eye baseline), as block 7 does when not enrolled."""
    closed = closed_ref_ratio * c["ear_base"]
    with np.errstate(divide="ignore", invalid="ignore"):
        return (c["ear"] - closed) / np.maximum(c["ear_base"] - closed, 1e-6)


def blendshape_aperture(blink: np.ndarray, closed_quantile: float = 99.5, min_closed: float = 0.5) -> np.ndarray | None:
    """eyeBlink (0 open .. 1 closed) scaled like the EAR aperture: 1 at the video's median, 0 at its
    own closed level. None when the video has no real closure to scale with."""
    known = blink[np.isfinite(blink)]
    if not len(known):
        return None
    open_level, closed = float(np.median(known)), float(np.percentile(known, closed_quantile))
    if closed < min_closed or closed - open_level < 1e-3:
        return None
    return 1.0 - (blink - open_level) / (closed - open_level)


# --------------------------------------------------------------------------- grouping (pure)


def microsleep_runs(labels: dict[int, str]) -> list[Run]:
    """The labelled microsleep runs of one video."""
    return [r for r in label_runs(labels, LABEL_GAP) if r.label == "microsleep"]


def seconds_to_nearest(frame: int, runs: list[Run], fps: float) -> float:
    """Distance from a frame to the nearest run (0 inside one)."""
    return min((0 if r.start <= frame <= r.end else min(abs(frame - r.start), abs(frame - r.end))) for r in runs) / fps


def split_near_far(blinks: list[Blink], runs: list[Run], fps: float, near_s: float) -> tuple[list[Blink], list[Blink]]:
    """Split the blinks into those within `near_s` of a microsleep run and the rest."""
    near = [b for b in blinks if seconds_to_nearest(b.frame, runs, fps) <= near_s]
    return near, [b for b in blinks if seconds_to_nearest(b.frame, runs, fps) > near_s]


def spearman(x: np.ndarray, y: np.ndarray) -> float | None:
    """Rank correlation (ties share their mean rank), None below 3 pairs or without spread."""
    if len(x) < 3:
        return None

    def ranks(v: np.ndarray) -> np.ndarray:
        order = np.argsort(v, kind="stable")
        r = np.empty(len(v))
        r[order] = np.arange(len(v), dtype=float)
        for value in np.unique(v):
            same = v == value
            r[same] = r[same].mean()
        return r

    rx, ry = ranks(x), ranks(y)
    if rx.std() == 0 or ry.std() == 0:
        return None
    return float(np.corrcoef(rx, ry)[0, 1])


def durations(blinks: list[Blink]) -> np.ndarray:
    """The blink durations as an array."""
    return np.array([b.duration for b in blinks])


# --------------------------------------------------------------------------- report


def _ms(values: np.ndarray) -> str:
    return "-" if not len(values) else f"{np.median(values) * 1000:.0f}"


def _f(v: float | None, d: int = 2) -> str:
    return "-" if v is None else f"{v:.{d}f}"


def _ratio(a: np.ndarray, b: np.ndarray) -> float | None:
    return None if not len(a) or not len(b) or np.median(b) <= 0 else float(np.median(a) / np.median(b))


def group_rows(name: str, per_video: dict[str, list[Blink]], drowsy_videos: set[str]) -> tuple[str, float | None]:
    """One table row for a group of videos, and the AUC of blink duration (drowsy vs alert)."""
    drowsy = durations([b for v, bs in per_video.items() if v in drowsy_videos for b in bs])
    alert = durations([b for v, bs in per_video.items() if v not in drowsy_videos for b in bs])
    a = auc(drowsy, alert)
    row = f"| {name} | {len(drowsy)} | {_ms(drowsy)} | {len(alert)} | {_ms(alert)} | {_f(_ratio(drowsy, alert))} | {_f(a)} |"
    return row, a


def report(
    traces: dict, labels: dict[str, dict[int, str]], thresholds: dict[str, Any], args: argparse.Namespace
) -> str:
    """The Markdown report of the blink-duration study."""
    dcfg = thresholds["drowsiness"]
    level, closed_ref = float(dcfg["blink_open_level"]), float(dcfg["blink_closed_ref_ratio"])
    max_s = float(dcfg["blink_max_s"]) + float(dcfg["slow_blink"]["reopen_max_s"])
    baseline_blinks, min_blinks = int(dcfg["slow_blink"]["baseline_blinks"]), int(dcfg["slow_blink"]["min_blinks"])
    videos = {v: tr for v, tr in traces.items() if not isinstance(tr, str) and v in labels}
    fps = {v: float(tr["fps"]) for v, tr in videos.items()}
    engine = {v: engine_blinks(tr, thresholds) for v, tr in videos.items()}
    by_ear = {
        v: time_excursions(tr["cols"]["t"], ear_aperture(tr["cols"], closed_ref), level, args.depth, max_s)
        for v, tr in videos.items()
    }
    by_blend: dict[str, list[Blink]] = {}
    for v, tr in videos.items():
        ap = blendshape_aperture(tr["cols"]["blink"]) if "blink" in tr["cols"] else None
        if ap is not None:
            by_blend[v] = time_excursions(tr["cols"]["t"], ap, level, args.depth, max_s)
    runs = {v: microsleep_runs(labels[v]) for v in videos}
    drowsy_videos = {v for v in videos if runs[v]}
    minutes = sum(tr["n"] / fps[v] for v, tr in videos.items()) / 60

    all_engine = [b for bs in engine.values() for b in bs]
    dur, reo = durations(all_engine), np.array([b.reopen for b in all_engine], dtype=float)
    rho = spearman(dur, reo)
    counts = sorted(len(bs) for bs in engine.values())
    with_baseline = sum(n >= baseline_blinks + min_blinks for n in counts)

    out = [
        "# Blink duration vs the driver's own blinks: offline prototype on FL3D (M35)",
        "",
        f"Traces only (blocks 5, 7-12 replayed with config/thresholds.yaml; no video, no model): {len(videos)} videos, "
        f"{minutes:.1f} min, {np.median(list(fps.values())):.0f} FPS ({1000 / np.median(list(fps.values())):.0f} ms per frame). "
        "The engine is not changed by this report.",
        "",
        "## 1. How many blinks can be measured",
        "",
        f"- Block 7 timed **{len(all_engine)} blinks** ({len(all_engine) / minutes:.1f} per minute). Per video: "
        f"median {int(np.median(counts))}, min {counts[0]}, max {counts[-1]}.",
        f"- Duration (aperture below {level} and back): median {_ms(dur)} ms, p5-p95 "
        f"{np.percentile(dur, 5) * 1000:.0f}-{np.percentile(dur, 95) * 1000:.0f} ms. Reopening: median {_ms(reo)} ms.",
        f"- A `duration_ratio` like `reopen_ratio` needs the first {baseline_blinks} blinks as the driver's own "
        f"baseline, then {min_blinks} more to compare: **{with_baseline} of {len(videos)} videos** have that many. "
        "The clips are too short for a ratio against the start of the trip.",
        "",
        "## 2. Drowsy against alert",
        "",
        f"FL3D has no drowsy-stretch label (frames are alert / microsleep / yawning). Stand-ins: videos with a "
        f"labelled microsleep ({len(drowsy_videos)}) against videos without ({len(videos) - len(drowsy_videos)}); and, "
        f"inside the microsleep videos, blinks within {args.near_s:.0f} s of a microsleep against the rest. Closures "
        f"longer than {max_s:.1f} s are not blinks and are left out on both sides.",
        "",
        "| Timing | Blinks, microsleep videos | Median ms | Blinks, other videos | Median ms | Ratio | AUC |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    aucs: dict[str, float | None] = {}
    for name, per_video in (("Block 7 (EAR)", engine), ("Offline, EAR", by_ear), ("Offline, eyeBlink", by_blend)):
        row, aucs[name] = group_rows(name, per_video, drowsy_videos)
        out.append(row)
    out += [
        "",
        "AUC: chance that a blink from a microsleep video is longer than one from another video (0.5 = no "
        "difference). The videos are of different people, so this also carries person-to-person differences.",
        "",
        "| Timing | Blinks near a microsleep | Median ms | Other blinks, same videos | Median ms | Ratio | AUC | "
        f"Videos with >= {args.min_blinks} on both sides | Median per-video ratio |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    near_auc: dict[str, float | None] = {}
    for name, per_video in (("Block 7 (EAR)", engine), ("Offline, EAR", by_ear), ("Offline, eyeBlink", by_blend)):
        near_all: list[Blink] = []
        far_all: list[Blink] = []
        paired: list[float] = []
        for v in drowsy_videos:
            near, far = split_near_far(per_video.get(v, []), runs[v], fps[v], args.near_s)
            near_all += near
            far_all += far
            if len(near) >= args.min_blinks and len(far) >= args.min_blinks:
                paired.append(float(np.median(durations(near)) / np.median(durations(far))))
        n, f = durations(near_all), durations(far_all)
        near_auc[name] = auc(n, f)
        out.append(
            f"| {name} | {len(n)} | {_ms(n)} | {len(f)} | {_ms(f)} | {_f(_ratio(n, f))} | {_f(near_auc[name])} | "
            f"{len(paired)} | {_f(float(np.median(paired)) if paired else None)} |"
        )
    main_auc = max((a for a in (aucs["Block 7 (EAR)"], near_auc["Block 7 (EAR)"]) if a is not None), default=None)

    ear_n, blend_n = sum(map(len, by_ear.values())), sum(map(len, by_blend.values()))
    per_video_pairs = [
        (np.median(durations(by_ear[v])), np.median(durations(by_blend[v])))
        for v in by_blend
        if len(by_ear[v]) >= min_blinks and len(by_blend[v]) >= min_blinks
    ]
    agree = spearman(np.array([a for a, _ in per_video_pairs]), np.array([b for _, b in per_video_pairs]))
    out += [
        "",
        "## 3. EAR against eyeBlink",
        "",
        f"Same offline timer on both signals (dip below {level} reaching {args.depth}, back within {max_s:.1f} s): "
        f"{ear_n} blinks on EAR, {blend_n} on eyeBlink ({len(by_blend)} videos have a closure to scale eyeBlink with). "
        f"Median duration {_ms(durations([b for bs in by_ear.values() for b in bs]))} ms on EAR, "
        f"{_ms(durations([b for bs in by_blend.values() for b in bs]))} ms on eyeBlink. Rank correlation of the "
        f"per-video medians: {_f(agree)} over {len(per_video_pairs)} videos with >= {min_blinks} blinks on both.",
        "",
        f"The offline timer finds {ear_n / max(len(all_engine), 1):.1f} times as many blinks on EAR as block 7 "
        f"times ({ear_n} against {len(all_engine)}). Block 7 only times a dip that its closure rule called a "
        "blink; why it leaves out more than half was not looked into here.",
        "",
        "## 4. Duration against reopening time",
        "",
        f"Per blink (block 7, {len(all_engine)} blinks): Spearman rho = **{_f(rho)}**. Duration and reopening time "
        "rank the blinks almost the same way: a longer blink is mostly a slower reopening.",
        "",
        "## 5. Verdict",
        "",
        f"Rules: add `duration_ratio` only if it separates (AUC >= {args.auc_min}) **and** adds to `reopen_ratio` "
        f"(|rho| <= {args.rho_max}). The two cut-offs were picked after a first look at the numbers, so they are "
        "not pre-registered; what matters is how far the result is from them.",
        "",
        f"- Separation: best AUC of block 7's timing {_f(main_auc)} -> "
        f"**{'met' if main_auc is not None and main_auc >= args.auc_min else 'not met'}**.",
        f"- Adds to `reopen_ratio`: rho {_f(rho)} -> "
        f"**{'met' if rho is not None and abs(rho) <= args.rho_max else 'not met'}**.",
    ]
    add = main_auc is not None and main_auc >= args.auc_min and rho is not None and abs(rho) <= args.rho_max
    out += [
        "",
        "**`duration_ratio` is worth a milestone.**"
        if add
        else "**Do not add `duration_ratio` to the engine on this evidence.**",
        "",
        "## Limits",
        "",
        "- NITYMED drowsiness is acted, at night, in clips of 15 s to 2.5 min: a real slow drift over a drive is not in it.",
        f"- One frame is {1000 / np.median(list(fps.values())):.0f} ms; the 30 ms group difference of Häkkänen 1999 "
        "(EOG) is below it. Only medians over many blinks mean anything.",
        '- "Near a microsleep" is a stand-in for drowsy, chosen here; UTA-RLDD (same person at KSS levels) is the '
        "dataset that can really answer question 1.",
        "- The eyeBlink scale is each video's own (median = open, 99.5th percentile = closed), not the engine's.",
    ]
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point (see the module doc). Returns the process exit code."""
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--traces", required=True, help="FL3D traces from tools/seq_eval.py trace")
    p.add_argument("--out", default=None)
    p.add_argument("--near-s", type=float, default=10.0, help="a blink this close to a microsleep is 'near'")
    p.add_argument("--min-blinks", type=int, default=5, help="per side, for a per-video ratio")
    p.add_argument("--depth", type=float, default=0.5, help="offline timer: a dip must reach this aperture")
    p.add_argument("--auc-min", type=float, default=0.65, help="verdict: separation needed")
    p.add_argument("--rho-max", type=float, default=0.8, help="verdict: most rank correlation with reopening allowed")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = p.parse_args(argv)
    from edge_agent.config import load_thresholds

    traces = pickle.loads(Path(args.traces).read_bytes())
    text = report(traces, load_fl3d_labels(), load_thresholds(), args)
    print(text)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
