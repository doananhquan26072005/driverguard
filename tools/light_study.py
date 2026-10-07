"""Same videos, other light: darken / overexpose / grey / blur each frame in RAM before block 2 (M46).

    python tools/light_study.py --out eval/results/lighting_transforms.md
    python tools/light_study.py --datasets fl3d --limit 4 --workers 4        # a quick look

eval/results/lighting.md splits the datasets by the brightness they happen to have: other people,
other cameras in every group. Here the SAME video runs through blocks 2-12 once per transform, so
a row differs from "original" by the light alone:
- gamma g:  out = 255 x (in / 255) ^ g, darker for g > 1 (eval.light_gammas)
- gain k:   out = min(in x k, 255), overexposed for k > 1 (eval.light_gains); the whole image, not a
            sun patch on the face
- grey:     the three channels replaced by the luminance (stands in for an infrared camera: block 2
            calls it IR, block 5's eye CNN decides)
- blur s:   Gaussian blur of sigma s pixels on the 640-wide image scale (eval.light_blur_sigmas)

Per transform: face found, median face brightness / sharpness (block 6 quality numbers), frames the
eye CNN decided, monitoring unavailable and why, what is still detected (FL3D microsleep runs
reaching L3, eyes closed per frame; YawDD yawns) and the alerts raised where none is due.

These are synthetic changes of real videos: no sensor noise of a dark cabin, no real IR image, no
glare patch. They say where the pipeline breaks, not how often that light occurs.

Privacy: frames are transformed and read in RAM only; nothing here writes an image.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.metrics import EvalConfig, ci_text, rate_ci  # noqa: E402
from tools.seq_eval import Tracer, dataset_videos, load_fl3d_labels, prf  # noqa: E402
from tools.trace_studies import DATASET_NOTE, _p, _share, condition_rows  # noqa: E402

ORIGINAL = "original"
REASONS = ("no_face", "camera_blocked", "bad_angle", "low_light", "glare", "blur")
POSITIVE = {"fl3d": "Microsleep runs reaching L3", "yawdd": "Yawning clips with a yawn event"}


# --------------------------------------------------------------------------- transforms (pure, in RAM)
def gamma(image: np.ndarray, g: float) -> np.ndarray:
    lut = np.clip(255.0 * (np.arange(256) / 255.0) ** g, 0, 255).astype(np.uint8)
    return lut[image]


def gain(image: np.ndarray, k: float) -> np.ndarray:
    return np.clip(image.astype(np.float32) * k, 0, 255).astype(np.uint8)


def grey(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return np.repeat(image[..., None], 3, axis=2)
    y = (0.114 * image[..., 0] + 0.587 * image[..., 1] + 0.299 * image[..., 2]).astype(np.uint8)  # BGR
    return np.repeat(y[..., None], 3, axis=2)


def blur(image: np.ndarray, sigma: float, reference_width: int = 640) -> np.ndarray:
    """sigma is given on the reference width (block 2's output), scaled to this image's width."""
    import cv2

    s = sigma * image.shape[1] / reference_width
    return cv2.GaussianBlur(image, (0, 0), s)


def transforms(cfg: EvalConfig) -> dict[str, tuple[str, float]]:
    """Name -> (kind, parameter), in report order."""
    out: dict[str, tuple[str, float]] = {ORIGINAL: ("none", 0.0)}
    out |= {f"gamma {g:g}": ("gamma", float(g)) for g in cfg.light_gammas}
    out |= {f"gain {k:g}": ("gain", float(k)) for k in cfg.light_gains}
    out["grey"] = ("grey", 0.0)
    out |= {f"blur {s:g}": ("blur", float(s)) for s in cfg.light_blur_sigmas}
    return out


def apply(image: np.ndarray, kind: str, value: float) -> np.ndarray:
    if kind == "gamma":
        return gamma(image, value)
    if kind == "gain":
        return gain(image, value)
    if kind == "grey":
        return grey(image)
    if kind == "blur":
        return blur(image, value)
    return image


# --------------------------------------------------------------------------- one video, one transform
def trace_transformed(path: Path, thresholds: dict[str, Any], kind: str, value: float) -> dict:
    """seq_eval.trace_video with every frame transformed first; adds why monitoring was unavailable."""
    import cv2

    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            raise RuntimeError(f"cannot open {path}")
        fps = cap.get(cv2.CAP_PROP_FPS)
        fps = fps if 0 < fps < 1000 else 30.0
        reasons: Counter = Counter()
        issues: Counter = Counter()
        with Tracer(thresholds, 60.0, use_phone=False) as tracer:
            i = 0
            while True:
                ok, image = cap.read()
                if not ok:
                    break
                r = tracer.step(apply(image, kind, value), i, i / fps)
                if r.risk.unavailable:
                    reasons[r.risk.unavailable_reason or "no_face"] += 1
                if r.quality.issue is not None:
                    issues[r.quality.issue] += 1
                i += 1
            tr = tracer.result(fps)
        tr["unavailable_reasons"] = dict(reasons)
        tr["quality_issues"] = dict(issues)
        return tr
    finally:
        cap.release()


def _job(args: tuple[str, str, str, str, dict[str, Any], str, float]) -> tuple[str, str, str, dict | str]:
    dataset, key, name, path, thresholds, kind, value = args
    try:
        return dataset, key, name, trace_transformed(Path(path), thresholds, kind, value)
    except Exception as e:  # noqa: BLE001 - one broken clip must not stop the run
        return dataset, key, name, f"{type(e).__name__}: {e}"


def pick(videos: dict[str, Path], limit: int | None, dataset: str) -> dict[str, Path]:
    """Evenly spaced videos; YawDD: half yawning clips, half others, so both columns have data."""
    if not limit or limit >= len(videos):
        return videos
    keys = sorted(videos)
    if dataset == "yawdd":
        yawn = [k for k in keys if "yawning" in k.lower()]
        rest = [k for k in keys if "yawning" not in k.lower()]
        half = max(1, limit // 2)
        chosen = yawn[:: max(1, len(yawn) // half)][:half] + rest[:: max(1, len(rest) // half)][:half]
    else:
        chosen = keys[:: max(1, len(keys) // limit)][:limit]
    return {k: videos[k] for k in chosen}


# --------------------------------------------------------------------------- report
def summarise(dataset: str, traces: dict[str, dict], thresholds: dict[str, Any]) -> dict[str, Any]:
    """One table row: coverage, quality numbers, unavailable by reason, detections and false alerts."""
    g = condition_rows(dataset, traces, thresholds, lambda k, st: "all")["all"]
    frames = sum(tr["n"] for tr in traces.values())
    cols = [tr["cols"] for tr in traces.values()]

    def median(name: str) -> float | None:
        v = np.concatenate([c[name][~np.isnan(c[name])] for c in cols]) if cols else np.array([])
        return float(np.median(v)) if len(v) else None

    reasons: Counter = Counter()
    for tr in traces.values():
        reasons.update(tr.get("unavailable_reasons", {}))
    row: dict[str, Any] = {
        "videos": len(traces),
        "minutes": g["seconds"] / 60,
        "face": _share(g["face"], g["frames"]),
        "bright": median("face_bright"),
        "sharp": median("sharpness"),
        "cnn": _share(g["cnn"], g["known"]),
        "unavailable": _share(sum(float(np.nansum(c["unavailable"])) for c in cols), frames),
        "reasons": {r: n / frames for r, n in reasons.items()} if frames else {},
        "pos_hit": int(g["pos_hit"]),
        "pos": int(g["pos_clips"]),
        "false_alerts": int(g["neg_alerts"]),
        "neg_hours": g["neg_s"] / 3600,
    }
    if dataset == "fl3d":
        labels = load_fl3d_labels()
        truth, pred = [], []
        for vid, tr in traces.items():
            c = tr["cols"]
            for frame, state in labels.get(vid, {}).items():
                if 0 <= frame < tr["n"] and state in ("microsleep", "alert"):
                    truth.append(state == "microsleep")
                    pred.append(c["eye_closed"][frame] == 1)
        row["eye"] = prf(np.array(pred, bool), np.array(truth, bool)) if truth else None
    return row


def _n(v: float | None, d: int = 0) -> str:
    return "–" if v is None else f"{v:.{d}f}"


def table(dataset: str, rows: dict[str, dict[str, Any]], order: Sequence[str]) -> list[str]:
    eye = dataset == "fl3d"
    head = (
        "| Transform | Face found | Face brightness | Sharpness | CNN-decided | Unavailable (why) | "
        f"{POSITIVE[dataset]} |" + (" Eyes closed: recall | FPR |" if eye else "") + " False alerts / hour (95% CI) |"
    )
    lines = [head, "|---|---:|---:|---:|---:|---|---:|" + ("---:|---:|" if eye else "") + "---:|"]
    for name in [n for n in order if n in rows]:
        r = rows[name]
        why = ", ".join(f"{k} {_p(v)}" for k, v in sorted(r["reasons"].items(), key=lambda kv: -kv[1]))
        unavailable = _p(r["unavailable"]) + (f" ({why})" if why else "")
        hit = f"{r['pos_hit']}/{r['pos']} ({_p(_share(r['pos_hit'], r['pos']))})" if r["pos"] else "–"
        cells = [name, _p(r["face"]), _n(r["bright"]), _n(r["sharp"], 1), _p(r["cnn"]), unavailable, hit]
        if eye:
            e = r.get("eye") or {}
            cells += [_p(e.get("recall")), _p(e.get("fpr"))]
        cells.append(f"{ci_text(rate_ci(r['false_alerts'], r['neg_hours']))} [{r['false_alerts']}]")
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def report(results: dict[str, dict[str, dict[str, dict]]], thresholds: dict[str, Any], order: Sequence[str]) -> str:
    q, u = thresholds["quality"], thresholds["risk"]["unavailable"]
    lines = [
        "# DriverGuard - the same videos in other light",
        "",
        "`tools/light_study.py`: every frame is darkened, overexposed, turned grey or blurred in RAM before block 2, "
        "then blocks 2-12 run as usual. A row differs from `original` by the transform alone (same people, same "
        "camera, same acting), which eval/results/lighting.md could not say. No image is written.",
        "",
        "- `gamma g`: 255 x (in / 255) ^ g, darker. `gain k`: in x k clipped at 255, overexposed (whole image).",
        "- `grey`: channels replaced by the luminance; block 2 then calls the image infrared and block 5's eye CNN "
        "decides. `blur s`: Gaussian blur, sigma s pixels at 640 px width.",
        "- Face brightness / sharpness: medians of the block 6 quality numbers on frames with a face (mean "
        "luminance 0-255 before CLAHE; Laplacian variance).",
        f"- Unavailable: share of frames with monitoring unavailable and why (`risk.unavailable`: no face "
        f"{u['no_face_s']} s, unusable face {u['low_quality_s']} s; `quality`: dark < {q['dark_face_brightness']}, "
        f"glare > {q['glare_face_brightness']}, blur < {q['blur_sharpness']}).",
        "- False alerts: as in lighting.md (FL3D: on `alert` frames more than 3 s from a drowsy run; YawDD: on "
        "normal / talking clips), the count in brackets.",
        "",
        "**Limits.** Synthetic changes: no sensor noise of a dark cabin, no real infrared image, no sun patch on "
        "half a face. A few videos per dataset, so the detection columns move by one or two events. This shows "
        "where the pipeline stops working, not how often such light occurs on the road.",
    ]
    for dataset, by_transform in results.items():
        rows = {name: summarise(dataset, traces, thresholds) for name, traces in by_transform.items() if traces}
        if not rows:
            continue
        first = next(iter(rows.values()))
        lines += [
            "",
            f"## {dataset}",
            "",
            f"{DATASET_NOTE[dataset]}. {first['videos']} videos, {first['minutes']:.1f} min per transform.",
            "",
        ]
        lines += table(dataset, rows, order)
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    from multiprocessing import get_context

    from edge_agent.config import load_thresholds

    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--datasets", nargs="+", default=["fl3d", "yawdd"], choices=["fl3d", "yawdd"])
    p.add_argument("--limit", type=int, default=8, help="videos per dataset (evenly spaced)")
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--out", default=None, help="write the report here (default: print)")
    args = p.parse_args(argv)

    thresholds = load_thresholds()
    plan = transforms(EvalConfig.from_dict(thresholds.get("eval")))
    jobs = []
    for dataset in args.datasets:
        for key, path in pick(dataset_videos(dataset), args.limit, dataset).items():
            jobs += [(dataset, key, name, str(path), thresholds, kind, value) for name, (kind, value) in plan.items()]
    print(f"[light_study] {len(jobs)} runs ({len(plan)} transforms), {args.workers} workers", file=sys.stderr)
    results: dict[str, dict[str, dict[str, dict]]] = defaultdict(lambda: defaultdict(dict))
    t0 = time.perf_counter()
    with get_context("spawn").Pool(args.workers) as pool:
        for n, (dataset, key, name, res) in enumerate(pool.imap_unordered(_job, jobs), 1):
            if isinstance(res, str):
                print(f"[light_study] {key} / {name}: {res}", file=sys.stderr)
            else:
                results[dataset][name][key] = res
            if n % 20 == 0 or n == len(jobs):
                print(f"[light_study] {n}/{len(jobs)}, {time.perf_counter() - t0:.0f} s", file=sys.stderr)
    text = report({d: dict(results[d]) for d in args.datasets}, thresholds, list(plan))
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"[light_study] wrote {args.out}", file=sys.stderr)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
