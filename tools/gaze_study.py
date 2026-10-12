"""Looking down, looking away and closed eyes on 3MDAD: 50 drivers in a real car, face camera.

    python tools/gaze_study.py trace --out data/eval_traces/3mdad_day.pkl
    python tools/gaze_study.py report --traces data/eval_traces/3mdad_day.pkl --out eval/results/gaze_3mdad.md

Own recordings (one person, docs/improvements.md) left two questions open: can looking down be
seen when the head hardly moves, and can it be told from closed eyes. 3MDAD (Jegham et al. 2020,
frontal view "RGB2", daytime) has 16 acted actions per driver as short frame sequences: safe
driving, writing a message with either hand, phone calls, the radio, the GPS, talking to the
passenger, fatigue... The frames of one driver are run through blocks 2-12 as one drive, action
after action, with the label of each action kept as an interval.

LIMITS, read before the numbers:
- The frame rate is not stored with the frames; `--fps` (30) is an assumption. Everything counted
  in frames (sections 1, 4) does not depend on it; alerts and "held for 2 s" (2, 3) do.
- A label covers the whole sequence of an action, also the frames where the driver is reaching
  for the phone or already looking back at the road.
- Sequences are 3-5 s long at 30 FPS and are joined end to end: the pose and the eye baseline of
  one action carry over into the next. Safe driving comes first so the baselines start there.
- Acted, parked or slow car, one camera position. Action names: from the dataset paper; safe
  driving, messages, calls, picture, passenger, fatigue and drinking were checked by eye on one driver.

Images are read into RAM only; the trace holds numbers and a driver index, no image.
"""

from __future__ import annotations

import argparse
import pickle
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from edge_agent.config import PROJECT_ROOT  # noqa: E402
from tools.seq_eval import auc  # noqa: E402

ROOT = PROJECT_ROOT / "data/kaggle/datasets/anouarbenkhalifa/3mdad-multimodal-driver-action-distraction/Day-RGB2/RGB2"
ACTIONS = {
    1: "safe driving",
    2: "hair / makeup",
    3: "adjusting the radio",
    4: "operating the GPS",
    5: "writing a message, right hand",
    6: "writing a message, left hand",
    7: "phone call, right hand",
    8: "phone call, left hand",
    9: "taking a picture",
    10: "talking to the passenger",
    11: "singing / dancing",
    12: "fatigue",
    13: "drinking, right hand",
    14: "drinking, left hand",
    15: "reaching behind",
    16: "smoking",
}
SAFE = 1
TEXTING = (5, 6)
FRAME_NO = re.compile(r"F(\d+)\.jpg$")
MIN_FRAMES = 20  # frames a driver needs in an action before it is summarised


def frames_of(action_dir: Path) -> list[Path]:
    """The frames of one action, in recording order (F1, F2, ... F10, not F1, F10, F100)."""
    files = [(int(m.group(1)), p) for p in action_dir.glob("*.jpg") if (m := FRAME_NO.search(p.name))]
    return [p for _, p in sorted(files)]


# --------------------------------------------------------------------------- tracing (models)


def trace_driver(args: tuple[str, float]) -> tuple[str, dict]:
    """One driver: safe driving, then actions 2-16, through blocks 2-12 as one drive."""
    import cv2

    from edge_agent.config import load_thresholds
    from edge_agent.perception.phone_detector import PhoneDetectorConfig
    from tools.seq_eval import Tracer

    subject, fps = args
    th = load_thresholds()
    yolo_every = max(1, round(fps / PhoneDetectorConfig.from_dict(th.get("phone")).target_fps))
    labels: list[tuple[str, float, float]] = []
    with Tracer(th, 60.0, True, yolo_every) as tracer:
        i = 0
        for action in ACTIONS:
            start = i
            for p in frames_of(ROOT / subject / f"AC{action}"):
                image = cv2.imread(str(p))
                if image is None:
                    continue
                tracer.step(image, i, i / fps)
                i += 1
            if i > start:
                labels.append((f"AC{action}", start / fps, (i - 1) / fps))
        trace = tracer.result(fps)
    return subject, {**trace, "labels": labels, "tags": {"dataset": "3mdad_day"}, "source": "3mdad RGB2"}


def run_trace(out: Path, fps: float, workers: int, limit: int | None) -> None:
    """Trace every driver of 3MDAD in parallel and save the traces to `out`."""
    from multiprocessing import Pool

    subjects = sorted((p.name for p in ROOT.iterdir() if p.is_dir()), key=lambda s: int(s[1:]))[:limit]
    if not subjects:
        raise SystemExit(f"no 3MDAD subjects under {ROOT}")
    with Pool(workers) as pool:
        done = dict(pool.imap_unordered(trace_driver, [(s, fps) for s in subjects]))
    traces = {f"D{int(s[1:]):02d}": done[s] for s in subjects}  # an index, as in the dataset folders
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(pickle.dumps(traces))
    frames = sum(t["n"] for t in traces.values())
    print(f"[gaze_study] {len(traces)} drivers, {frames} frames at an assumed {fps:g} FPS -> {out} (numbers only)")


# --------------------------------------------------------------------------- report (pure)


def action_mask(tr: dict, action: int) -> np.ndarray:
    """Boolean mask of the frames of this trace labelled with action AC<action>."""
    t = tr["cols"]["t"]
    m = np.zeros(len(t), bool)
    for name, a, b in tr["labels"]:
        if name == f"AC{action}":
            m |= (t >= a - 1e-9) & (t <= b + 1e-9)
    return m


def driver_frame(tr: dict) -> dict[str, np.ndarray] | None:
    """Per-frame signals of one driver against that driver's own safe-driving frames; None without them."""
    c = tr["cols"]
    face = c["face"] == 1
    safe = action_mask(tr, SAFE) & face & (c["blink"] < 0.3)  # eyes open
    if safe.sum() < MIN_FRAMES:
        return None
    iris = (c["iris_y_l"] + c["iris_y_r"]) / 2.0
    side = (c["iris_x_r"] - c["iris_x_l"]) / 2.0  # outer -> inner in each eye: half the difference = sideways
    ear0 = float(np.nanmedian(c["ear"][safe]))
    return {
        "face": face,
        "ear_ratio": c["ear"] / ear0,
        "blink": c["blink"],
        "look_down": (c["look_down_l"] + c["look_down_r"]) / 2.0,
        "iris_y": iris - float(np.nanmedian(iris[safe])),
        "iris_side": np.abs(side - float(np.nanmedian(side[safe]))),
        "pitch": c["pitch"] - float(np.nanmedian(c["pitch"][safe])),
        "yaw": np.abs(c["yaw"] - float(np.nanmedian(c["yaw"][safe]))),
        "eye_closed": c["eye_closed"],
        "off_road": c["off_road"],
        "phone_flag": c["phone_flag"],
    }


def gaze_hits(traces: dict[str, dict], thresholds: dict[str, Any], down_deg: float) -> dict[int, tuple[int, int]]:
    """Per action: (drivers whose sequence reaches gaze_down_duration >= 2 s, drivers with a sequence of
    at least 2 s), blocks 5, 7-12 replayed with distraction.gaze.down_deg = down_deg."""
    import copy

    from tools.seq_eval import replay

    th = copy.deepcopy(thresholds)
    th["distraction"]["gaze"]["down_deg"] = down_deg
    out = {a: [0, 0] for a in ACTIONS}
    for tr in traces.values():
        r = replay(tr, th, eye="block5")
        t, held_s = r["cols"]["t"], r["cols"]["gaze_down_s"]
        for name, start, end in tr["labels"]:
            if end - start < 2.0:
                continue
            a = int(name[2:])
            out[a][1] += 1
            out[a][0] += bool(np.nanmax(held_s[(t >= start) & (t <= end)]) >= 2.0)
    return {a: (n, d) for a, (n, d) in out.items()}


def _q(v: np.ndarray) -> str:
    v = v[~np.isnan(v)]
    return "–" if len(v) == 0 else " / ".join(f"{x:.2f}" for x in np.percentile(v, [10, 50, 90]))


def _share(n: int, d: int) -> str:
    return "–" if d == 0 else f"{n} / {d} ({n / d:.0%})"


def report(traces: dict[str, dict], thresholds: dict[str, Any]) -> str:
    """The Markdown report of the gaze study."""
    deep_ear = thresholds["drowsiness"]["microsleep_deep"]["ear_ratio"]
    deep_blink = thresholds["drowsiness"]["microsleep_deep"]["blink"]
    frames = {name: f for name, tr in traces.items() if (f := driver_frame(tr)) is not None}
    masks = {(name, a): action_mask(traces[name], a) for name in frames for a in ACTIONS}
    fps = next(iter(traces.values()))["fps"]
    total = sum(tr["n"] for tr in traces.values())
    lines = [
        "# DriverGuard - looking down, looking away and closed eyes on 3MDAD",
        "",
        f"{len(traces)} drivers ({len(frames)} with usable safe-driving frames), {total} frames, 16 actions each, "
        f"real car, face camera, daytime. Blocks 2-12 with config/thresholds.yaml, each driver's actions joined "
        f"into one drive (safe driving first). Assumed frame rate: {fps:g} FPS (not stored with the frames).",
        "",
        "Every signal is taken against the same driver's safe-driving frames: EAR as a ratio of that median, "
        "iris_y, pitch and yaw as a difference (iris_y: iris centre against the line through the eye corners, in "
        "eye widths, > 0 = lower). A label covers the whole sequence of an action, also the frames where the driver "
        "reaches for the phone or looks back at the road. Acted. Numbers only, no image stored.",
        "",
        "## 1. The signals per action (frames with a face; p10 / p50 / p90 over all drivers)",
        "",
        f"Deep by today's rule: EAR ≤ {deep_ear} x the driver's safe-driving EAR and eyeBlink ≥ {deep_blink}, what "
        "block 7 counts toward a microsleep.",
        "",
        "| Action | Frames | Face found | EAR ratio | eyeBlink | eyeLookDown | iris_y | Pitch | Yaw (abs) | "
        "Deep by today's rule | Phone in the driver zone |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for a, title in ACTIONS.items():
        cat = {k: np.concatenate([f[k][masks[n, a]] for n, f in frames.items()]) for k in next(iter(frames.values()))}
        face = cat["face"]
        deep = (cat["ear_ratio"] <= deep_ear) & (cat["blink"] >= deep_blink)
        phone = cat["phone_flag"][face]
        lines.append(
            f"| AC{a} {title} | {len(face)} | {face.mean():.0%} | "
            + " | ".join(_q(cat[k][face]) for k in ("ear_ratio", "blink", "look_down", "iris_y", "pitch", "yaw"))
            + f" | {deep[face].mean():.1%} | {np.nanmean(phone) if np.isfinite(phone).any() else float('nan'):.0%} |"
        )

    lines += [
        "",
        f"## 2. What the system answers per action (alerts, at the assumed {fps:g} FPS)",
        "",
        "Drivers whose sequence of that action got at least one alert of the kind. L3 microsleep during a message "
        'is the false alarm of docs/improvements.md "looking down or eyes closed"; an alert in safe driving is a '
        "false alarm outright. Sequences last 3-5 s: an alert that needs 2 s has little room.",
        "",
        "| Action | Drivers | Median length (s) | L3 microsleep | off_road | phone | any alert |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for a, title in ACTIONS.items():
        n = ms = off = ph = anyone = 0
        lengths = []
        for tr in traces.values():
            spans = [(s, e) for name, s, e in tr["labels"] if name == f"AC{a}"]
            if not spans:
                continue
            n += 1
            lengths.append(sum(e - s for s, e in spans))
            t = tr["cols"]["t"]
            got = [set(rs) for i, _, rs in tr["alerts"] if any(s <= t[i] <= e for s, e in spans)]
            ms += any("microsleep" in g for g in got)
            off += any("off_road" in g for g in got)
            ph += any("phone" in g for g in got)
            anyone += bool(got)
        lines.append(
            f"| AC{a} {title} | {n} | {np.median(lengths):.1f} | {_share(ms, n)} | {_share(off, n)} | "
            f"{_share(ph, n)} | {_share(anyone, n)} |"
        )

    cuts = (10.0, 12.0, 15.0)
    by_cut = {c: gaze_hits(traces, thresholds, c) for c in cuts}
    lines += [
        "",
        f"## 3. The gaze-down angle as block 8 measures it, held for 2 s (at the assumed {fps:g} FPS)",
        "",
        "Blocks 5, 7-12 replayed with `distraction.gaze.down_deg` set to each value: head pitch off the road pose + "
        "`iris_gain` x (iris_y off the driver's usual value), frames block 7 calls firmly shut left out, the usual "
        "values learnt by the pipeline itself during the first seconds of the drive (safe driving). Drivers whose "
        "sequence of the action has `gaze_down_duration` ≥ 2 s. No alert reads this signal; the off_road and phone "
        "columns of section 2 are what the driver gets today.",
        "",
        "| Action | " + " | ".join(f"≥ {c:g}°" for c in cuts) + " |",
        "|---|" + "---:|" * len(cuts),
    ]
    for a, title in ACTIONS.items():
        lines.append(f"| AC{a} {title} | " + " | ".join(_share(*by_cut[c][a]) for c in cuts) + " |")
    lines += [
        "",
        "## 4. Writing a message against safe driving, driver by driver (AUC per frame)",
        "",
        "One AUC per driver with at least 20 frames of both; 0.5 = the signal does not separate them.",
        "",
        "| Signal | Drivers | Worst | p25 | Median | Pooled over drivers |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for key, sign in (("iris_y", 1), ("look_down", 1), ("pitch", 1), ("ear_ratio", -1)):
        per, pos_all, neg_all = [], [], []
        for n, f in frames.items():
            text = np.zeros(len(f["face"]), bool)
            for a in TEXTING:
                text |= masks[n, a]
            pos = f[key][text & f["face"]]
            neg = f[key][masks[n, SAFE] & f["face"]]
            pos, neg = pos[~np.isnan(pos)] * sign, neg[~np.isnan(neg)] * sign
            if len(pos) >= MIN_FRAMES and len(neg) >= MIN_FRAMES:
                per.append(auc(pos, neg))
                pos_all.append(pos)
                neg_all.append(neg)
        per = [v for v in per if v is not None]
        pooled = auc(np.concatenate(pos_all), np.concatenate(neg_all)) if pos_all else None
        lines.append(
            f"| {key} | {len(per)} | {min(per):.3f} | {np.percentile(per, 25):.3f} | {np.median(per):.3f} | "
            f"{pooled:.3f} |"
            if per and pooled is not None
            else f"| {key} | 0 | – | – | – | – |"
        )
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point (see the module doc). Returns the process exit code."""
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    tr = sub.add_parser("trace", help="run blocks 2-12 on every driver and save the numbers")
    tr.add_argument("--out", required=True)
    tr.add_argument("--fps", type=float, default=30.0, help="frame rate assumed for the sequences")
    tr.add_argument("--workers", type=int, default=4)
    tr.add_argument("--limit", type=int, default=None, help="only the first N drivers")
    rp = sub.add_parser("report", help="tables from saved traces")
    rp.add_argument("--traces", required=True)
    rp.add_argument("--out", default=None)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = p.parse_args(argv)
    if args.cmd == "trace":
        run_trace(Path(args.out), args.fps, args.workers, args.limit)
        return 0
    from edge_agent.config import load_thresholds

    text = report(pickle.loads(Path(args.traces).read_bytes()), load_thresholds())
    print(text)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
