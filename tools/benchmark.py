"""M7 - Speed benchmark: FPS, latency p50 / p95 per block, model sizes, YOLO FP32 vs INT8.

    python tools/benchmark.py --source data/videos/clip.mp4 --out eval/results/benchmark.md
    python tools/benchmark.py                 # synthetic frames (no face: MediaPipe looks faster than real)

Steps:
1. Load --frames frames from --source into RAM (a video with a face gives realistic
   MediaPipe timings; without --source, synthetic frames are used and flagged in the report).
2. Build models/yolov8n_int8.onnx if missing: static INT8 quantisation (QDQ, per-channel
   weights) calibrated on the same frames, letterboxed like at runtime.
3. Time every block alone (preprocess, face landmarks, features, decision chain, YOLO FP32,
   YOLO INT8), then the whole main loop (blocks 2-12, as fast as possible) with YOLO on its own
   thread at the configured rate, once with FP32 and once with INT8.
4. Compare INT8 with FP32 on the frames (phone score difference, detection agreement).
Frames stay in RAM; nothing but the report is written (plus the INT8 model on first run).

Long run (M42): `--duration` switches to the main loop alone, paced like a camera, for that long,
sampling once a second what a vehicle hub would run out of: CPU, memory, temperature, FPS.

    python tools/benchmark.py --source clip.mp4 --duration 60m --condition face --out eval/results/benchmark_soak.md
    python tools/benchmark.py --duration 10m --condition no_face          # synthetic frames
    python tools/edge_sim.py --profile jetson_nano --duration 10m --source clip.mp4   # the same in a limited container
    python tools/benchmark.py --duration 90s --pace-fps 0 --condition drawn_face --check   # CI (M87)

- Frames of --source are looped from RAM at --pace-fps (30 = a camera; 0 = as fast as possible).
- Every second: FPS, p95 frame latency, CPU of this process (100 % = one core), resident memory,
  CPU temperature where the OS gives one (Linux; macOS does not without extra tools).
- Verdict against `eval.soak_min_fps` (every minute) and `eval.soak_rss_growth_mb_per_h`.
- --profile NAME (config/edge_profiles.yaml) sets the thread counts of the profile and marks the
  report `simulated`. The CPU / memory limits themselves are applied from outside (a container:
  tools/edge_sim.py); the report prints the limits the process really sees (cgroup), so a run
  without them cannot pass for a limited one.
- --condition drawn_face needs no video: a face made of ellipses (tools/drawn_face.py) that MediaPipe
  finds on every frame, so the landmark model and blocks 5-6 do their work. --check makes the exit code
  1 when a judged criterion fails or FPS could not be judged: the CI step that measures FPS (M87).
A capped container on a fast machine is not the device: per-core speed, GPU and heat differ.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import sys
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from edge_agent.config import PROJECT_ROOT, load_thresholds  # noqa: E402

FPS_TARGET = 15.0  # CLAUDE.md: at least 15 FPS


# --------------------------------------------------------------------------- statistics (pure)


def summarize(ms: list[float]) -> dict[str, float]:
    """Latency list (ms) -> mean / p50 / p95 / max and the FPS it allows."""
    a = np.asarray(ms, dtype=float)
    mean = float(a.mean()) if a.size else float("nan")
    return {
        "n": int(a.size),
        "mean_ms": mean,
        "p50_ms": float(np.percentile(a, 50)) if a.size else float("nan"),
        "p95_ms": float(np.percentile(a, 95)) if a.size else float("nan"),
        "max_ms": float(a.max()) if a.size else float("nan"),
        "fps": 1000.0 / mean if a.size and mean > 0 else float("nan"),
    }


def iou(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def agreement(ref: list[tuple], other: list[tuple], iou_min: float = 0.5) -> tuple[int, int, int]:
    """(matched, only in ref, only in other) between two lists of per-frame detection tuples."""
    matched = only_ref = only_other = 0
    for r_dets, o_dets in zip(ref, other, strict=True):
        used: set[int] = set()
        for rd in r_dets:
            j = next((k for k, od in enumerate(o_dets) if k not in used and iou(rd.bbox, od.bbox) >= iou_min), None)
            if j is None:
                only_ref += 1
            else:
                used.add(j)
                matched += 1
        only_other += len(o_dets) - len(used)
    return matched, only_ref, only_other


def time_calls(fn: Callable[[Any], Any], items: list[Any], warmup: int) -> tuple[list[float], list[Any]]:
    outputs, ms = [], []
    for i, item in enumerate(items):
        t0 = time.perf_counter()
        out = fn(item)
        dt = (time.perf_counter() - t0) * 1000.0
        if i >= warmup:
            ms.append(dt)
        outputs.append(out)
    return ms, outputs


def file_mb(path: Path) -> float | None:
    return path.stat().st_size / 1e6 if path.exists() else None


# --------------------------------------------------------------------------- inputs and models


def load_frames(source: str | None, n: int) -> tuple[list[np.ndarray], str]:
    if source:
        cap = cv2.VideoCapture(int(source) if source.isdigit() else source)
        frames = []
        while len(frames) < n:
            ok, img = cap.read()
            if not ok:
                if not frames or source.isdigit():
                    break
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # loop a short clip
                continue
            frames.append(img)
        cap.release()
        if frames:
            h, w = frames[0].shape[:2]
            return frames, f"{source} ({w}x{h}, {len(frames)} frames)"
        print(f"[benchmark] cannot read {source}, using synthetic frames", file=sys.stderr)
    rng = np.random.default_rng(0)
    base = rng.integers(0, 255, (720, 1280, 3), dtype=np.uint8)
    frames = [np.roll(base, 7 * i, axis=1) for i in range(n)]
    return frames, f"synthetic noise 1280x720, {n} frames (NO FACE: MediaPipe timings are optimistic)"


def quantize_yolo(fp32: Path, int8: Path, calib: list[np.ndarray], input_size: int) -> None:
    """Static INT8 (QDQ, per-channel) calibrated on letterboxed frames."""
    from onnxruntime.quantization import CalibrationDataReader, QuantFormat, QuantType, quantize_static
    from onnxruntime.quantization.shape_inference import quant_pre_process

    from edge_agent.perception.phone_detector import letterbox

    class Reader(CalibrationDataReader):
        def __init__(self) -> None:
            from edge_agent.perception.onnx import load_ort

            ort = load_ort()

            name = ort.InferenceSession(str(fp32), providers=["CPUExecutionProvider"]).get_inputs()[0].name
            blobs = (cv2.dnn.blobFromImage(letterbox(f, input_size)[0], 1 / 255.0, swapRB=True) for f in calib)
            self._it = iter([{name: b} for b in blobs])

        def get_next(self) -> dict[str, np.ndarray] | None:
            return next(self._it, None)

    prepped = int8.with_suffix(".prep.onnx")
    # Static 640x640 input: plain ONNX shape inference is enough (no sympy needed).
    quant_pre_process(str(fp32), str(prepped), skip_symbolic_shape=True)
    try:
        quantize_static(
            str(prepped),
            str(int8),
            Reader(),
            quant_format=QuantFormat.QDQ,
            per_channel=True,
            weight_type=QuantType.QInt8,
            activation_type=QuantType.QUInt8,
        )
    finally:
        prepped.unlink(missing_ok=True)


# --------------------------------------------------------------------------- measurements


def main_loop(frames: list[np.ndarray], th: dict[str, Any], yolo_model: Any, warmup: int) -> dict[str, float]:
    """Blocks 2-12 as fast as possible, YOLO on its own thread (as edge_agent.main runs them)."""
    from edge_agent.capture import Frame
    from edge_agent.context.can_sim import CanSimulator, scenario_from_dict
    from edge_agent.decision.pipeline import DecisionPipeline
    from edge_agent.perception import PreprocessConfig, Preprocessor
    from edge_agent.perception.eye_state import EyeStateConfig, make_estimator
    from edge_agent.perception.features import FeatureConfig, FeatureExtractor
    from edge_agent.perception.landmarks import FaceLandmarkDetector, LandmarkConfig
    from edge_agent.perception.phone_detector import AsyncPhoneDetector, PhoneDetectorConfig, face_bbox, phone_near_face

    pre = Preprocessor(PreprocessConfig.from_dict(th.get("preprocess")))
    ext = FeatureExtractor(FeatureConfig.from_dict(th.get("features")))
    eye_state = make_estimator(EyeStateConfig.from_dict(th.get("eye_state")))
    phone_cfg = PhoneDetectorConfig.from_dict(th.get("phone"))
    pipeline = DecisionPipeline(th)
    can = CanSimulator(scenario_from_dict({"start_clock": "12:00", "timeline": [{"t": 0, "speed_kmh": 60}]}))
    ms = []
    t_start = time.perf_counter()
    with (
        FaceLandmarkDetector(LandmarkConfig.from_dict(th.get("landmarks"))) as lmd,
        AsyncPhoneDetector(phone_cfg, model=yolo_model) as phone,
    ):
        for i, img in enumerate(frames):
            t0 = time.perf_counter()
            now = time.monotonic()
            p = pre(Frame(img, i, now))
            lm = lmd.detect(p)
            phone.submit(p)
            res = phone.latest()
            flag = (
                None
                if res is None
                else phone_near_face(res.detections, face_bbox(lm.points) if lm else None, phone_cfg)
            )
            feats = ext(lm, i, now)
            if eye_state is not None:
                feats = eye_state(p, lm, feats)
            pipeline.step(feats, flag, can.sample(now - t_start))
            if i >= warmup:
                ms.append((time.perf_counter() - t0) * 1000.0)
        runs = phone.runs
    s = summarize(ms)
    s["yolo_runs_per_s"] = runs / (time.perf_counter() - t_start)
    return s


def run(args: argparse.Namespace) -> dict[str, Any]:
    import mediapipe

    from edge_agent.perception.onnx import load_ort

    ort = load_ort()

    from edge_agent.capture import Frame
    from edge_agent.context.can_sim import CanSimulator, scenario_from_dict
    from edge_agent.decision.pipeline import DecisionPipeline
    from edge_agent.perception import PreprocessConfig, Preprocessor
    from edge_agent.perception.eye_state import EyeStateConfig, EyeStateEstimator
    from edge_agent.perception.features import FeatureConfig, FeatureExtractor
    from edge_agent.perception.landmarks import FaceLandmarkDetector, LandmarkConfig
    from edge_agent.perception.phone_detector import PhoneDetectorConfig, YoloPhoneModel

    th = load_thresholds(args.config)
    frames, source_desc = load_frames(args.source, args.frames)
    phone_cfg = PhoneDetectorConfig.from_dict(th.get("phone"))
    models = PROJECT_ROOT / "models"
    fp32_path = phone_cfg.resolved_model_path()
    int8_path = models / "yolov8n_int8.onnx"
    if not int8_path.exists() or args.requantize:
        print(f"[benchmark] quantizing {fp32_path.name} -> {int8_path.name} ...", file=sys.stderr)
        quantize_yolo(fp32_path, int8_path, frames[: args.calib_frames], phone_cfg.input_size)

    w = args.warmup
    stages: dict[str, dict[str, float]] = {}
    pre = Preprocessor(PreprocessConfig.from_dict(th.get("preprocess")))
    ms, pre_frames = time_calls(lambda i: pre(Frame(frames[i], i, i / 30)), list(range(len(frames))), w)
    stages["2 preprocess"] = summarize(ms)
    with FaceLandmarkDetector(LandmarkConfig.from_dict(th.get("landmarks"))) as lmd:
        ms, lms = time_calls(lmd.detect, pre_frames, w)
    stages["3 face landmarks (MediaPipe)"] = summarize(ms)
    faces = sum(lm is not None for lm in lms)
    ext = FeatureExtractor(FeatureConfig.from_dict(th.get("features")))
    ms, feats = time_calls(lambda k: ext(lms[k], k, k / 30), list(range(len(lms))), w)
    stages["6 features (EAR, MAR, solvePnP)"] = summarize(ms)
    # Block 5 is normally called only on unreliable-EAR frames; time it on every frame with a face.
    eye_cfg = EyeStateConfig(**{**EyeStateConfig.from_dict(th.get("eye_state")).__dict__, "always_run": True})
    if eye_cfg.resolved_model_path().exists():
        eye = EyeStateEstimator(eye_cfg)
        with_face = [k for k, lm in enumerate(lms) if lm is not None]
        if with_face:
            ms, _ = time_calls(
                lambda k: eye.estimate(pre_frames[k], lms[k], feats[k]), with_face, min(w, len(with_face) // 2)
            )
            stages["5 eye-state CNN (when called)"] = summarize(ms)
    pipeline = DecisionPipeline(th)
    can = CanSimulator(scenario_from_dict({"start_clock": "12:00", "timeline": [{"t": 0, "speed_kmh": 60}]}))
    ms, _ = time_calls(lambda f: pipeline.step(f, False, can.sample(f.timestamp)), feats, w)
    stages["7-12 decision chain"] = summarize(ms)

    yolo = {}
    for name, path in (("FP32", fp32_path), ("INT8", int8_path)):
        cfg = PhoneDetectorConfig(**{**phone_cfg.__dict__, "model_path": str(path)})
        model = YoloPhoneModel(cfg)
        # Raw class scores too, to compare the two models beyond the NMS'd boxes.
        ms, dets = time_calls(lambda f, m=model: m(f.image), pre_frames, w)
        stages[f"4 YOLOv8n {name} ({phone_cfg.num_threads} threads)"] = summarize(ms)
        yolo[name] = {"model": model, "dets": dets}

    matched, only_fp32, only_int8 = agreement(yolo["FP32"]["dets"], yolo["INT8"]["dets"])
    loops = {
        "FP32": main_loop(frames, th, yolo["FP32"]["model"], w),
        "INT8": main_loop(frames, th, yolo["INT8"]["model"], w),
    }
    return {
        "system": {
            "cpu": platform.processor() or platform.machine(),
            "cores": os.cpu_count(),
            "os": f"{platform.system()} {platform.release()}",
            "python": platform.python_version(),
            "onnxruntime": ort.__version__,
            "opencv": cv2.__version__,
            "mediapipe": mediapipe.__version__,
        },
        "source": source_desc,
        "frames_with_face": faces,
        "frames": len(frames),
        "warmup": w,
        "stages": stages,
        "main_loop": loops,
        "models_mb": {
            "face_landmarker.task (float16)": file_mb(models / "face_landmarker.task"),
            "open_closed_eye.onnx (eye state, FP32)": file_mb(models / "open_closed_eye.onnx"),
            "yolov8n.onnx (FP32)": file_mb(fp32_path),
            "yolov8n_int8.onnx (INT8)": file_mb(int8_path),
        },
        "int8_vs_fp32": {"matched": matched, "only_fp32": only_fp32, "only_int8": only_int8},
    }


def report(r: dict[str, Any]) -> str:
    def f(v: float | None, d: int = 1) -> str:
        return "–" if v is None or v != v else f"{v:.{d}f}"

    sysinfo = r["system"]
    lines = [
        "# DriverGuard - speed benchmark",
        "",
        f"- Machine: {sysinfo['cpu']}, {sysinfo['cores']} logical cores, {sysinfo['os']}",
        f"- Software: Python {sysinfo['python']}, onnxruntime {sysinfo['onnxruntime']}, "
        f"OpenCV {sysinfo['opencv']}, MediaPipe {sysinfo['mediapipe']}",
        f"- Input: {r['source']}; face found in {r['frames_with_face']}/{r['frames']} frames; "
        f"first {r['warmup']} frames of each measurement are warm-up",
        "",
        "## Main loop (blocks 2-12, YOLO on its own thread)",
        "",
        f"| YOLO model | FPS | p50 ms | p95 ms | max ms | YOLO runs/s | ≥ {FPS_TARGET:g} FPS |",
        "|---|---:|---:|---:|---:|---:|:---:|",
    ]
    for name, s in r["main_loop"].items():
        ok = "✅" if s["fps"] >= FPS_TARGET else "❌"
        lines.append(
            f"| {name} | {f(s['fps'])} | {f(s['p50_ms'])} | {f(s['p95_ms'])} | {f(s['max_ms'])} | "
            f"{f(s['yolo_runs_per_s'])} | {ok} |"
        )
    lines += [
        "",
        "Frames are processed back to back (no camera pacing), so FPS is the loop's capacity; a 30 FPS "
        "camera leaves the difference as headroom.",
        "",
        "## Each block alone",
        "",
        "| Block | mean ms | p50 ms | p95 ms | max ms | FPS alone |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, s in r["stages"].items():
        lines.append(
            f"| {name} | {f(s['mean_ms'], 2)} | {f(s['p50_ms'], 2)} | {f(s['p95_ms'], 2)} | "
            f"{f(s['max_ms'], 2)} | {f(s['fps'], 0)} |"
        )
    agree = r["int8_vs_fp32"]
    lines += [
        "",
        "## Models",
        "",
        "| Model | Size (MB) |",
        "|---|---:|",
        *[f"| {k} | {f(v, 2)} |" for k, v in r["models_mb"].items()],
        "",
        f"INT8 vs FP32 phone detections on these frames: {agree['matched']} matched (IoU ≥ 0.5), "
        f"{agree['only_fp32']} only in FP32, {agree['only_int8']} only in INT8.",
    ]
    if agree["matched"] + agree["only_fp32"] + agree["only_int8"] == 0:
        lines.append(
            "No phone in these frames, so detection accuracy of INT8 is not measured here: "
            "run on a clip with a phone, and `tools/eval.py` with each model for precision / recall."
        )
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- long run (M42)

PROFILES_PATH = PROJECT_ROOT / "config" / "edge_profiles.yaml"


@dataclass
class Sample:
    t: float  # seconds since the run started
    fps: float  # frames finished in the last second
    p95_ms: float  # p95 frame latency of that second (NaN without a frame)
    cpu_pct: float  # this process, 100 = one core
    rss_mb: float
    temp_c: float | None
    threads: int


def parse_duration(text: str) -> float:
    """ "90s", "10m", "1.5h" or plain seconds -> seconds."""
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([smh]?)\s*", text)
    if m is None or float(m.group(1)) <= 0:
        raise ValueError(f"not a duration: {text!r} (examples: 90s, 10m, 1h)")
    return float(m.group(1)) * {"": 1, "s": 1, "m": 60, "h": 3600}[m.group(2)]


def load_profile(name: str, path: Path = PROFILES_PATH) -> dict[str, Any]:
    """One resource profile of config/edge_profiles.yaml: cpus, memory_mb, threads, note."""
    import yaml

    profiles = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if name not in profiles:
        raise KeyError(f"unknown profile {name!r} (in {path.name}: {', '.join(sorted(profiles))})")
    p = profiles[name]
    missing = [k for k in ("cpus", "memory_mb", "threads") if k not in p]
    if missing:
        raise KeyError(f"profile {name!r} lacks {missing}")
    return {**p, "name": name}


def cgroup_limits(root: Path = Path("/sys/fs/cgroup")) -> dict[str, float | None]:
    """CPU and memory limits this process runs under (Linux cgroup v2), None where there is none."""
    out: dict[str, float | None] = {"cpus": None, "memory_mb": None}
    try:
        quota, period = (root / "cpu.max").read_text().split()
        if quota != "max":
            out["cpus"] = int(quota) / int(period)
    except (OSError, ValueError):
        pass
    try:
        text = (root / "memory.max").read_text().strip()
        if text != "max":
            out["memory_mb"] = int(text) / (1 << 20)  # MiB, the unit of `docker run --memory 4096m`
    except (OSError, ValueError):
        pass
    return out


def read_temperature() -> float | None:
    """Hottest CPU / SoC sensor in deg C, None when the OS gives none (macOS, most containers)."""
    try:
        import psutil

        readings = [t.current for group in psutil.sensors_temperatures().values() for t in group]
        if readings:
            return float(max(readings))
    except (AttributeError, OSError, ImportError):
        pass
    try:
        zones = sorted(Path("/sys/class/thermal").glob("thermal_zone*/temp"))
        values = [int(z.read_text()) / 1000.0 for z in zones]
        return max(values) if values else None
    except (OSError, ValueError):
        return None


def per_minute(samples: list[Sample]) -> list[dict[str, float | None]]:
    """One row per minute of the run: FPS mean / min, worst p95 latency, CPU mean / max, memory, temperature."""
    rows = []
    for minute in sorted({int(s.t // 60) for s in samples}):
        part = [s for s in samples if int(s.t // 60) == minute]
        lat = [s.p95_ms for s in part if s.p95_ms == s.p95_ms]
        temps = [s.temp_c for s in part if s.temp_c is not None]
        rows.append(
            {
                "minute": minute,
                "seconds": len(part),
                "fps_mean": float(np.mean([s.fps for s in part])),
                "fps_min": float(min(s.fps for s in part)),
                "p95_ms": float(max(lat)) if lat else None,
                "cpu_mean": float(np.mean([s.cpu_pct for s in part])),
                "cpu_max": float(max(s.cpu_pct for s in part)),
                "rss_mb": float(part[-1].rss_mb),
                "temp_c": float(max(temps)) if temps else None,
            }
        )
    return rows


def rss_growth_mb_per_h(samples: list[Sample], skip_s: float = 60.0) -> float | None:
    """Slope of resident memory after the first `skip_s` (models loading, pools filling), by least
    squares, in MB per hour. None with less than a minute of samples after that."""
    pts = [(s.t, s.rss_mb) for s in samples if s.t >= skip_s]
    if len(pts) < 60:
        return None
    t, m = np.array(pts).T
    return float(np.polyfit(t, m, 1)[0] * 3600.0)


def soak_verdict(result: dict[str, Any], min_fps: float, max_growth: float) -> list[tuple[str, bool | None, str]]:
    """(criterion, passed or None when it cannot be judged, what was measured)."""
    minutes = [m for m in result["minutes"] if m["seconds"] >= 30]  # a short last minute says little
    lowest = min((m["fps_mean"] for m in minutes), default=None)
    growth = result["rss_growth_mb_per_h"]
    pace = result["pace_fps"]
    out = [
        (
            f"FPS at least {min_fps:g} in every minute",
            None if lowest is None else lowest >= min_fps,
            "–" if lowest is None else f"lowest minute {lowest:.1f} FPS" + (f" (paced at {pace:g})" if pace else ""),
        ),
        (
            f"memory grows less than {max_growth:g} MB / h",
            None if growth is None else growth < max_growth,
            "run too short to tell (needs 2 min)" if growth is None else f"{growth:+.1f} MB / h after the first minute",
        ),
    ]
    temps = [m["temp_c"] for m in result["minutes"] if m["temp_c"] is not None]
    out.append(
        ("temperature", None, f"highest {max(temps):.0f} °C" if temps else "not available on this system (not judged)")
    )
    return out


def check_failures(verdict: list[tuple[str, bool | None, str]]) -> list[str]:
    """--check: what a long run failed. FPS that could not be judged (a run under 30 s) fails too: a
    gate that measured nothing must not pass. Memory and temperature only fail when judged."""
    return [
        f"{name}: {measured}"
        for name, ok, measured in verdict
        if ok is False or (ok is None and name.startswith("FPS"))
    ]


def soak(args: argparse.Namespace, th: dict[str, Any]) -> dict[str, Any]:
    """The main loop (blocks 2-12, YOLO on its own thread) for args.duration seconds, sampled every second."""
    import mediapipe
    import psutil

    from edge_agent.capture import Frame
    from edge_agent.context.can_sim import CanSimulator, scenario_from_dict
    from edge_agent.decision.pipeline import DecisionPipeline
    from edge_agent.perception import PreprocessConfig, Preprocessor
    from edge_agent.perception.eye_state import EyeStateConfig, make_estimator
    from edge_agent.perception.features import FeatureConfig, FeatureExtractor
    from edge_agent.perception.landmarks import FaceLandmarkDetector, LandmarkConfig
    from edge_agent.perception.onnx import load_ort
    from edge_agent.perception.phone_detector import (
        AsyncPhoneDetector,
        FaceBoxMemory,
        PhoneDetectorConfig,
        face_bbox,
        phone_kind,
        phone_near_face,
    )

    profile = load_profile(args.profile) if args.profile else None
    phone_over = dict(th.get("phone") or {})
    if args.phone_model:
        phone_over["model_path"] = args.phone_model
    if profile is not None:
        phone_over["num_threads"] = int(profile["threads"])
        cv2.setNumThreads(int(profile["threads"]))
    phone_cfg = PhoneDetectorConfig.from_dict(phone_over)
    if args.condition == "drawn_face":
        from edge_agent.capture import CaptureConfig
        from tools.drawn_face import drawn_face_frames

        capture = CaptureConfig.from_dict(th.get("capture"))
        frames, source_desc = drawn_face_frames(args.frames, capture.camera_width, capture.camera_height)
    else:
        frames, source_desc = load_frames(args.source if args.condition != "no_face" else None, args.frames)
    pre = Preprocessor(PreprocessConfig.from_dict(th.get("preprocess")))
    ext = FeatureExtractor(FeatureConfig.from_dict(th.get("features")))
    eye_state = make_estimator(EyeStateConfig.from_dict(th.get("eye_state")))
    pipeline = DecisionPipeline(th)
    can = CanSimulator(scenario_from_dict({"start_clock": "12:00", "timeline": [{"t": 0, "speed_kmh": 60}]}))
    face_memory = FaceBoxMemory(phone_cfg.face_memory_s)
    proc = psutil.Process()
    proc.cpu_percent(None)  # the first call only sets the reference point
    period = 1.0 / args.pace_fps if args.pace_fps > 0 else 0.0
    samples: list[Sample] = []
    latencies: list[float] = []
    second: list[float] = []
    faces = n = 0
    start = time.monotonic()
    next_frame = next_sample = start
    with (
        FaceLandmarkDetector(LandmarkConfig.from_dict(th.get("landmarks"))) as lmd,
        AsyncPhoneDetector(phone_cfg) as phone,
    ):
        while True:
            now = time.monotonic()
            if now - start >= args.duration:
                break
            if period and now < next_frame:
                time.sleep(next_frame - now)
                now = time.monotonic()
            next_frame = max(next_frame + period, now) if period else now
            t0 = time.perf_counter()
            p = pre(Frame(frames[n % len(frames)], n, now))
            lm = lmd.detect(p)
            phone.submit(p)
            res = phone.latest()
            flag = held = None
            face = face_memory.update(face_bbox(lm.points) if lm else None, now)
            if res is not None:
                flag = phone_near_face(res.detections, face, phone_cfg)
                held = phone_kind(res.detections, face, phone_cfg)
            feats = ext(lm, n, now)
            if eye_state is not None:
                feats = eye_state(p, lm, feats)
            pipeline.step(feats, flag, can.sample(now - start), held)
            ms = (time.perf_counter() - t0) * 1000.0
            second.append(ms)
            latencies.append(ms)
            faces += lm is not None
            n += 1
            now = time.monotonic()
            if now >= next_sample + 1.0:
                span = now - next_sample
                samples.append(
                    Sample(
                        t=now - start,
                        fps=len(second) / span,
                        p95_ms=float(np.percentile(second, 95)) if second else float("nan"),
                        cpu_pct=proc.cpu_percent(None),
                        rss_mb=proc.memory_info().rss / 1e6,
                        temp_c=read_temperature(),
                        threads=proc.num_threads(),
                    )
                )
                second, next_sample = [], now
                if args.progress and len(samples) % 60 == 0:
                    s = samples[-1]
                    print(
                        f"[benchmark] {s.t / 60:.0f} min: {s.fps:.1f} FPS, CPU {s.cpu_pct:.0f} %, {s.rss_mb:.0f} MB",
                        file=sys.stderr,
                    )
        yolo_runs, stale = phone.runs, phone.stale_results
    elapsed = time.monotonic() - start
    ort = load_ort()
    return {
        "system": {
            "cpu": platform.processor() or platform.machine(),
            "cores": os.cpu_count(),
            "os": f"{platform.system()} {platform.release()}",
            "python": platform.python_version(),
            "onnxruntime": ort.__version__,
            "opencv": cv2.__version__,
            "mediapipe": mediapipe.__version__,
            "ram_gb": psutil.virtual_memory().total / 1e9,
        },
        "limits": cgroup_limits(),
        "profile": profile,
        "condition": args.condition,
        "label": args.label,
        "source": source_desc,
        "phone_model": Path(phone_cfg.model_path).name,
        "phone_threads": phone_cfg.num_threads,
        "pace_fps": args.pace_fps,
        "duration_s": elapsed,
        "frames": n,
        "frames_with_face": faces,
        "latency": summarize(latencies),
        "yolo_runs_per_s": yolo_runs / elapsed if elapsed > 0 else 0.0,
        "yolo_stale": stale,
        "cpu": {
            "mean": float(np.mean([s.cpu_pct for s in samples])) if samples else None,
            "p95": float(np.percentile([s.cpu_pct for s in samples], 95)) if samples else None,
            "max": float(max((s.cpu_pct for s in samples), default=0.0)) if samples else None,
        },
        "rss_mb": {
            "start": samples[0].rss_mb if samples else None,
            "end": samples[-1].rss_mb if samples else None,
            "max": max((s.rss_mb for s in samples), default=None),
        },
        "rss_growth_mb_per_h": rss_growth_mb_per_h(samples),
        "minutes": per_minute(samples),
        "samples": [asdict(s) for s in samples],
    }


def soak_report(r: dict[str, Any], min_fps: float, max_growth: float) -> str:
    def f(v: float | None, d: int = 1) -> str:
        return "–" if v is None or v != v else f"{v:.{d}f}"

    sysinfo, lim, profile = r["system"], r["limits"], r["profile"]
    simulated = profile is not None or lim["cpus"] is not None or lim["memory_mb"] is not None
    limits = (
        f"{f(lim['cpus'], 2)} CPUs, {f(lim['memory_mb'], 0)} MB (cgroup)"
        if simulated and (lim["cpus"] is not None or lim["memory_mb"] is not None)
        else "none seen by the process"
    )
    cores = lim["cpus"] or sysinfo["cores"]
    lines = [
        "# DriverGuard - long-run benchmark" + (" (`simulated`)" if simulated else ""),
        "",
        f"- Run: {r['label'] or 'unnamed'}; condition `{r['condition']}`; {r['duration_s'] / 60:.1f} min; "
        + (f"paced at {r['pace_fps']:g} FPS (a camera)" if r["pace_fps"] else "as fast as possible"),
        f"- Machine: {sysinfo['cpu']}, {sysinfo['cores']} logical cores, {sysinfo['ram_gb']:.0f} GB, {sysinfo['os']}",
        f"- Limits: {limits}"
        + (
            f"; profile `{profile['name']}` ({profile.get('note', '')}): asked {profile['cpus']} CPUs, "
            f"{profile['memory_mb']} MB, {profile['threads']} threads per model"
            if profile
            else ""
        ),
        f"- Software: Python {sysinfo['python']}, onnxruntime {sysinfo['onnxruntime']}, OpenCV {sysinfo['opencv']}, "
        f"MediaPipe {sysinfo['mediapipe']}; phone model {r['phone_model']} on {r['phone_threads']} threads",
        f"- Input: {r['source']}, looped from RAM; face found in {r['frames_with_face']}/{r['frames']} frames",
    ]
    if profile is not None and lim["cpus"] is None:
        lines.append(
            "- **The CPU limit of the profile was NOT applied** (no cgroup limit seen): only the thread counts were. "
            "Run it through tools/edge_sim.py."
        )
    lat = r["latency"]
    lines += [
        "",
        "## Whole run",
        "",
        "| FPS reached | Frame latency p50 / p95 / max (ms) | Capacity (1000 / mean ms) | CPU mean / p95 / max (% of one core) | "
        "CPU mean, share of the cores it may use | Memory start / end / peak (MB) | Memory growth (MB / h) | YOLO runs / s |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
        f"| {f(r['frames'] / r['duration_s'])} | {f(lat['p50_ms'])} / {f(lat['p95_ms'])} / {f(lat['max_ms'])} | "
        f"{f(lat['fps'])} FPS | {f(r['cpu']['mean'], 0)} / {f(r['cpu']['p95'], 0)} / {f(r['cpu']['max'], 0)} | "
        f"{f(r['cpu']['mean'] / cores if r['cpu']['mean'] is not None else None, 0)} % of {f(cores, 0 if cores == int(cores) else 2)} | "
        f"{f(r['rss_mb']['start'], 0)} / {f(r['rss_mb']['end'], 0)} / {f(r['rss_mb']['max'], 0)} | "
        f"{f(r['rss_growth_mb_per_h'])} | {f(r['yolo_runs_per_s'])} |",
        "",
        "| Criterion | Result | Measured |",
        "|---|:---:|---|",
    ]
    for name, ok, measured in soak_verdict(r, min_fps, max_growth):
        lines.append(f"| {name} | {'–' if ok is None else ('✅' if ok else '❌')} | {measured} |")
    if r["yolo_stale"]:
        lines.append("")
        lines.append(
            f"YOLO results older than `phone.max_result_age_s` when they arrived: {r['yolo_stale']} "
            "(they count as unknown: phone detection is weakened)."
        )
    lines += [
        "",
        "## Minute by minute",
        "",
        "| Minute | FPS mean | FPS lowest second | p95 latency, worst second (ms) | CPU mean (%) | CPU max (%) | Memory (MB) | Temperature (°C) |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for m in r["minutes"]:
        lines.append(
            f"| {m['minute'] + 1} | {f(m['fps_mean'])} | {f(m['fps_min'])} | {f(m['p95_ms'])} | {f(m['cpu_mean'], 0)} | "
            f"{f(m['cpu_max'], 0)} | {f(m['rss_mb'], 0)} | {f(m['temp_c'], 0)} |"
        )
    lines += [
        "",
        "CPU is this process only (MediaPipe, YOLO thread and the decision chain together), 100 % = one core. "
        "Frames are a short clip looped from RAM: no camera, no decoding, no HUD, no network.",
    ]
    if simulated:
        lines.append(
            "`simulated`: a container capped to the device's core count and memory on another machine. It does not "
            "reproduce the device's per-core speed, its GPU / TensorRT, or heat and throttling: an upper bound, not a "
            "measurement of the device."
        )
    return "\n".join(lines) + "\n"


def combine_report(results: list[dict[str, Any]], min_fps: float, max_growth: float) -> str:
    """Several long runs side by side (their --json files), then each run in full."""

    def f(v: float | None, d: int = 1) -> str:
        return "–" if v is None or v != v else f"{v:.{d}f}"

    lines = [
        "# DriverGuard - long-run benchmark: runs side by side",
        "",
        "Each row is one run of `tools/benchmark.py --duration` (the main loop, blocks 2-12, YOLO on its own "
        "thread, frames looped from RAM). Rows marked `simulated` ran in a container capped to a board's core count "
        "and memory on a development machine: an upper bound for that board, not a measurement of it (per-core "
        "speed, GPU / TensorRT and heat are not reproduced).",
        "",
        "| Run | Where | Limits | Phone model | Min | FPS reached | Capacity (FPS) | Latency p95 (ms) | CPU mean (% of one core) | "
        "Memory peak (MB) | Memory growth (MB / h) | FPS ≥ " + f"{min_fps:g}" + " every minute |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    for r in results:
        lim = r["limits"]
        capped = lim["cpus"] is not None or lim["memory_mb"] is not None
        where = "`simulated`" if capped or r["profile"] else "this machine"
        limits = f"{f(lim['cpus'], 0)} CPUs, {f(lim['memory_mb'], 0)} MB" if capped else "none"
        ok = soak_verdict(r, min_fps, max_growth)[0][1]
        lines.append(
            f"| {r['label'] or 'unnamed'} ({r['condition']}) | {where} | {limits} | {r['phone_model']} | "
            f"{r['duration_s'] / 60:.1f} | {f(r['frames'] / r['duration_s'])} | {f(r['latency']['fps'])} | "
            f"{f(r['latency']['p95_ms'])} | {f(r['cpu']['mean'], 0)} | {f(r['rss_mb']['max'], 0)} | "
            f"{f(r['rss_growth_mb_per_h'])} | {'–' if ok is None else ('✅' if ok else '❌')} |"
        )
    for r in results:
        body = (
            soak_report(r, min_fps, max_growth)
            .replace("\n## ", "\n### ")
            .replace("# DriverGuard - long-run benchmark", "## Run:", 1)
        )
        lines += ["", "---", "", body.rstrip("\n")]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", default=None, help="video file (or camera index) to benchmark on")
    p.add_argument("--frames", type=int, default=300, help="frames per measurement")
    p.add_argument("--warmup", type=int, default=20, help="first frames ignored in the statistics")
    p.add_argument("--calib-frames", type=int, default=64, help="frames used to calibrate INT8")
    p.add_argument("--requantize", action="store_true", help="rebuild models/yolov8n_int8.onnx")
    p.add_argument("--config", default=None, help="thresholds.yaml")
    p.add_argument("--out", default=None, help="write the markdown report here")
    p.add_argument("--json", default=None, help="write raw results as JSON here")
    p.add_argument("--duration", default=None, help="long run instead (M42): e.g. 90s, 10m, 1h")
    p.add_argument("--pace-fps", type=float, default=30.0, help="long run: frames per second fed (0 = flat out)")
    p.add_argument(
        "--condition",
        choices=("no_face", "face", "face_phone", "drawn_face"),
        default="face",
        help="long run: what the frames show (drawn_face: tools/drawn_face.py, no --source needed)",
    )
    p.add_argument("--check", action="store_true", help="long run: exit code 1 when a criterion fails")
    p.add_argument("--profile", default=None, help="long run: resource profile of config/edge_profiles.yaml")
    p.add_argument("--phone-model", default=None, help="long run: ONNX to use, e.g. models/yolov8n_int8.onnx")
    p.add_argument("--label", default=None, help="long run: name of the run in the report (machine, setup)")
    p.add_argument("--csv", default=None, help="long run: write the per-second samples here")
    p.add_argument("--progress", action="store_true", help="long run: one line per minute on stderr")
    p.add_argument("--combine", nargs="+", default=None, help="--json files of long runs: one report of them all")
    if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp1252: the report has ≥, ±
        sys.stdout.reconfigure(encoding="utf-8")
    args = p.parse_args(argv)
    if args.frames <= args.warmup:
        p.error("--frames must be larger than --warmup")
    if args.combine:
        from tools.metrics import EvalConfig

        cfg = EvalConfig.from_dict(load_thresholds(args.config).get("eval"))
        results = [json.loads(Path(x).read_text(encoding="utf-8")) for x in args.combine]
        text = combine_report(results, cfg.soak_min_fps, cfg.soak_rss_growth_mb_per_h)
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
        print(text)
        return 0
    if args.duration is not None:
        from tools.metrics import EvalConfig

        th = load_thresholds(args.config)
        cfg = EvalConfig.from_dict(th.get("eval"))
        try:
            args.duration = parse_duration(args.duration)
        except ValueError as e:
            p.error(str(e))
        result = soak(args, th)
        text = soak_report(result, cfg.soak_min_fps, cfg.soak_rss_growth_mb_per_h)
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(text, encoding="utf-8")
        print(text)
        if args.csv:
            rows = ["t_s,fps,p95_ms,cpu_pct,rss_mb,temp_c,threads"]
            rows += [
                f"{s['t']:.1f},{s['fps']:.2f},{s['p95_ms']:.2f},{s['cpu_pct']:.1f},{s['rss_mb']:.1f},"
                f"{'' if s['temp_c'] is None else s['temp_c']},{s['threads']}"
                for s in result["samples"]
            ]
            Path(args.csv).write_text("\n".join(rows) + "\n", encoding="utf-8")
        if args.json:
            Path(args.json).write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
        if args.check:
            failed = check_failures(soak_verdict(result, cfg.soak_min_fps, cfg.soak_rss_growth_mb_per_h))
            for line in failed:
                print(f"[benchmark] FAILED {line}", file=sys.stderr)
            return 1 if failed else 0
        return 0

    result = run(args)
    text = report(result)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
