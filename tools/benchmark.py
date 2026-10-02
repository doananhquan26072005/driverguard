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
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from collections.abc import Callable
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
    if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp1252: the report has ≥, ±
        sys.stdout.reconfigure(encoding="utf-8")
    args = p.parse_args(argv)
    if args.frames <= args.warmup:
        p.error("--frames must be larger than --warmup")

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
