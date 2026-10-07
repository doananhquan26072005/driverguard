"""UTA-RLDD for DriverGuard: trace every video once, then replay blocks 7-12 on the traces.

UTA-RLDD (Ghoddoosian et al., CVPRW 2019): ~10 min videos, one self-rated label per video from the
file name: 0 = alert, 5 = low vigilance, 10 = drowsy. Kaggle copy: 48 subjects, folds 1-4,
`FoldX_partY/FoldX_partY/<subject>/<label>[_part].<ext>`. The subjects sit at a laptop, they do not
drive. Tracing (97 GB, ~16 h on 4 CPUs) runs on Kaggle with notebooks/uta_rldd_kaggle.ipynb; the
traces (numbers per frame, never an image) are then kept in data/eval_traces/uta_rldd/.

Split by subject (eval/splits/uta_rldd_{dev,test}.txt): thresholds are searched on dev only, the
test subjects are scored once for a chosen configuration.

    python tools/uta_rldd.py report --split dev --out eval/results/uta_rldd_dev.md
    python tools/uta_rldd.py grid --out eval/results/uta_rldd_grid_dev.md          # dev only
    python tools/uta_rldd.py compare --split test --set risk.drowsy.l1=45          # current vs the --set values
    python tools/uta_rldd.py personal --out eval/results/personalization_uta_rldd.md

The functions that score (summarize, metrics, the reports) are pure: they take traces / rows.
"""

from __future__ import annotations

import copy
import csv
import gzip
import json
import math
import pickle
import re
import shutil
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import asdict, dataclass
from multiprocessing import get_context
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from edge_agent.config import PROJECT_ROOT  # noqa: E402

UTA_DIR = PROJECT_ROOT / "data/eval_traces/uta_rldd"
SPLIT_DIR = PROJECT_ROOT / "eval/splits"
VIDEO_EXT = {".mov", ".mp4", ".m4v", ".avi", ".mkv"}
LABELS = (0, 5, 10)
TERMS = ("perclos", "microsleep", "yawn", "nod", "slow_blink", "brow")  # RiskAssessment.drowsy_terms order
EVENTS = ("blink", "microsleep", "yawn", "nod", "bow", "perclos_high", "brow_raise")
PERCLOS_RATIOS = (0.48, 0.55, 0.65, 0.75)  # 0.48 ~ P80 with the closed EAR at 0.35 x baseline; 0.65 = current


# --------------------------------------------------------------------------- dataset index


@dataclass(frozen=True)
class Video:
    key: str  # F3_S32_10_1
    fold: int
    subject: str
    label: int  # 0 / 5 / 10
    part: int  # 0, or 1, 2 for a recording split in two files (subject 32: 10_1, 10_2)
    path: str
    size_mb: float


def parse_video(rel: str) -> tuple[int, str, int, int] | None:
    """(fold, subject, label, part) from a path below the dataset root, None when it is not a UTA video."""
    parts = Path(rel).parts
    m = re.fullmatch(r"(0|5|10)(?:[_\- ](\d+))?", Path(rel).stem.strip())
    fold = next((int(f.group(1)) for p in parts if (f := re.match(r"fold\s*(\d+)", p, re.I))), None)
    if m is None or fold is None or len(parts) < 2:
        return None
    return fold, parts[-2].strip(), int(m.group(1)), int(m.group(2) or 0)


def discover(root: str | Path) -> tuple[list[Video], list[str]]:
    """Every labelled video below root, and the video files whose name could not be read."""
    root = Path(root)
    videos, skipped = [], []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in VIDEO_EXT:
            continue
        rel = p.relative_to(root).as_posix()
        parsed = parse_video(rel)
        if parsed is None:
            skipped.append(rel)
            continue
        fold, subject, label, part = parsed
        key = f"F{fold}_S{subject}_{label}" + (f"_{part}" if part else "")
        videos.append(Video(key, fold, subject, label, part, str(p), round(p.stat().st_size / 1e6, 1)))
    return sorted(videos, key=lambda v: (v.fold, v.subject, v.label, v.part)), skipped


def probe(path: str) -> dict[str, float]:
    """Container metadata of one video (no frame is decoded)."""
    import cv2

    cap = cv2.VideoCapture(path)
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        n = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        return {
            "fps": round(fps, 3),
            "frames": int(n),
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "minutes": round(n / fps / 60, 2) if fps > 0 else float("nan"),
        }
    finally:
        cap.release()


def write_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


# --------------------------------------------------------------------------- tracing (models, spawn workers)


def trace_file(out_dir: str | Path, key: str) -> Path:
    return Path(out_dir) / f"{key}.pkl.gz"


def save_trace(path: Path, tr: dict) -> None:
    tmp = path.with_suffix(".part")
    with gzip.open(tmp, "wb", compresslevel=3) as f:
        pickle.dump(tr, f, protocol=pickle.HIGHEST_PROTOCOL)
    tmp.replace(path)  # a killed session never leaves a half-written trace


def load_trace(path: str | Path) -> dict:
    if not hasattr(np, "_core"):  # traces pickled with numpy 2 (Kaggle) read with numpy 1
        import numpy.core as core

        sys.modules.setdefault("numpy._core", core)
        for name in ("numeric", "multiarray", "_multiarray_umath"):
            sys.modules.setdefault(f"numpy._core.{name}", getattr(core, name))
    with gzip.open(path, "rb") as f:
        return pickle.load(f)


def find_traces(dirs: list[str | Path]) -> dict[str, Path]:
    """key -> trace file, searching the directories (and below them) in order; first one wins."""
    out: dict[str, Path] = {}
    for d in dirs:
        d = Path(d)
        if not d.exists():
            continue
        for p in sorted(d.rglob("*.pkl.gz")):
            out.setdefault(p.name.removesuffix(".pkl.gz"), p)
    return out


def _trace_job(args: tuple[str, str, str, dict[str, Any], float]) -> dict[str, Any]:
    key, path, out, thresholds, speed = args
    t0 = time.time()
    info: dict[str, Any] = {"key": key}
    try:
        from tools.seq_eval import trace_video

        tr = trace_video(Path(path), thresholds, speed, use_phone=False)
        if tr["n"] == 0:
            raise RuntimeError("no frame decoded")
        save_trace(Path(out), tr)
        c = tr["cols"]
        info |= {
            "frames": tr["n"],
            "fps": round(tr["fps"], 3),
            "minutes": round(tr["n"] / tr["fps"] / 60, 2),
            "face": round(float(np.mean(c["face"])), 4),
            "reliable": round(float(np.mean(c["reliable"])), 4),
            "alerts": len(tr["alerts"]),
            "error": "",
        }
    except Exception as e:  # one broken video must not stop the run
        info |= {"frames": 0, "error": f"{type(e).__name__}: {e}"}
    info["wall_s"] = round(time.time() - t0, 1)
    return info


def run_traces(
    videos: list[Video],
    out_dir: str | Path,
    thresholds: dict[str, Any],
    resume_dirs: list[str | Path] = (),
    workers: int = 4,
    deadline: float | None = None,
    speed_kmh: float = 60.0,
) -> list[dict[str, Any]]:
    """Trace the videos not traced yet (blocks 2-12, no phone model), one file per video.

    Traces found in resume_dirs (output of an earlier session) are copied, not redone. No new video
    starts after `deadline` (time.time()), so the session can still finish and keep its output.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    have = find_traces([out_dir])
    for key, p in find_traces(list(resume_dirs)).items():
        if key not in have and any(v.key == key for v in videos):
            shutil.copy(p, trace_file(out_dir, key))
            have[key] = trace_file(out_dir, key)
    todo = [v for v in videos if v.key not in have]
    print(
        f"[trace] {len(videos)} videos, {len(videos) - len(todo)} already traced, {len(todo)} to do, {workers} workers"
    )
    log: list[dict[str, Any]] = []
    if not todo:
        return log
    t0 = time.time()
    frames = 0
    queue = list(todo)
    running: dict[Any, Video] = {}
    with ProcessPoolExecutor(workers, mp_context=get_context("spawn")) as pool:
        while queue or running:
            while queue and len(running) < workers and (deadline is None or time.time() < deadline):
                v = queue.pop(0)
                job = (v.key, v.path, str(trace_file(out_dir, v.key)), thresholds, speed_kmh)
                running[pool.submit(_trace_job, job)] = v
            if not running:
                break
            done, _ = wait(list(running), return_when=FIRST_COMPLETED)
            for fut in done:
                v = running.pop(fut)
                try:
                    info = fut.result()
                except Exception as e:  # worker killed (out of memory, ...)
                    info = {"key": v.key, "frames": 0, "error": f"{type(e).__name__}: {e}", "wall_s": 0.0}
                info |= {"fold": v.fold, "subject": v.subject, "label": v.label, "size_mb": v.size_mb}
                log.append(info)
                frames += info["frames"]
                rate = frames / max(time.time() - t0, 1e-9)
                if info["error"]:
                    print(f"[trace] {len(log)}/{len(todo)} {v.key} FAILED {info['error']}", flush=True)
                else:
                    print(
                        f"[trace] {len(log)}/{len(todo)} {v.key} {info['minutes']:.1f} min {info['frames']} fr "
                        f"{info['fps']:g} fps face {info['face']:.1%} reliable {info['reliable']:.1%} "
                        f"alerts {info['alerts']} | {info['wall_s']:.0f} s | total {rate:.0f} frames/s, "
                        f"{(time.time() - t0) / 60:.0f} min elapsed",
                        flush=True,
                    )
    if queue:
        print(f"[trace] time budget reached: {len(queue)} videos left for the next session: {[v.key for v in queue]}")
    return log


# --------------------------------------------------------------------------- replay (blocks 7-12, no model)


def make_thresholds(base: dict[str, Any], sets: list[str] = ()) -> dict[str, Any]:
    """A copy of base with "a.b=value" assignments; ValueError when the result breaks a consistency rule."""
    from edge_agent.config import consistency_errors
    from tools.seq_eval import set_threshold

    th = copy.deepcopy(base)
    for a in sets:
        set_threshold(th, a)
    errors = consistency_errors(th)
    if errors:
        raise ValueError("; ".join(errors))
    return th


def replay_plus(
    tr: dict,
    thresholds: dict[str, Any],
    extras: bool = True,
    profile: dict[str, float] | None = None,
    eye: str = "trace",
) -> dict:
    """seq_eval.replay, plus per-frame columns it does not return (PERCLOS, the open-eye baseline,
    gaze_down, the drowsy_score terms) and the blinks block 7 timed (frame, duration, reopening).
    profile: a fake driver enrollment handed to blocks 7 and 8 (see seq_eval.replay).
    eye: "trace" = block 5 as it decided when the video was traced; "block5" = block 5 decided again
    with these thresholds (seq_eval.replay)."""
    from tools.seq_eval import replay

    if not extras:
        return replay(tr, thresholds, eye, profile=profile)
    n = tr["n"]
    names = ("perclos", "perclos_ready", "ear_base", "gaze_down", "off_road", *(f"term_{k}" for k in TERMS))
    ex = {k: np.full(n, np.nan) for k in names}
    blinks: list[tuple[int, float, float]] = []
    last: list[Any] = [None]

    def observe(i: int, pipeline: Any, r: Any) -> None:
        d = r.drowsiness
        ex["perclos"][i] = d.perclos_60s
        ex["perclos_ready"][i] = d.perclos_ready
        ex["ear_base"][i] = d.ear_open_baseline
        ex["gaze_down"][i] = d.gaze_down
        ex["off_road"][i] = r.distraction.off_road
        for k, v in zip(TERMS, r.risk.drowsy_terms):
            ex[f"term_{k}"][i] = v
        log = getattr(getattr(pipeline.drowsiness, "_slow", None), "_log", None)  # as tools/blink_duration.py
        if log and log[-1] is not last[0]:
            last[0] = log[-1]
            blinks.append((i, float(log[-1][1]), float(log[-1][2])))

    out = replay(tr, thresholds, eye, observe, profile)
    out["cols"] = {**out["cols"], **ex}
    out["traced_alerts"] = len(tr["alerts"])  # what the full pipeline raised when the video was traced
    out["blinks"] = blinks
    return out


def _mean(x: np.ndarray) -> float:
    x = x[np.isfinite(x)]
    return float(np.mean(x)) if len(x) else float("nan")


def _pct(x: np.ndarray, q: float) -> float:
    x = x[np.isfinite(x)]
    return float(np.percentile(x, q)) if len(x) else float("nan")


def summarize(tr: dict, thresholds: dict[str, Any]) -> dict[str, Any]:
    """One row of numbers for one (replayed) trace. Scores, levels and windows leave out the start-up
    stretch (eval.warmup_s); alerts are counted apart for the start-up and for the rest."""
    from tools.metrics import DISTRACTION_REASONS, DROWSY_REASONS, EvalConfig, per_second_max, window_scores

    c, n, fps = tr["cols"], tr["n"], tr["fps"]
    cfg = EvalConfig.from_dict(thresholds.get("eval"))
    dur = n / fps if n else 0.0
    m = c["t"] >= cfg.warmup_s
    s: dict[str, Any] = {
        "frames": n,
        "fps": round(fps, 3),
        "dur_s": round(dur, 2),
        "warm_s": round(min(cfg.warmup_s, dur), 2),
        "score_s": round(max(0.0, dur - cfg.warmup_s), 2),
        "face": _mean(c["face"]),
        "reliable": _mean(c["reliable"]),
        "eye_known": float(np.mean(np.isfinite(c["eye_closed"]))) if n else float("nan"),
        "cnn_used": float(np.mean(np.isfinite(c["p_closed"]))) if n else float("nan"),
        "score_mean": _mean(c["drowsy_score"][m]),
        "score_p50": _pct(c["drowsy_score"][m], 50),
        "score_p90": _pct(c["drowsy_score"][m], 90),
        "score_max": _pct(c["drowsy_score"][m], 100),
        "max_closed_s": _pct(c["closed_duration"], 100),
    }
    drowsy_level = c.get("drowsy_level", c["level"])
    dis_level = c.get("distraction_level", np.zeros(n))
    for lv in (1, 2, 3):
        s[f"time_l{lv}"] = float(np.mean(drowsy_level[m] >= lv)) if m.any() else float("nan")
    s["time_dis_l2"] = float(np.mean(dis_level[m] >= 2)) if m.any() else float("nan")

    # windows: every window after the start-up, and how many of them reach each level
    for branch, col in (("drowsy", drowsy_level), ("dis", dis_level)):
        per_sec = per_second_max(c["t"], [int(v) for v in np.nan_to_num(col)], dur)
        for lv in (1, 2, 3):
            w = window_scores(
                dur, [], [(0.0, dur)], per_sec, EvalConfig(cfg.window_s, cfg.warmup_s, cfg.positive_frac, lv)
            )
            s["win"] = w.awake
            s[f"{branch}_win_l{lv}"] = w.false_alarms

    alerts = [(round(i / fps, 2), int(lv), list(rs)) for i, lv, rs in tr["alerts"]]
    count: Counter = Counter()
    first = float("nan")
    for t, lv, rs in alerts:
        drowsy = any(r in DROWSY_REASONS for r in rs)
        branch = "drowsy" if drowsy else "dis" if any(r in DISTRACTION_REASONS for r in rs) else "other"
        if t < cfg.warmup_s:
            count[f"a_{branch}_warm"] += 1
        else:
            count[f"a_{branch}"] += 1
            if drowsy:
                for k in range(2, lv + 1):
                    count[f"a_drowsy_l{k}"] += 1
        if drowsy and math.isnan(first):
            first = t
    for k in ("a_drowsy", "a_drowsy_l2", "a_drowsy_l3", "a_dis", "a_other", "a_drowsy_warm", "a_dis_warm"):
        s[k] = count[k]
    s["first_drowsy_s"] = first
    if "traced_alerts" in tr:
        s["a_all"], s["a_traced"] = len(alerts), tr["traced_alerts"]
    s["alerts"] = json.dumps(alerts)
    ev = Counter(e for i, e in tr["events"] if i / fps >= cfg.warmup_s)
    for e in EVENTS:
        s[f"ev_{e}"] = ev[e]

    if "term_perclos" in c:  # replay_plus(extras=True): signals, for the separation table
        ready = m & (c["perclos_ready"] == 1)
        s["perclos_mean"] = _mean(c["perclos"][ready])
        s["perclos_p90"] = _pct(c["perclos"][ready], 90)
        s["gaze_down"] = _mean(c["gaze_down"][m])
        s["off_road"] = _mean(c["off_road"][m])
        for k in TERMS:
            s[f"term_{k}"] = _mean(c[f"term_{k}"][m])
        ok = m & (c["reliable"] == 1) & np.isfinite(c["ear"]) & (c["ear_base"] > 0)
        ratio = c["ear"][ok] / c["ear_base"][ok]
        for r in PERCLOS_RATIOS:
            s[f"closed_r{int(r * 100)}"] = float(np.mean(ratio < r)) if len(ratio) else float("nan")
        s["ear_base"] = _mean(c["ear_base"][m])
        s["ear_ratio_mean"] = _mean(ratio)
        s["ear_ratio_p10"] = _pct(ratio, 10)
        blink = c.get("blink", np.full(n, np.nan))[m]
        s["bs_blink_mean"] = _mean(blink)
        s["bs_closed_frac"] = (
            float(np.mean(blink[np.isfinite(blink)] >= 0.5)) if np.isfinite(blink).any() else float("nan")
        )
        s["cnn_closed_frac"] = (
            float(np.mean(c["p_cnn"][m][np.isfinite(c["p_cnn"][m])] >= 0.6))
            if np.isfinite(c["p_cnn"][m]).any()
            else float("nan")
        )
        mar = c["mar"][m]
        s["mar_open_frac"] = (
            float(np.mean(mar[np.isfinite(mar)] >= float(thresholds["drowsiness"]["yawn"]["mar_open"])))
            if np.isfinite(mar).any()
            else float("nan")
        )
        s["pitch_std"] = float(np.nanstd(c["pitch"][m])) if np.isfinite(c["pitch"][m]).any() else float("nan")
        s["brow_mean"] = _mean(c.get("brow", np.full(n, np.nan))[m])
        if "perclos_p80" in c:  # traced by newer code (M40); as traced, not replayed
            s["perclos_p80_mean"] = _mean(c["perclos_p80"][m])
        if "look_down_l" in c:  # eyeLookDown blendshapes (M39)
            s["look_down_mean"] = _mean((c["look_down_l"][m] + c["look_down_r"][m]) / 2)
        minutes = s["score_s"] / 60
        for e in ("blink", "microsleep", "yawn", "nod", "brow_raise"):
            s[f"{e}_per_min"] = ev[e] / minutes if minutes > 0 else float("nan")
        b = [(d, r) for i, d, r in tr.get("blinks", []) if i / fps >= cfg.warmup_s]
        s["blink_timed"] = len(b)
        s["blink_dur_med"] = float(np.median([d for d, _ in b])) if b else float("nan")
        s["blink_reopen_med"] = float(np.median([r for _, r in b])) if b else float("nan")
    return s


_CACHE: dict[str, dict] = {}


def _replay_job(
    args: tuple[str, str, dict[str, Any], bool, dict[str, float] | None, str],
) -> tuple[str, dict[str, Any]]:
    key, path, thresholds, extras, profile, eye = args
    if key not in _CACHE:  # each worker reads a trace once and keeps it for the next configuration
        _CACHE[key] = load_trace(path)
    return key, summarize(replay_plus(_CACHE[key], thresholds, extras, profile, eye), thresholds)


def replay_rows(
    items: list[tuple[Video, Path]],
    thresholds: dict[str, Any],
    pool: Any = None,
    extras: bool = False,
    profiles: dict[str, dict[str, float]] | None = None,
    eye: str = "trace",
) -> list[dict[str, Any]]:
    """One row per video: its identity + summarize() of blocks 7-12 replayed with these thresholds.
    profiles: video key -> fake enrollment for that video (videos without one learn their baselines)."""
    meta = {v.key: v for v, _ in items}
    jobs = [(v.key, str(p), thresholds, extras, (profiles or {}).get(v.key), eye) for v, p in items]
    results = pool.map(_replay_job, jobs, chunksize=1) if pool is not None else map(_replay_job, jobs)
    rows = []
    for key, s in results:
        v = meta[key]
        rows.append({"key": key, "fold": v.fold, "subject": f"F{v.fold}_S{v.subject}", "label": v.label, **s})
    return sorted(rows, key=lambda r: r["key"])


def replay_pool(workers: int) -> Any:
    return ProcessPoolExecutor(workers, mp_context=get_context("spawn")) if workers > 1 else None


# --------------------------------------------------------------------------- aggregation (pure)

_SUM = {"frames", "dur_s", "warm_s", "score_s", "win", "blink_timed"}
_MAX = {"score_max", "max_closed_s"}


def by_subject(rows: list[dict[str, Any]], label: int) -> dict[str, dict[str, Any]]:
    """subject -> one row for this label; a recording in two files (10_1, 10_2) is merged: counts
    added, the other numbers averaged with the scored seconds as weights."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        if r["label"] == label:
            groups[r["subject"]].append(r)
    out = {}
    for subject, parts in groups.items():
        if len(parts) == 1:
            out[subject] = parts[0]
            continue
        merged: dict[str, Any] = {}
        w = np.array([max(p["score_s"], 1e-9) for p in parts])
        for k, v in parts[0].items():
            vals = [p[k] for p in parts]
            if k == "alerts":
                merged[k] = json.dumps([a for p in parts for a in json.loads(p[k])])
            elif not isinstance(v, (int, float)) or k in ("fold", "label"):
                merged[k] = v
            elif k in _SUM or k.startswith(("a_", "ev_")) or "_win_" in k:
                merged[k] = sum(vals)
            elif k in _MAX:
                merged[k] = float(np.nanmax(vals)) if np.isfinite(vals).any() else float("nan")
            elif k == "first_drowsy_s":
                merged[k] = float(np.nanmin(vals)) if np.isfinite(vals).any() else float("nan")
            else:
                x = np.array(vals, dtype=float)
                ok = np.isfinite(x)
                merged[k] = float(np.sum(x[ok] * w[ok]) / np.sum(w[ok])) if ok.any() else float("nan")
        merged["key"] = "+".join(p["key"] for p in parts)
        out[subject] = merged
    return out


def sign_test(wins: int, losses: int) -> float | None:
    """Two-sided exact sign test (ties dropped): p-value of this many wins out of wins + losses."""
    n = wins + losses
    if n == 0:
        return None
    k = max(wins, losses)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k, n + 1)) / 2**n)


def paired(s0: dict[str, dict], s1: dict[str, dict], key: str) -> dict[str, Any]:
    """Same subject, two levels: how often the number is higher at the drowsier level."""
    d = [s1[k][key] - s0[k][key] for k in s0 if k in s1 and np.isfinite(s0[k][key]) and np.isfinite(s1[k][key])]
    up, down = sum(x > 0 for x in d), sum(x < 0 for x in d)
    return {
        "pairs": len(d),
        "higher": up,
        "lower": down,
        "median_diff": float(np.median(d)) if d else float("nan"),
        "p": sign_test(up, down),
    }


def _auc(a: dict[str, dict], b: dict[str, dict], key: str) -> float | None:
    from tools.seq_eval import auc

    return auc(np.array([r[key] for r in a.values()], dtype=float), np.array([r[key] for r in b.values()], dtype=float))


def metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """The numbers one configuration is judged on (docs/improvements.md task 5, "what is optimal")."""
    from tools.metrics import rate_ci, wilson_ci

    s0, s5, s10 = (by_subject(rows, lb) for lb in LABELS)
    hours = sum(r["score_s"] for r in s0.values()) / 3600
    fa = sum(r["a_drowsy"] for r in s0.values())
    fa_l2 = sum(r["a_drowsy_l2"] for r in s0.values())
    rate = rate_ci(fa, hours)
    win0 = sum(r["win"] for r in s0.values())
    win10 = sum(r["win"] for r in s10.values())
    win5 = sum(r["win"] for r in s5.values())
    far_subject = [r["drowsy_win_l1"] / r["win"] for r in s0.values() if r["win"]]
    pm = paired(s0, s10, "score_mean")
    alerted10 = sum((r["a_drowsy"] + r["a_drowsy_warm"]) > 0 for r in s10.values())
    out = {
        "subjects": len({r["subject"] for r in rows}),
        "awake_h": hours,
        "fa": fa,
        "fa_per_h": rate[0],
        "fa_per_h_lo": rate[1],
        "fa_per_h_hi": rate[2],
        "fa_l2plus": fa_l2,
        "fa_l3": sum(r["a_drowsy_l3"] for r in s0.values()),
        "fa_warmup": sum(r["a_drowsy_warm"] for r in s0.values()),
        "win0": win0,
        "far_l1": wilson_ci(sum(r["drowsy_win_l1"] for r in s0.values()), win0)[0],
        "far_l2": wilson_ci(sum(r["drowsy_win_l2"] for r in s0.values()), win0)[0],
        "far_l1_worst_subject": max(far_subject, default=None),
        "subjects_far_gt0": sum(f > 0 for f in far_subject),
        "win10": win10,
        "hit10_l1": wilson_ci(sum(r["drowsy_win_l1"] for r in s10.values()), win10)[0],
        "hit10_l2": wilson_ci(sum(r["drowsy_win_l2"] for r in s10.values()), win10)[0],
        "hit5_l1": wilson_ci(sum(r["drowsy_win_l1"] for r in s5.values()), win5)[0],
        "auc_mean": _auc(s10, s0, "score_mean"),
        "auc_p90": _auc(s10, s0, "score_p90"),
        "auc5_mean": _auc(s5, s0, "score_mean"),
        "pairs": pm["pairs"],
        "pairs_higher": pm["higher"],
        "pairs_lower": pm["lower"],
        "pairs_p": pm["p"],
        "v10": len(s10),
        "v10_alerted": alerted10,
        "v10_l2plus": sum(r["a_drowsy_l2"] > 0 for r in s10.values()),
        "v10_l3": sum(r["a_drowsy_l3"] > 0 for r in s10.values()),
        "v5": len(s5),
        "v5_alerted": sum((r["a_drowsy"] + r["a_drowsy_warm"]) > 0 for r in s5.values()),
        "v5_l3": sum(r["a_drowsy_l3"] > 0 for r in s5.values()),
        "v0": len(s0),
        "v0_alerted": sum((r["a_drowsy"] + r["a_drowsy_warm"]) > 0 for r in s0.values()),
        "dis_alerts_0": sum(r["a_dis"] for r in s0.values()),
    }
    return out


# --------------------------------------------------------------------------- reports (pure)


def _f(v: Any, d: int = 2) -> str:
    return "–" if v is None or (isinstance(v, float) and not math.isfinite(v)) else f"{v:.{d}f}"


def _p(v: Any, d: int = 1) -> str:
    return "–" if v is None or (isinstance(v, float) and not math.isfinite(v)) else f"{v * 100:.{d}f}%"


def _med(values: list[float]) -> str:
    x = np.array([v for v in values if v is not None and np.isfinite(v)], dtype=float)
    if not len(x):
        return "–"
    return f"{np.median(x):.2f} ({np.percentile(x, 25):.2f}–{np.percentile(x, 75):.2f})"


def baseline_report(rows: list[dict[str, Any]], thresholds: dict[str, Any], title: str, note: str = "") -> str:
    """Markdown report of one configuration on one split (numbers only)."""
    from tools.metrics import EvalConfig, ci_text, rate_ci, wilson_ci

    cfg = EvalConfig.from_dict(thresholds.get("eval"))
    subj = {lb: by_subject(rows, lb) for lb in LABELS}
    m = metrics(rows)
    lines = [f"# {title}", ""]
    if note:
        lines += [note, ""]
    lines += [
        f"{m['subjects']} subjects, {len(rows)} videos. Blocks 7-12 replayed from per-frame traces (blocks 2-6 run "
        "once, phone model off, simulated 60 km/h, fresh state per video). Labels are per video and self-rated: "
        "0 = alert, 5 = low vigilance, 10 = drowsy. A `10` video is not drowsy on every second, a `0` video is "
        f"assumed awake throughout. Scores, levels and windows leave out the first {cfg.warmup_s:g} s of each video.",
        "",
        "## 1. Measurability",
        "",
        "| Label | Subjects | Videos | Hours | Hours scored | Face found | Face reliable | Eye state judged | CNN used | FPS median (min–max) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for lb in LABELS:
        rs = [r for r in rows if r["label"] == lb]
        if not rs:
            continue
        w = np.array([r["frames"] for r in rs], dtype=float)
        avg = lambda k: float(np.sum(np.array([r[k] for r in rs]) * w) / w.sum())  # noqa: E731
        fps = [r["fps"] for r in rs]
        lines.append(
            f"| {lb} | {len(subj[lb])} | {len(rs)} | {sum(r['dur_s'] for r in rs) / 3600:.2f} | "
            f"{sum(r['score_s'] for r in rs) / 3600:.2f} | {_p(avg('face'))} | {_p(avg('reliable'))} | "
            f"{_p(avg('eye_known'))} | {_p(avg('cnn_used'))} | {np.median(fps):g} ({min(fps):g}–{max(fps):g}) |"
        )
    low = sorted((r["reliable"], r["key"]) for r in rows if r["reliable"] < 0.8)
    if low:
        lines += [
            "",
            "Videos with a reliable face on < 80 % of frames: " + ", ".join(f"{k} {_p(v)}" for v, k in low) + ".",
        ]

    # ---- alerts on awake videos
    hours = m["awake_h"]
    warm_h = sum(r["warm_s"] for r in subj[0].values()) / 3600
    by_reason: Counter = Counter()
    warm_reason: Counter = Counter()
    listed = []
    for r in subj[0].values():
        for t, lv, rs in json.loads(r["alerts"]):
            for reason in rs:
                (warm_reason if t < cfg.warmup_s else by_reason)[(reason, lv)] += 1
            listed.append((r["subject"], t, lv, ",".join(rs)))
    lines += [
        "",
        "## 2. Alerts on awake videos (`0`): false alarms",
        "",
        f"{hours:.2f} h of awake video after the start-up stretch, {len(subj[0])} subjects. Exact Poisson 95 % CI. "
        "The subjects read / watch a laptop and do not drive: distraction alerts (off_road) are listed apart and "
        "are not drowsiness false alarms.",
        "",
        "| Alerts | Count | Per hour (95% CI) |",
        "|---|---:|---:|",
        f"| Drowsiness branch, any level | {m['fa']} | {ci_text(rate_ci(m['fa'], hours))} |",
        f"| Drowsiness branch, L2 or L3 | {m['fa_l2plus']} | {ci_text(rate_ci(m['fa_l2plus'], hours))} |",
        f"| Drowsiness branch, L3 | {m['fa_l3']} | {ci_text(rate_ci(m['fa_l3'], hours))} |",
        f"| Distraction branch | {m['dis_alerts_0']} | {ci_text(rate_ci(m['dis_alerts_0'], hours))} |",
        "",
        "By reason and level (an alert with two reasons counts under both):",
        "",
        "| Reason | Level | Count | Per hour (95% CI) |",
        "|---|---:|---:|---:|",
    ]
    for (reason, lv), k in sorted(by_reason.items()):
        lines.append(f"| {reason} | L{lv} | {k} | {ci_text(rate_ci(k, hours))} |")
    hi = m["fa_per_h_hi"]
    verdict = (
        "no exposure"
        if hi is None
        else f"upper bound {hi:.2f} / h ≤ 1.0: the PRD target holds on this split"
        if hi <= 1.0
        else f"upper bound {hi:.2f} / h > 1.0: the PRD target (≤ 1.0 / h, CI included) is not shown on this split"
    )
    lines += [
        "",
        f"Drowsiness false alarms per hour: {ci_text(rate_ci(m['fa'], hours))}; {verdict}. Not driving data: this "
        "is a check before real drives, not the PRD verdict.",
        "",
        f"Start-up stretch (first {cfg.warmup_s:g} s of each video, {warm_h * 60:.1f} min in all), reported apart: "
        + (", ".join(f"{r} L{lv} {k}" for (r, lv), k in sorted(warm_reason.items())) or "no alert")
        + ".",
    ]
    if listed:
        shown = sorted(listed)[:80]
        lines += [
            "",
            f"Alerts on `0` videos (subject, time, level, reasons){' (first 80)' if len(listed) > 80 else ''}: "
            + "; ".join(f"{s} {t:.0f}s L{lv} {rs}" for s, t, lv, rs in shown)
            + ".",
        ]

    # ---- windows
    lines += [
        "",
        "## 3. Windows",
        "",
        f"Windows of {cfg.window_s:g} s, not overlapping, after the start-up stretch; a window counts when the "
        "drowsiness branch reaches the level in it. On `0` the share is the FAR. On `10` (and `5`) it is the "
        "share of windows with a drowsiness level: 1 minus it is an upper bound of the MAR, since the label "
        "covers the whole video, not each window. Wilson 95 % CI (windows of one video are correlated).",
        "",
        "| Label | Windows | ≥ L1 | ≥ L2 | L3 | Distraction ≥ L2 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for lb in LABELS:
        rs = list(subj[lb].values())
        n = sum(r["win"] for r in rs)
        cells = [ci_text(wilson_ci(sum(r[f"drowsy_win_l{lv}"] for r in rs), n), True) for lv in (1, 2, 3)]
        dis = ci_text(wilson_ci(sum(r["dis_win_l2"] for r in rs), n), True)
        lines.append(f"| {lb} | {n} | {cells[0]} | {cells[1]} | {cells[2]} | {dis} |")

    # ---- separation
    lines += [
        "",
        "## 4. Does the system respond to the drowsiness level?",
        "",
        "Per subject and level; median (p25–p75) across subjects.",
        "",
        "| Label | Subjects | drowsy_score mean | drowsy_score p90 | PERCLOS mean | Time at ≥ L1 | ≥ 1 drowsiness alert | ≥ 1 at L2+ | ≥ 1 at L3 | First alert, median s |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for lb in LABELS:
        rs = list(subj[lb].values())
        if not rs:
            continue
        n = len(rs)
        any_alert = sum((r["a_drowsy"] + r["a_drowsy_warm"]) > 0 for r in rs)
        first = [r["first_drowsy_s"] for r in rs if np.isfinite(r["first_drowsy_s"])]
        lines.append(
            f"| {lb} | {n} | {_med([r['score_mean'] for r in rs])} | {_med([r['score_p90'] for r in rs])} | "
            f"{_med([r.get('perclos_mean', float('nan')) for r in rs])} | {_med([r['time_l1'] for r in rs])} | "
            f"{any_alert}/{n} | {sum(r['a_drowsy_l2'] > 0 for r in rs)}/{n} | {sum(r['a_drowsy_l3'] > 0 for r in rs)}/{n} | "
            f"{_f(float(np.median(first)) if first else None, 0)} |"
        )
    lines += [
        "",
        "AUC = chance that a subject's drowsier video scores higher than another subject's `0` video (0.5 = no "
        "signal). Paired = the same subject's two videos (sign test, ties dropped).",
        "",
        "| Number | AUC 10 vs 0 | AUC 5 vs 0 | Paired 10 vs 0: higher / lower (p) | Median difference 10 − 0 |",
        "|---|---:|---:|---:|---:|",
    ]
    for key in ("score_mean", "score_p90", "perclos_mean", "time_l1"):
        if not all(key in r for r in rows):
            continue
        pr = paired(subj[0], subj[10], key)
        lines.append(
            f"| {key} | {_f(_auc(subj[10], subj[0], key), 3)} | {_f(_auc(subj[5], subj[0], key), 3)} | "
            f"{pr['higher']} / {pr['lower']} of {pr['pairs']} (p = {_f(pr['p'], 3)}) | {_f(pr['median_diff'], 3)} |"
        )

    # ---- DDAW
    sens = wilson_ci(m["v10_alerted"], m["v10"], z=1.644854)
    lines += [
        "",
        "## 5. EU DDAW frame (approximation, not used to choose thresholds)",
        "",
        "`10` ≈ KSS ≥ 8. One label per video, so one event per subject: a subject counts as detected when the "
        "`10` video gets at least one drowsiness alert (any level).",
        "",
        f"- Sensitivity: {m['v10_alerted']}/{m['v10']} subjects = {ci_text(sens, True)} (Wilson 90 % CI). "
        "DDAW asks for a mean > 40 % and a 90 % lower bound > 20 %, on ≥ 10 subjects and ≥ 10 events.",
        f"- Never alone: drowsiness false alarms on `0` are {ci_text(rate_ci(m['fa'], hours))} / h over {hours:.2f} h, "
        f"and {m['v0_alerted']}/{m['v0']} awake videos get a drowsiness alert.",
        f"- `5` videos (KSS 6–7, reported apart): {m['v5_alerted']}/{m['v5']} get a drowsiness alert, "
        f"{m['v5_l3']}/{m['v5']} an L3.",
    ]

    # ---- per subject
    far = {s: (r["drowsy_win_l1"] / r["win"] if r["win"] else float("nan")) for s, r in subj[0].items()}
    x = np.array([v for v in far.values() if np.isfinite(v)])
    lines += [
        "",
        "## 6. Per subject",
        "",
        "One subject has ~10 min of awake video: 0 false alarms still has a 95 % upper bound of ~22 / h. Compare "
        "subjects on the window FAR and on the score, not on alerts per hour.",
        "",
    ]
    if len(x):
        lines += [
            f"Window FAR (L1) on `0` across subjects: median {_p(float(np.median(x)))}, p90 "
            f"{_p(float(np.percentile(x, 90)))}, max {_p(float(x.max()))}; {int(np.sum(x > 0))}/{len(x)} subjects above 0.",
            "",
        ]
    lines += [
        "| Subject | Reliable face (min) | FAR L1 on `0` | Drowsiness alerts 0 / 5 / 10 | Distraction alerts 0 / 5 / 10 | Score mean 0 / 5 / 10 | Reasons on `0` |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for s in sorted({r["subject"] for r in rows}):
        got = [subj[lb].get(s) for lb in LABELS]
        cell = lambda k, d=0: " / ".join("–" if r is None else _f(float(r[k]), d) for r in got)  # noqa: E731
        reasons = Counter()
        if got[0] is not None:
            for t, lv, rs in json.loads(got[0]["alerts"]):
                if t >= cfg.warmup_s:
                    reasons[f"L{lv} {'+'.join(rs)}"] += 1
        far0 = "–" if got[0] is None else f"{got[0]['drowsy_win_l1']}/{got[0]['win']}"
        lines.append(
            f"| {s} | {_p(min(r['reliable'] for r in got if r is not None))} | "
            f"{far0} | {cell('a_drowsy')} | {cell('a_dis')} | "
            f"{cell('score_mean', 1)} | {', '.join(f'{k} {n}' for k, n in sorted(reasons.items()))} |"
        )
    worst = sorted(((v, s) for s, v in far.items() if np.isfinite(v) and v > 0), reverse=True)[:5]
    if worst:
        lines += ["", "Highest window FAR: " + ", ".join(f"{s} {_p(v)}" for v, s in worst) + "."]

    # ---- score terms
    if all("term_perclos" in r for r in rows):
        lines += [
            "",
            "## 7. What drives drowsy_score",
            "",
            "Mean of each term (0..1, before its weight) per video; median across subjects. AUC as in section 4.",
            "",
            "| Term | Weight | `0` | `5` | `10` | AUC 10 vs 0 | Paired 10 vs 0: higher / lower (p) |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
        weights = thresholds["risk"]["drowsy"]
        for k in TERMS:
            key = f"term_{k}"
            pr = paired(subj[0], subj[10], key)
            med = [_f(_pct(np.array([r[key] for r in subj[lb].values()], dtype=float), 50), 3) for lb in LABELS]
            lines.append(
                f"| {k} | {weights.get(f'weight_{k}', '–')} | {med[0]} | {med[1]} | {med[2]} | "
                f"{_f(_auc(subj[10], subj[0], key), 3)} | {pr['higher']} / {pr['lower']} of {pr['pairs']} (p = {_f(pr['p'], 3)}) |"
            )
        lines += [
            "",
            "## 8. Looking down (gaze_down, block 7) and off road (block 8)",
            "",
            "Subjects look at a laptop, slightly bowed. A drowsy subject with drooping lids and a bowed head can be "
            "read as looking down (L2 off_road) instead of drowsy.",
            "",
            "| Label | gaze_down, share of time | off_road, share of time | Distraction alerts | Drowsiness alerts |",
            "|---|---:|---:|---:|---:|",
        ]
        for lb in LABELS:
            rs = list(subj[lb].values())
            lines.append(
                f"| {lb} | {_med([r['gaze_down'] for r in rs])} | {_med([r['off_road'] for r in rs])} | "
                f"{sum(r['a_dis'] for r in rs)} | {sum(r['a_drowsy'] for r in rs)} |"
            )
    return "\n".join(lines) + "\n"


SIGNALS = {
    "score_mean": "block 9 drowsy_score, mean",
    "score_p90": "block 9 drowsy_score, p90",
    "time_l1": "share of time the drowsiness branch is at ≥ L1",
    "perclos_mean": "block 7 perclos_60s (current rule), mean",
    "perclos_p90": "block 7 perclos_60s, p90",
    "perclos_p80_mean": "block 7 perclos_p80_60s as traced (P80 definition), mean",
    "look_down_mean": "MediaPipe eyeLookDown, mean of both eyes",
    "closed_r48": "frames with EAR < 0.48 x baseline (~ P80: eye ≥ 80 % closed)",
    "closed_r55": "frames with EAR < 0.55 x baseline",
    "closed_r65": "frames with EAR < 0.65 x baseline (current perclos_close_ratio)",
    "closed_r75": "frames with EAR < 0.75 x baseline",
    "bs_closed_frac": "frames with MediaPipe eyeBlink ≥ 0.5 (no baseline needed)",
    "bs_blink_mean": "MediaPipe eyeBlink, mean",
    "cnn_closed_frac": "frames with eye CNN p_closed ≥ 0.6",
    "ear_ratio_mean": "EAR / baseline, mean (lower = more closed)",
    "ear_ratio_p10": "EAR / baseline, p10 (lower = more closed)",
    "ear_base": "open-eye EAR baseline learnt by block 7",
    "blink_per_min": "block 7 blink events / min",
    "blink_dur_med": "block 7 blink duration, median s",
    "blink_reopen_med": "block 7 eyelid reopening time, median s",
    "microsleep_per_min": "block 7 microsleep events / min",
    "max_closed_s": "longest closed_duration, s",
    "yawn_per_min": "block 7 yawn events / min",
    "mar_open_frac": "frames with MAR ≥ yawn.mar_open",
    "nod_per_min": "block 7 nod events / min",
    "pitch_std": "head pitch, standard deviation",
    "brow_raise_per_min": "block 7 brow_raise events / min",
    "brow_mean": "MediaPipe browOuterUp, mean",
    "term_slow_blink": "slow_blink_score term, mean",
    "gaze_down": "share of time read as looking down",
    "face": "face found (measurability, not a drowsiness signal)",
}
LOWER_IS_DROWSY = {"ear_ratio_mean", "ear_ratio_p10", "ear_base", "face"}


def signals_report(rows: list[dict[str, Any]], title: str) -> str:
    """Which per-video numbers separate `10` from `0`, pooled and within the same subject."""
    subj = {lb: by_subject(rows, lb) for lb in LABELS}
    lines = [
        f"# {title}",
        "",
        "One number per video (after the start-up stretch), per subject. AUC oriented so that higher = drowsier "
        "(marked ↓ when the raw number falls with drowsiness). Paired = the same subject's `10` against their "
        "`0`: how many subjects move in the drowsy direction, exact sign test. A signal earns a weight when it "
        "separates within subjects, not only across them.",
        "",
        "| Signal | AUC 10 vs 0 | AUC 5 vs 0 | Paired: drowsier / not, of pairs (p) | Median `0` | Median `5` | Median `10` | Meaning |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    table = []
    for key, meaning in SIGNALS.items():
        if not any(key in r for r in rows):
            continue
        sign = -1.0 if key in LOWER_IS_DROWSY else 1.0
        flip = {lb: {s: {key: sign * r[key]} for s, r in subj[lb].items()} for lb in LABELS}
        pr = paired(flip[0], flip[10], key)
        med = [_f(_pct(np.array([r[key] for r in subj[lb].values()], dtype=float), 50), 3) for lb in LABELS]
        a10 = _auc(flip[10], flip[0], key)
        table.append(
            (
                -(a10 or 0),
                f"| {key}{' ↓' if sign < 0 else ''} | {_f(a10, 3)} | {_f(_auc(flip[5], flip[0], key), 3)} | "
                f"{pr['higher']} / {pr['lower']} of {pr['pairs']} (p = {_f(pr['p'], 3)}) | {med[0]} | {med[1]} | {med[2]} | {meaning} |",
            )
        )
    lines += [row for _, row in sorted(table)]
    return "\n".join(lines) + "\n"


GRID_COLUMNS = (
    ("far_l1", "FAR L1 on 0", _p),
    ("far_l2", "FAR L2 on 0", _p),
    ("fa", "False alarms", str),
    ("fa_per_h", "/ h", _f),
    ("fa_per_h_hi", "95% upper", _f),
    ("far_l1_worst_subject", "Worst subject FAR", _p),
    ("auc_mean", "AUC mean", lambda v: _f(v, 3)),
    ("auc_p90", "AUC p90", lambda v: _f(v, 3)),
    ("pairs_higher", "Pairs 10 > 0", str),
    ("v10_alerted", "10 alerted", str),
    ("v5_alerted", "5 alerted", str),
    ("hit10_l1", "Windows ≥ L1 on 10", _p),
)


def grid_report(results: list[dict[str, Any]], title: str, note: str = "") -> str:
    """One row per configuration; the first row is the reference."""
    lines = [f"# {title}", ""]
    if note:
        lines += [note, ""]
    ref = results[0] if results else {}
    lines += [
        f"{ref.get('subjects', 0)} subjects, {_f(ref.get('awake_h'))} h of awake video scored, {ref.get('pairs', 0)} "
        f"subjects with both `0` and `10`, {ref.get('v10', 0)} `10` and {ref.get('v5', 0)} `5` subjects. "
        "False alarms = drowsiness-branch alerts on `0` after the start-up stretch, exact Poisson upper bound. "
        "Blocking condition of task 5: upper bound ≤ 1.0 / h. Among those, the best separation of `10` from `0`.",
        "",
        "| Group | Configuration | " + " | ".join(h for _, h, _ in GRID_COLUMNS) + " |",
        "|---|---|" + "---:|" * len(GRID_COLUMNS),
    ]
    for r in results:
        if r.get("error"):
            lines.append(f"| {r['group']} | {r['config']} | not run: {r['error']} |" + " |" * (len(GRID_COLUMNS) - 1))
            continue
        lines.append(
            f"| {r['group']} | {r['config']} | " + " | ".join(fmt(r.get(k)) for k, _, fmt in GRID_COLUMNS) + " |"
        )
    return "\n".join(lines) + "\n"


def run_configs(
    configs: list[tuple[str, list[str]]],
    items: list[tuple[Video, Path]],
    base: dict[str, Any],
    pool: Any = None,
    csv_path: str | Path | None = None,
    deadline: float | None = None,
    eye: str = "trace",
) -> list[dict[str, Any]]:
    """metrics() of every (group, [assignments]) configuration; written to csv_path as it goes."""
    results: list[dict[str, Any]] = []
    for n, (group, sets) in enumerate(configs, 1):
        name = "; ".join(sets) or "baseline"
        if deadline is not None and time.time() > deadline:
            print(f"[grid] time budget reached, {len(configs) - n + 1} configurations not run")
            break
        t0 = time.time()
        try:
            th = make_thresholds(base, sets)
        except (ValueError, KeyError) as e:  # unknown key, or a broken consistency rule
            row = {"group": group, "config": name, "error": str(e)}
        else:
            row = {"group": group, "config": name, **metrics(replay_rows(items, th, pool, eye=eye)), "error": ""}
        results.append(row)
        if csv_path:
            write_csv(csv_path, results)
        print(
            f"[grid] {n}/{len(configs)} {group}: {name} | "
            + (
                row["error"]
                or f"FAR L1 {_p(row['far_l1'])} fa {row['fa']} ({_f(row['fa_per_h'])}/h, upper {_f(row['fa_per_h_hi'])}) "
                f"AUC {_f(row['auc_mean'], 3)} pairs {row['pairs_higher']}/{row['pairs']} 10 alerted {row['v10_alerted']}/{row['v10']}"
            )
            + f" | {time.time() - t0:.0f} s",
            flush=True,
        )
    return results


def default_grid() -> list[tuple[str, list[str]]]:
    """Small grids, one or two keys at a time (task 5), then one drowsy_score term off at a time (task 6).
    Microsleep / L3 thresholds are not searched: UTA-RLDD does not say where the microsleeps are."""
    d, r = "drowsiness", "risk.drowsy"
    g: list[tuple[str, list[str]]] = [("baseline", [])]
    g += [("perclos closure", [f"{d}.perclos_close_ratio={v}"]) for v in (0.48, 0.55, 0.60)]
    g += [
        ("perclos event", [f"{d}.perclos_drowsy={a}", f"{d}.perclos_rearm={b}"])
        for a, b in ((0.10, 0.08), (0.25, 0.20))
    ]
    g += [
        ("perclos ramp", [f"{r}.perclos_low={a}", f"{r}.perclos_high={b}"])
        for a, b in ((0.03, 0.15), (0.08, 0.25), (0.10, 0.30), (0.15, 0.40), (0.20, 0.50))
    ]
    g += [("score l1", [f"{r}.l1={v}"]) for v in (30, 35, 45, 50, 60)]
    g += [("score l2", [f"{r}.l2={v}"]) for v in (60, 80, 90)]
    g += [
        ("eye close / open", [f"{d}.eye.close_ratio={a}", f"{d}.eye.open_ratio={b}", f"{d}.perclos_close_ratio={c}"])
        for a, b, c in ((0.60, 0.70, 0.60), (0.70, 0.80, 0.65), (0.70, 0.80, 0.70))
    ]
    g += [("eye baseline", [f"{d}.eye.baseline_percentile={v}"]) for v in (80, 95)]
    g += [("eye baseline", [f"{d}.eye.baseline_window_s={v}"]) for v in (60, 300)]
    g += [
        ("yawn", [f"{d}.yawn.mar_open={a}", f"{d}.yawn.mar_close={b}"])
        for a, b in ((0.40, 0.30), (0.50, 0.38), (0.55, 0.42))
    ]
    g += [("yawn", [f"{d}.yawn.min_s={v}"]) for v in (1.0, 2.0)]
    g += [("yawn", [f"{r}.yawn_full={v}"]) for v in (2, 4)]
    g += [("nod", [f"{d}.nod.pitch_down_deg={v}"]) for v in (12, 20)]
    g += [("nod", [f"{r}.nod_full={v}"]) for v in (1, 3)]
    g += [("looking down", [f"{d}.microsleep_deep.bowed_pitch_deg=0"])]
    g += [("repeated L1", ["alert.l1_repeat_count=0"])]
    g += [("trend", ["risk.trend.level=0"])]
    # task 6: ablation, one term off at a time, then the two provisional terms together
    g += [("ablation", [f"{r}.weight_{k}=0"]) for k in TERMS]
    g += [("ablation", [f"{r}.weight_slow_blink=0", f"{r}.weight_brow=0"])]
    g += [("ablation", [f"{r}.weight_slow_blink=0", f"{r}.weight_brow=0", f"{r}.weight_perclos={v}"]) for v in (50, 60)]
    return g


def video_rows(videos: list[Video]) -> list[dict[str, Any]]:
    return [asdict(v) for v in videos]


# --------------------------------------------------------------------------- stored traces, splits


def split_subjects(split: str, split_dir: Path = SPLIT_DIR) -> set[str] | None:
    """Subjects (F1_S01, ...) of "dev" / "test"; None for "all"."""
    if split == "all":
        return None
    return set((split_dir / f"uta_rldd_{split}.txt").read_text(encoding="utf-8").split())


def load_items(split: str = "dev", root: Path = UTA_DIR, split_dir: Path = SPLIT_DIR) -> list[tuple[Video, Path]]:
    """(video, trace file) of every traced video of the split, from the index written when tracing."""
    wanted = split_subjects(split, split_dir)
    found = find_traces([root / "traces"])
    items = []
    with open(root / "index.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            v = Video(
                r["key"], int(r["fold"]), r["subject"], int(r["label"]), int(r["part"]), r["path"], float(r["size_mb"])
            )
            if v.key in found and (wanted is None or f"F{v.fold}_S{v.subject}" in wanted):
                items.append((v, found[v.key]))
    return items


# --------------------------------------------------------------------------- per-driver baseline (fake enrollment)

PERSONAL_SETTINGS = (
    ("fixed", "fixed common eye baseline (never learnt)"),
    ("learnt", "self-learnt during the video (as evaluated)"),
    ("own", "fake-enrolled from the start of the same video"),
    ("awake", "fake-enrolled from the start of the subject's `0` video"),
)


def _profile_job(args: tuple[str, str, dict[str, Any]]) -> tuple[str, dict[str, float] | None]:
    from tools.trace_studies import fake_profile

    key, path, thresholds = args
    return key, fake_profile(load_trace(path), thresholds)


def fake_profiles(
    items: list[tuple[Video, Path]], thresholds: dict[str, Any], pool: Any = None
) -> dict[str, dict[str, float] | None]:
    """Video key -> what driver enrollment would have measured on the first eval.fake_enroll_s of it."""
    jobs = [(v.key, str(p), thresholds) for v, p in items]
    return dict(pool.map(_profile_job, jobs, chunksize=4) if pool is not None else map(_profile_job, jobs))


def awake_profiles(
    items: list[tuple[Video, Path]], own: dict[str, dict[str, float] | None]
) -> dict[str, dict[str, float]]:
    """Every video of a subject gets the profile of that subject's `0` video (none: left to learn)."""
    source = {(v.fold, v.subject): own.get(v.key) for v, _ in items if v.label == 0}
    return {v.key: p for v, _ in items if (p := source.get((v.fold, v.subject))) is not None}


def personal_study(
    items: list[tuple[Video, Path]], thresholds: dict[str, Any], pool: Any = None, eye: str = "trace"
) -> dict[str, list[dict[str, Any]]]:
    """Rows per setting of PERSONAL_SETTINGS: the same videos replayed with each eye / pose baseline."""
    own = fake_profiles(items, thresholds, pool)
    fixed = make_thresholds(thresholds, ["drowsiness.eye.baseline_min_data_s=1000000"])
    return {
        "fixed": replay_rows(items, fixed, pool, eye=eye),
        "learnt": replay_rows(items, thresholds, pool, eye=eye),
        "own": replay_rows(items, thresholds, pool, profiles={k: p for k, p in own.items() if p is not None}, eye=eye),
        "awake": replay_rows(items, thresholds, pool, profiles=awake_profiles(items, own), eye=eye),
    }


def personal_report(runs: dict[str, list[dict[str, Any]]], splits: dict[str, set[str] | None], title: str) -> str:
    """Markdown: metrics() of each setting on each split (None = every subject)."""
    lines = [
        f"# {title}",
        "",
        "Blocks 7-12 replayed on the stored UTA-RLDD traces (`tools/uta_rldd.py personal`). Driver enrollment (M9) "
        "never runs in the evaluations (a simulated 60 km/h from the first frame), so its result is imitated: the "
        "medians of the good frames of the first seconds of a video (`eval.fake_enroll_s`) give the open-eye EAR, "
        "closed-mouth MAR and road pose, handed to blocks 7 and 8 the way a finished enrollment does.",
        "",
    ]
    lines += [f"- **{name}**: {text}." for name, text in PERSONAL_SETTINGS]
    lines += [
        "",
        "`own` is what a real enrollment at the start of the trip would give (a drowsy driver enrolls drowsy). "
        "`awake` is the best case: the baseline of the same person when alert, used for their `5` and `10` videos "
        "(for a `0` video it is the same as `own`). The enrollment seconds lie inside the start-up stretch that no "
        "score counts. False alarms = drowsiness-branch alerts on `0` after the start-up stretch.",
        "",
        "| Subjects | Setting | " + " | ".join(h for _, h, _ in GRID_COLUMNS) + " |",
        "|---|---|" + "---:|" * len(GRID_COLUMNS),
    ]
    for split, subjects in splits.items():
        for name, _ in PERSONAL_SETTINGS:
            rows = [r for r in runs[name] if subjects is None or r["subject"] in subjects]
            if not rows:
                continue
            m = metrics(rows)
            lines.append(
                f"| {split} ({m['subjects']}) | {name} | "
                + " | ".join(fmt(m.get(k)) for k, _, fmt in GRID_COLUMNS)
                + " |"
            )
    lines += [
        "",
        "## Reading it",
        "",
        "- One subject has one `0` video of ~10 min: the settings differ by a few alerts at most, and their CIs "
        "overlap. A small difference is not a result.",
        "- The Kaggle copy carries no per-subject attributes (glasses), so there is no eyewear split here.",
        "- The subjects sit at a laptop: the enrolled road pose is not tested by this dataset (distraction is "
        "scored apart from drowsiness everywhere above).",
        '- Do not write "personalised" as a measured benefit in a report unless this table shows one.',
    ]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    import argparse

    from edge_agent.config import load_thresholds

    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("study", choices=("report", "signals", "grid", "compare", "personal"))
    p.add_argument("--split", choices=("dev", "test", "all"), default="dev")
    p.add_argument("--set", action="append", default=[], help="what-if threshold, e.g. risk.drowsy.l1=45")
    p.add_argument("--out", default=None)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument(
        "--eye",
        choices=("trace", "block5"),
        default="block5",
        help="block 5 as traced on Kaggle (thresholds of that commit), or decided again with today's thresholds",
    )
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = p.parse_args(argv)
    base = load_thresholds()
    th = make_thresholds(base, args.set)
    what = "config/thresholds.yaml" + (f" with {', '.join(args.set)}" if args.set else "")
    what += "; block 5 as traced" if args.eye == "trace" else "; block 5 decided again from the traced inputs"
    pool = replay_pool(args.workers)
    try:
        if args.study == "grid":  # the search never sees the held-out subjects
            results = run_configs(default_grid(), load_items("dev"), th, pool, eye=args.eye)
            text = grid_report(results, "DriverGuard - UTA-RLDD, threshold search and ablation (dev)", f"From {what}.")
        elif args.study == "compare":
            results = run_configs(
                [("current", []), ("what-if", args.set)], load_items(args.split), base, pool, eye=args.eye
            )
            text = grid_report(
                results, f"DriverGuard - UTA-RLDD, current thresholds against a what-if ({args.split})", f"From {what}."
            )
        elif args.study == "personal":
            runs = personal_study(load_items("all"), th, pool, args.eye)
            splits = {"all": None, "dev": split_subjects("dev"), "test": split_subjects("test")}
            text = personal_report(runs, splits, f"DriverGuard - does a per-driver baseline help? (UTA-RLDD, {what})")
        else:
            rows = replay_rows(load_items(args.split), th, pool, extras=True, eye=args.eye)
            if args.study == "signals":
                text = signals_report(rows, f"DriverGuard - UTA-RLDD, which signals follow the level ({args.split})")
            else:
                text = baseline_report(rows, th, f"DriverGuard - UTA-RLDD ({args.split})", f"Thresholds: {what}.")
    finally:
        if pool is not None:
            pool.shutdown()
    print(text)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
