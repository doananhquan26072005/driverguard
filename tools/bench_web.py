"""Speed of the in-browser agent's Python (blocks 6-14) in Pyodide, next to the same call on the device.

    python tools/bench_web.py --label "before M49"            # synthetic moving face, 60 s
    python tools/bench_web.py --label "Mac, YawDD clip" --clip data/.../clip.avi

The product is the web code wrapped in an APK, and there blocks 6-14 run in Pyodide (WebAssembly),
not in the CPython that tools/benchmark.py measures. This tool times the page's per-frame call,
`WebAgent.frame()` + JSON, on the same landmark numbers in both: natively (with OpenCV, the device's
case) and in Pyodide under Node (frontend/bench/bridge.bench.mjs; needs `npm ci` in frontend/ and,
the first time, the network for Pyodide's numpy / pyyaml / sqlite3 packages).

Input, numbers only (no image is made or stored):
- default: a synthetic face (tests/test_edge_agent/test_web_bridge.py) whose head turns slowly, with
  landmark jitter and a blink every few seconds, so the head-pose fit has work to do on every frame;
- --clip: the landmarks MediaPipe finds in a video, kept in RAM.

Each run is one entry (by --label) in eval/results/benchmark_web.json; the table
eval/results/benchmark_web.md is rewritten from all of them, so a change has its before and after.
Node is not a browser and a development machine is not the hub: these are the costs of the Python
part only, to compare versions of the code. Canvas, MediaPipe and YOLO are timed by the page itself.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from edge_agent.perception.features import POSE_LANDMARKS, POSE_MODEL_POINTS  # noqa: E402
from edge_agent.perception.geometry import rodrigues  # noqa: E402
from edge_agent.web.bridge import WebAgent  # noqa: E402
from tests.test_edge_agent.test_web_bridge import H, W, synthetic_face  # noqa: E402
from tools.build_web_py import build  # noqa: E402

RESULTS_JSON = ROOT / "eval" / "results" / "benchmark_web.json"
RESULTS_MD = ROOT / "eval" / "results" / "benchmark_web.md"
BENCH_SCRIPT = ROOT / "frontend" / "bench" / "bridge.bench.mjs"
SCENARIO = "city_day"  # driving, so blocks 7-12 judge every frame
FACE_DISTANCE_CM = 60.0
BLINK_EVERY_S = 4.0
BLINK_FRAMES = 4


def moving_faces(seconds: float, fps: float, seed: int = 0, jitter_px: float = 0.3) -> list[dict[str, Any]]:
    """One frame per 1 / fps: the synthetic face with its rigid points turned by a slow head motion
    (yaw +-25, pitch +-10, roll +-5 degrees), every landmark jittered, a short blink now and then."""
    rng = np.random.default_rng(seed)
    faces = {False: synthetic_face(ear=0.30), True: synthetic_face(ear=0.05)}
    idx = list(POSE_LANDMARKS)
    blink_period = max(int(BLINK_EVERY_S * fps), BLINK_FRAMES + 1)
    out = []
    for i in range(int(seconds * fps)):
        t = i / fps
        yaw, pitch, roll = 25 * np.sin(t / 1.5), 10 * np.sin(t / 2.3), 5 * np.sin(t / 1.0)
        rmat = (
            rodrigues(np.array([0.0, 0.0, np.radians(roll)]))
            @ rodrigues(np.array([0.0, np.radians(yaw), 0.0]))
            @ rodrigues(np.array([np.radians(pitch), 0.0, 0.0]))
        )
        p = POSE_MODEL_POINTS @ rmat.T + np.array([0.0, 0.0, FACE_DISTANCE_CM])
        closed = i % blink_period < BLINK_FRAMES and i >= blink_period
        pts = faces[closed].copy()
        pts[idx, 0] = W * p[:, 0] / p[:, 2] + W / 2  # pinhole camera, f = image width
        pts[idx, 1] = W * p[:, 1] / p[:, 2] + H / 2
        pts[:, :2] += rng.normal(0.0, jitter_px, (len(pts), 2)).astype(np.float32)
        blink = [0.9, 0.9] if closed else [0.05, 0.05]
        out.append({"points": [round(float(v), 2) for v in pts.ravel()], "blink": blink, "brow": 0.0})
    return out


def clip_faces(path: str, max_frames: int) -> list[dict[str, Any]]:
    """Landmarks of the driver in a video's first frames (frames without a face are skipped). RAM only."""
    import cv2

    from edge_agent.capture.frame_source import Frame
    from edge_agent.config import load_thresholds
    from edge_agent.perception import PreprocessConfig, Preprocessor
    from edge_agent.perception.landmarks import FaceLandmarkDetector, LandmarkConfig

    th = load_thresholds()
    pre = Preprocessor(PreprocessConfig.from_dict(th.get("preprocess")))
    out: list[dict[str, Any]] = []
    cap = cv2.VideoCapture(path)
    with FaceLandmarkDetector(LandmarkConfig.from_dict(th.get("landmarks"))) as detector:
        i = 0
        while len(out) < max_frames:
            ok, image = cap.read()
            if not ok:
                break
            lm = detector.detect(pre(Frame(image=image, frame_id=i, timestamp=i / 30.0)))
            i += 1
            if lm is None:
                continue
            if (lm.image_width, lm.image_height) != (W, H):
                raise SystemExit(f"--clip: frames are {lm.image_width}x{lm.image_height} after block 2, need {W}x{H}")
            blink = list(lm.eye_blink or (0.05, 0.05))
            out.append(
                {"points": [round(float(v), 2) for v in lm.points.ravel()], "blink": blink, "brow": lm.brow_up or 0.0}
            )
    cap.release()
    if not out:
        raise SystemExit(f"--clip: no face found in {path}")
    return out


def summarize(ms: list[float]) -> dict[str, float]:
    a = np.sort(np.asarray(ms, dtype=float))
    return {
        "mean_ms": float(a.mean()),
        "p50_ms": float(np.percentile(a, 50)),
        "p95_ms": float(np.percentile(a, 95)),
        "p99_ms": float(np.percentile(a, 99)),
        "max_ms": float(a[-1]),
    }


def time_native(doc: dict[str, Any]) -> dict[str, float]:
    """The same call in this CPython (OpenCV present: the device's head pose)."""
    agent = WebAgent("bench", "trip-bench", scenario=doc["scenario"])
    frames = [(np.asarray(f["points"], np.float32), f["blink"], [f["brow"]]) for f in doc["frames"]]
    ms = []
    for i, (pts, blink, brow) in enumerate(frames):
        t0 = time.perf_counter()
        json.loads(agent.frame(100 + i / doc["fps"], i, W, H, pts, 1, blink, 30.0, 110.0, brow, 110.0, 40.0, 150.0))
        ms.append((time.perf_counter() - t0) * 1000.0)
    return summarize(ms[doc["warmup_frames"] :])


def time_pyodide(doc: dict[str, Any]) -> dict[str, Any]:
    if not (ROOT / "frontend" / "node_modules" / "pyodide").exists():
        raise SystemExit("Pyodide for Node is missing: run `npm ci` in frontend/")
    with tempfile.TemporaryDirectory() as tmp:
        zip_path, frames_path = Path(tmp) / "edge_agent.zip", Path(tmp) / "frames.json"
        build(zip_path)  # the code as it is now, not the last `npm run prepare-live`
        frames_path.write_text(json.dumps(doc))
        run = subprocess.run(
            ["node", str(BENCH_SCRIPT), str(zip_path), str(frames_path)],
            cwd=ROOT / "frontend",
            capture_output=True,
            text=True,
            timeout=1800,
            check=False,
        )
    if run.returncode != 0:
        raise SystemExit(f"node {BENCH_SCRIPT.name} failed:\n{run.stderr[:2000]}")
    return json.loads(run.stdout.strip().splitlines()[-1])


def report(runs: dict[str, dict[str, Any]]) -> str:
    lines = [
        "# DriverGuard - speed of the in-browser agent's Python (blocks 6-14)",
        "",
        "One row per run of `tools/bench_web.py`: the page's per-frame call `WebAgent.frame()` + JSON on the same "
        "landmark numbers, in CPython with OpenCV (the device's case) and in Pyodide under Node (the code of "
        "`#/live` and the APK). Node is not a browser and these machines are not the hub: the rows compare "
        "versions of the code. Canvas, MediaPipe and YOLO are not in these numbers.",
        "",
        "| Run | Date | Machine | Input | Device: p50 / p95 ms | Pyodide: p50 / p95 / max ms | Pyodide / device "
        "| Head pose (solve_pnp) share | Projections / frame | Pyodide start (ms) |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for label, r in runs.items():
        n, w = r["native"], r["pyodide"]
        shares = w.get("shares", {})
        lines.append(
            f"| {label} | {r['date']} | {r['machine']} | {r['input']} "
            f"| {n['p50_ms']:.2f} / {n['p95_ms']:.2f} "
            f"| {w['p50_ms']:.2f} / {w['p95_ms']:.2f} / {w['max_ms']:.1f} "
            f"| {w['p50_ms'] / n['p50_ms']:.1f}x "
            f"| {100 * shares.get('head_pose_solve_pnp', 0.0):.0f} % "
            f"| {w.get('project_calls_per_frame', 0.0):.1f} "
            f"| {w['startup_ms']:.0f} |"
        )
    lines += [
        "",
        "- Share: cumulative time of `geometry.solve_pnp` over that of `bridge._frame`, under cProfile in "
        "Pyodide. Projections: passes over the model points per frame (`geometry._project` and `_jacobian`).",
        "- Pyodide start: runtime + numpy + pyyaml + sqlite3 + `WebAgent()` from the local disk, without downloads.",
        "- Software of the last run: " + "; ".join(f"{k} {v}" for k, v in list(runs.values())[-1]["software"].items())
        if runs
        else "",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--label", required=True, help="name of this run in the table (an existing one is replaced)")
    p.add_argument("--seconds", type=float, default=60.0, help="length of the synthetic sequence")
    p.add_argument("--fps", type=float, default=30.0)
    p.add_argument("--warmup-s", type=float, default=10.0, help="start of the sequence left out of the timings")
    p.add_argument("--clip", default=None, help="video to take real landmarks from, instead of the synthetic face")
    p.add_argument("--clip-frames", type=int, default=1800)
    p.add_argument("--json", default=str(RESULTS_JSON))
    p.add_argument("--out", default=str(RESULTS_MD))
    args = p.parse_args(argv)

    if args.clip:
        frames = clip_faces(args.clip, args.clip_frames)
        source = f"{Path(args.clip).name}, {len(frames)} frames with a face"
    else:
        frames = moving_faces(args.seconds, args.fps)
        source = f"synthetic moving face, {args.seconds:.0f} s at {args.fps:.0f} FPS"
    warmup = min(int(args.warmup_s * args.fps), len(frames) // 2)
    doc = {"scenario": SCENARIO, "fps": args.fps, "width": W, "height": H, "warmup_frames": warmup, "frames": frames}

    native = time_native(doc)
    web = time_pyodide(doc)
    run = {
        "date": time.strftime("%d/%m/%Y"),
        "machine": f"{platform.machine()}, {platform.system()}",
        "input": source,
        "native": native,
        "pyodide": web,
        "software": {
            "Python": platform.python_version(),
            "numpy": np.__version__,
            "Pyodide": web.get("pyodide", "?"),
            "Node": web.get("node", "?"),
        },
    }
    json_path = Path(args.json)
    runs = json.loads(json_path.read_text()) if json_path.exists() else {}
    runs[args.label] = run
    json_path.write_text(json.dumps(runs, indent=1) + "\n")
    Path(args.out).write_text(report(runs))
    print(
        f"{args.label}: device p50 {native['p50_ms']:.2f} ms, Pyodide p50 {web['p50_ms']:.2f} / p95 "
        f"{web['p95_ms']:.2f} ms, solve_pnp {100 * web.get('shares', {}).get('head_pose_solve_pnp', 0):.0f} %, "
        f"{web.get('project_calls_per_frame', 0):.1f} projections / frame -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
