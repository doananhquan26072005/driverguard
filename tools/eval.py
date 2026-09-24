"""M7 - Accuracy evaluation: system events vs dataset labels.

Per behaviour: precision, recall, F1, detection delay and false positives per hour of
driving; plus the same for every emitted alert (any level, any reason).

Labels: CSV with a header `video,behavior,start_s,end_s` (one row per labelled episode).
  behaviour = microsleep | yawn | nod | drowsy | phone | off_road
  A row with behavior `none` just lists a video without any episode (a negative clip),
  so its driving time counts in false positives per hour.

    # 1. run the full pipeline (blocks 2-12) on every labelled video, then score
    python tools/eval.py run --labels labels.csv --videos data/videos --save predictions.json
    python tools/eval.py run --labels labels.csv --videos data/videos --phone-model models/yolov8n_int8.onnx
    # 2. re-score saved predictions (e.g. with another tolerance) without re-running videos
    python tools/eval.py score --labels labels.csv --predictions predictions.json
    # 3. per-frame labels (e.g. NTHU-DDD "0001100..." strings) -> label rows
    python tools/eval.py convert-frames --frames 001_mouth.txt --video 001.mp4 --fps 30 --map 1=yawn >> labels.csv

Matching (per video and behaviour): a prediction is a true positive when its time falls in a
labelled episode widened by --tolerance seconds on both sides; each episode is matched once,
further predictions inside it are duplicates (neither TP nor FP); a prediction outside every
episode is a false positive. Videos are read frame by frame (no frame is dropped) and time is
frame_index / fps, so results are reproducible. Frames stay in RAM, nothing is written but metrics.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BEHAVIORS = ("microsleep", "yawn", "nod", "drowsy", "phone", "off_road")
ALERT = "alert"  # every emitted alert, whatever its reason
REASON_TO_BEHAVIOR = {"phone": "phone", "off_road": "off_road", "drowsy_score": "drowsy", "trend": "drowsy"}
EVENT_TO_BEHAVIOR = {"microsleep": "microsleep", "yawn": "yawn", "nod": "nod", "perclos_high": "drowsy"}


@dataclass(frozen=True)
class Episode:
    video: str
    behavior: str
    start_s: float
    end_s: float


@dataclass(frozen=True)
class Prediction:
    video: str
    behavior: str
    time_s: float
    level: int = 0


@dataclass
class Score:
    behavior: str
    episodes: int
    predictions: int
    tp: int
    fp: int
    duplicates: int
    precision: float | None
    recall: float | None
    f1: float | None
    fp_per_hour: float | None
    delay_p50_s: float | None


# --------------------------------------------------------------------------- label / prediction files


def read_labels(path: str | Path) -> tuple[list[Episode], list[str]]:
    """Episodes and the ordered list of videos mentioned in the label file."""
    episodes, videos = [], []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            video = row["video"].strip()
            if video not in videos:
                videos.append(video)
            behavior = row["behavior"].strip()
            if behavior == "none":
                continue
            if behavior not in BEHAVIORS:
                raise ValueError(f"unknown behavior {behavior!r} in {path} (expected one of {BEHAVIORS})")
            start, end = float(row["start_s"]), float(row["end_s"])
            if end < start:
                raise ValueError(f"end before start for {video} {behavior} {start}-{end}")
            episodes.append(Episode(video, behavior, start, end))
    return episodes, videos


def frames_to_episodes(
    values: str, fps: float, mapping: dict[str, str], video: str, min_s: float = 0.0
) -> list[Episode]:
    """Per-frame label string ("000111100022") -> episodes of consecutive frames with the same mapped value."""
    digits = "".join(ch for ch in values if not ch.isspace())
    episodes: list[Episode] = []
    start = 0
    for i in range(1, len(digits) + 1):
        if i < len(digits) and digits[i] == digits[start]:
            continue
        behavior = mapping.get(digits[start])
        if behavior is not None and (i - start) / fps >= min_s:
            episodes.append(Episode(video, behavior, round(start / fps, 3), round(i / fps, 3)))
        start = i
    return episodes


def save_predictions(path: str | Path, predictions: list[Prediction], durations: dict[str, float]) -> None:
    data = {"durations_s": durations, "predictions": [asdict(p) for p in predictions]}
    Path(path).write_text(json.dumps(data, indent=1), encoding="utf-8")


def load_predictions(path: str | Path) -> tuple[list[Prediction], dict[str, float]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Prediction(**p) for p in data["predictions"]], {k: float(v) for k, v in data["durations_s"].items()}


# --------------------------------------------------------------------------- scoring (pure)


def _ratio(num: int, den: int) -> float | None:
    return num / den if den else None


def match(episodes: list[Episode], times: Iterable[float], tolerance_s: float) -> tuple[int, int, int, list[float]]:
    """(tp, fp, duplicates, delays) for one video and behaviour."""
    windows = sorted((e.start_s - tolerance_s, e.end_s + tolerance_s, e.start_s) for e in episodes)
    matched = [False] * len(windows)
    tp = fp = dup = 0
    delays: list[float] = []
    for t in sorted(times):
        hit = next((i for i, (lo, hi, _) in enumerate(windows) if lo <= t <= hi), None)
        if hit is None:
            fp += 1
        elif matched[hit]:
            dup += 1
        else:
            matched[hit] = True
            tp += 1
            delays.append(t - windows[hit][2])
    return tp, fp, dup, delays


def score(
    episodes: list[Episode],
    predictions: list[Prediction],
    durations_s: dict[str, float],
    tolerance_s: float = 1.0,
) -> list[Score]:
    """One Score per behaviour, plus ALERT (every alert vs every labelled episode)."""
    videos = list(durations_s)
    hours = sum(durations_s.values()) / 3600.0
    rows = []
    for behavior in (*BEHAVIORS, ALERT):
        tp = fp = dup = n_eps = n_pred = 0
        delays: list[float] = []
        for video in videos:
            if behavior == ALERT:  # an alert is right if it overlaps any labelled behaviour
                eps = [e for e in episodes if e.video == video]
            else:
                eps = [e for e in episodes if e.video == video and e.behavior == behavior]
            times = [p.time_s for p in predictions if p.video == video and p.behavior == behavior]
            t, f, d, dl = match(eps, times, tolerance_s)
            tp, fp, dup, n_eps, n_pred = tp + t, fp + f, dup + d, n_eps + len(eps), n_pred + len(times)
            delays += dl
        precision = _ratio(tp, tp + fp)
        recall = _ratio(tp, n_eps)
        f1 = 2 * precision * recall / (precision + recall) if precision and recall else (0.0 if n_eps else None)
        rows.append(
            Score(
                behavior=behavior,
                episodes=n_eps,
                predictions=n_pred,
                tp=tp,
                fp=fp,
                duplicates=dup,
                precision=precision,
                recall=recall if behavior != ALERT else None,  # alerts are not meant to cover every label
                f1=f1 if behavior != ALERT else None,
                fp_per_hour=fp / hours if hours > 0 else None,
                delay_p50_s=statistics.median(delays) if delays else None,
            )
        )
    return rows


def _fmt(v: float | None, pct: bool = False, digits: int = 2) -> str:
    if v is None:
        return "–"
    return f"{v * 100:.1f}%" if pct else f"{v:.{digits}f}"


def report(scores: list[Score], durations_s: dict[str, float], tolerance_s: float) -> str:
    hours = sum(durations_s.values()) / 3600.0
    lines = [
        "# DriverGuard - accuracy evaluation",
        "",
        f"{len(durations_s)} videos, {hours * 60:.1f} min of driving, match tolerance ±{tolerance_s:g} s.",
        "",
        "| Behaviour | Episodes | Predictions | TP | FP | Dup | Precision | Recall | F1 | FP / hour | Delay p50 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for s in scores:
        name = "**all alerts**" if s.behavior == ALERT else s.behavior
        lines.append(
            f"| {name} | {s.episodes} | {s.predictions} | {s.tp} | {s.fp} | {s.duplicates} | "
            f"{_fmt(s.precision, True)} | {_fmt(s.recall, True)} | {_fmt(s.f1)} | "
            f"{_fmt(s.fp_per_hour, digits=1)} | {_fmt(s.delay_p50_s, digits=1)} s |"
        )
    lines += [
        "",
        "TP / FP / Dup: matched episodes / predictions outside every episode / extra predictions in an "
        "already matched episode. Delay: prediction time minus episode start (negative = inside the "
        "tolerance before the labelled start). *all alerts*: every emitted alert (L1-L3) scored against "
        "every labelled episode, whatever its behaviour; recall is not meaningful there.",
    ]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- running the system on videos


def predictions_from_result(video: str, t: float, r: Any) -> list[Prediction]:
    """Detections of one frame's DecisionResult."""
    out = [Prediction(video, EVENT_TO_BEHAVIOR[ev], t) for ev in r.drowsiness.events if ev in EVENT_TO_BEHAVIOR]
    alert = r.alert.new_alert
    if alert is not None:
        out.append(Prediction(video, ALERT, t, alert.level))
        for behavior in {REASON_TO_BEHAVIOR[x] for x in alert.reasons if x in REASON_TO_BEHAVIOR}:
            out.append(Prediction(video, behavior, t, alert.level))
    return out


def run_video(
    path: Path, thresholds: dict[str, Any], speed_kmh: float, use_phone: bool
) -> tuple[list[Prediction], float]:
    import cv2

    from edge_agent.capture import Frame
    from edge_agent.context.can_sim import CanSimulator, scenario_from_dict
    from edge_agent.decision.pipeline import DecisionPipeline
    from edge_agent.perception import PreprocessConfig, Preprocessor
    from edge_agent.perception.eye_state import EyeStateConfig, make_estimator
    from edge_agent.perception.features import FeatureConfig, FeatureExtractor
    from edge_agent.perception.landmarks import FaceLandmarkDetector, LandmarkConfig
    from edge_agent.perception.phone_detector import (
        FaceBoxMemory,
        PhoneDetectorConfig,
        YoloPhoneModel,
        face_bbox,
        phone_near_face,
    )

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {path}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    fps = fps if 0 < fps < 1000 else 30.0
    preprocessor = Preprocessor(PreprocessConfig.from_dict(thresholds.get("preprocess")))
    extractor = FeatureExtractor(FeatureConfig.from_dict(thresholds.get("features")))
    eye_state = make_estimator(EyeStateConfig.from_dict(thresholds.get("eye_state")))
    phone_cfg = PhoneDetectorConfig.from_dict(thresholds.get("phone"))
    yolo = YoloPhoneModel(phone_cfg) if use_phone else None
    yolo_every = max(1, round(fps / phone_cfg.target_fps))  # same rate as the runtime thread
    pipeline = DecisionPipeline(thresholds)
    can = CanSimulator(scenario_from_dict({"start_clock": "12:00", "timeline": [{"t": 0, "speed_kmh": speed_kmh}]}))
    preds: list[Prediction] = []
    detections: tuple = ()
    last_yolo_t = -1e9
    face_memory = FaceBoxMemory(phone_cfg.face_memory_s)
    i = 0
    with FaceLandmarkDetector(LandmarkConfig.from_dict(thresholds.get("landmarks"))) as landmarks:
        while True:
            ok, image = cap.read()
            if not ok:
                break
            t = i / fps
            pre = preprocessor(Frame(image=image, frame_id=i, timestamp=t))
            lm = landmarks.detect(pre)
            if yolo is not None and i % yolo_every == 0:
                detections, last_yolo_t = yolo(pre.image), t
            phone_flag = None
            face = face_memory.update(face_bbox(lm.points) if lm else None, t)
            if yolo is not None and t - last_yolo_t <= phone_cfg.max_result_age_s:
                phone_flag = phone_near_face(detections, face, phone_cfg)
            feats = extractor(lm, i, t)
            if eye_state is not None:
                feats = eye_state(pre, lm, feats)
            r = pipeline.step(feats, phone_flag, can.sample(t))
            preds += predictions_from_result(path.name, t, r)
            i += 1
    cap.release()
    return preds, i / fps


# --------------------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="run the pipeline on the labelled videos and score")
    run.add_argument("--labels", required=True)
    run.add_argument("--videos", required=True, help="directory with the video files named in the labels")
    run.add_argument("--config", default=None, help="thresholds.yaml to evaluate (default: config/thresholds.yaml)")
    run.add_argument("--speed", type=float, default=60.0, help="simulated vehicle speed, km/h (default 60)")
    run.add_argument("--no-phone", action="store_true", help="skip YOLO (faster; phone gets no predictions)")
    run.add_argument("--phone-model", default=None, help="ONNX to use instead, e.g. models/yolov8n_int8.onnx")
    run.add_argument("--save", default=None, help="write predictions JSON (re-score later with `score`)")
    sc = sub.add_parser("score", help="score saved predictions")
    sc.add_argument("--labels", required=True)
    sc.add_argument("--predictions", required=True)
    for s in (run, sc):
        s.add_argument("--tolerance", type=float, default=1.0, help="seconds added on both sides of each episode")
        s.add_argument("--out", default=None, help="also write the markdown report here")
        s.add_argument("--json", default=None, help="also write the scores as JSON here")
    cf = sub.add_parser("convert-frames", help="per-frame label string -> label CSV rows (stdout)")
    cf.add_argument("--frames", required=True, help="text file with one label digit per frame")
    cf.add_argument("--video", required=True, help="video file name to put in the rows")
    cf.add_argument("--fps", type=float, required=True)
    cf.add_argument("--map", action="append", required=True, help="DIGIT=behavior, e.g. 1=yawn (repeatable)")
    cf.add_argument("--min-s", type=float, default=0.0, help="drop episodes shorter than this")
    cf.add_argument("--header", action="store_true", help="print the CSV header first")
    if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp1252: the report has ≥, ±
        sys.stdout.reconfigure(encoding="utf-8")
    args = p.parse_args(argv)

    if args.cmd == "convert-frames":
        mapping = dict(m.split("=", 1) for m in args.map)
        bad = set(mapping.values()) - set(BEHAVIORS)
        if bad:
            p.error(f"unknown behaviors {bad}")
        values = Path(args.frames).read_text(encoding="utf-8")
        w = csv.writer(sys.stdout, lineterminator="\n")
        if args.header:
            w.writerow(["video", "behavior", "start_s", "end_s"])
        episodes = frames_to_episodes(values, args.fps, mapping, args.video, args.min_s)
        for e in episodes:
            w.writerow([e.video, e.behavior, e.start_s, e.end_s])
        return 0

    episodes, videos = read_labels(args.labels)
    if args.cmd == "score":
        predictions, durations = load_predictions(args.predictions)
        missing = [v for v in videos if v not in durations]
        if missing:
            p.error(f"no predictions for {missing}: run them first")
        durations = {v: durations[v] for v in videos}
    else:
        from edge_agent.config import load_thresholds

        thresholds = load_thresholds(args.config)
        if args.phone_model:  # compare FP32 / INT8 accuracy on the same labels
            thresholds.setdefault("phone", {})["model_path"] = args.phone_model
        predictions, durations = [], {}
        for video in videos:
            t0 = time.perf_counter()
            preds, dur = run_video(Path(args.videos) / video, thresholds, args.speed, not args.no_phone)
            predictions += preds
            durations[video] = dur
            print(
                f"[eval] {video}: {dur:.0f} s, {len(preds)} detections, {time.perf_counter() - t0:.0f} s",
                file=sys.stderr,
            )
        if args.save:
            save_predictions(args.save, predictions, durations)

    scores = score(episodes, predictions, durations, args.tolerance)
    text = report(scores, durations, args.tolerance)
    print(text)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    if args.json:
        Path(args.json).write_text(json.dumps([asdict(s) for s in scores], indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
