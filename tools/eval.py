"""M7 - Accuracy evaluation: system events vs dataset labels.

Per behaviour: precision, recall, F1, detection delay and false positives per hour; plus the
same for every emitted alert (any reason), in total and per level. False positives per hour are
divided by the hours where one can happen (the video time minus the episodes the predictions are
matched against, widened by the tolerance) and printed with those hours and an exact Poisson
95 % CI (tools/metrics.py). With per-second risk levels (recorded by `run`), FAR / MAR on fixed
windows are added, drowsiness and distraction apart (config/thresholds.yaml, section `eval`).

Labels: CSV with a header `video,behavior,start_s,end_s` (one row per labelled episode).
  behaviour = microsleep | yawn | nod | drowsy | phone | off_road
  A row with behavior `none` just lists a video without any episode (a negative clip),
  so its driving time counts in false positives per hour.
  Optional column `subject` (M40): who is in the video. With it the report adds a table per
  person: an average over all videos can hide one group of people who get most of the false
  alarms. A video without a subject is its own person.

False positives of the start-up stretch (the first `eval.warmup_s` of every video, before the
baselines and the PERCLOS window fill up) are also reported apart from the rest (M40).

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

from tools.metrics import (  # noqa: E402
    DISTRACTION_REASONS,
    DROWSY_REASONS,
    EvalConfig,
    WindowCounts,
    branch_level,
    ci_text,
    exposure_seconds,
    rate_ci,
    widen,
    window_scores,
    window_table,
)

BEHAVIORS = ("microsleep", "yawn", "nod", "drowsy", "phone", "off_road")
ALERT = "alert"  # every emitted alert, whatever its reason
REASON_TO_BEHAVIOR = {"phone": "phone", "off_road": "off_road", "drowsy_score": "drowsy", "trend": "drowsy"}
EVENT_TO_BEHAVIOR = {"microsleep": "microsleep", "yawn": "yawn", "nod": "nod", "perclos_high": "drowsy"}
# Labelled behaviours that make a FAR / MAR window drowsy / distracted.
DROWSY_BEHAVIORS = ("microsleep", "drowsy", "nod", "yawn")
DISTRACTION_BEHAVIORS = ("phone", "off_road")
BRANCHES = ("drowsy", "distraction")  # per-second level series recorded by run_video


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
    exposure_h: float = 0.0  # hours where a false positive of this row can happen
    fp_ci_low: float | None = None  # exact Poisson 95 % CI of fp_per_hour
    fp_ci_high: float | None = None
    fp_warmup: int = 0  # of fp: in the start-up stretch of a video (score(warmup_s=...))
    warmup_h: float = 0.0  # of exposure_h: in the start-up stretches


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


def read_subjects(path: str | Path) -> dict[str, str]:
    """video -> subject, from the optional `subject` column ({} when the file has none)."""
    out: dict[str, str] = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            subject = (row.get("subject") or "").strip()
            if subject:
                out[row["video"].strip()] = subject
    return out


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


Levels = dict[str, dict[str, list[int]]]  # video -> branch -> highest risk level of each second


def save_predictions(
    path: str | Path, predictions: list[Prediction], durations: dict[str, float], levels: Levels | None = None
) -> None:
    data = {"durations_s": durations, "predictions": [asdict(p) for p in predictions], "levels": levels or {}}
    Path(path).write_text(json.dumps(data), encoding="utf-8")


def load_predictions(path: str | Path) -> tuple[list[Prediction], dict[str, float], Levels]:
    """Predictions, durations and per-second levels (empty for files saved before they existed)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    durations = {k: float(v) for k, v in data["durations_s"].items()}
    return [Prediction(**p) for p in data["predictions"]], durations, data.get("levels", {})


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
    warmup_s: float = 0.0,
) -> list[Score]:
    """One Score per behaviour, plus ALERT (every alert vs every labelled episode) in total and per level.

    A row's false positives per hour are over the time where one can happen: each video's duration
    minus the episodes that row is matched against, widened by the tolerance. warmup_s > 0 also
    counts the false positives and the exposure of the first warmup_s of every video (fp_warmup,
    warmup_h), so the start-up stretch can be reported apart.
    """
    videos = list(durations_s)
    rows = []
    for name, behavior, level in (
        [(b, b, None) for b in BEHAVIORS] + [(ALERT, ALERT, None)] + [(f"{ALERT} L{lv}", ALERT, lv) for lv in (1, 2, 3)]
    ):
        tp = fp = dup = n_eps = n_pred = fp_warm = 0
        exposure_s = warm_s = 0.0
        delays: list[float] = []
        for video in videos:
            if behavior == ALERT:  # an alert is right if it overlaps any labelled behaviour
                eps = [e for e in episodes if e.video == video]
            else:
                eps = [e for e in episodes if e.video == video and e.behavior == behavior]
            times = [
                p.time_s
                for p in predictions
                if p.video == video and p.behavior == behavior and (level is None or p.level == level)
            ]
            t, f, d, dl = match(eps, times, tolerance_s)
            tp, fp, dup, n_eps, n_pred = tp + t, fp + f, dup + d, n_eps + len(eps), n_pred + len(times)
            wide = widen([(e.start_s, e.end_s) for e in eps], tolerance_s)
            exposure_s += exposure_seconds(durations_s[video], wide)
            if warmup_s > 0:
                warm_s += exposure_seconds(min(durations_s[video], warmup_s), wide)
                fp_warm += sum(1 for x in times if x < warmup_s and not any(lo <= x <= hi for lo, hi in wide))
            delays += dl
        hours = exposure_s / 3600.0
        rate, lo, hi = rate_ci(fp, hours)
        precision = _ratio(tp, tp + fp)
        recall = _ratio(tp, n_eps)
        f1 = 2 * precision * recall / (precision + recall) if precision and recall else (0.0 if n_eps else None)
        rows.append(
            Score(
                behavior=name,
                episodes=n_eps,
                predictions=n_pred,
                tp=tp,
                fp=fp,
                duplicates=dup,
                precision=precision,
                recall=recall if behavior != ALERT else None,  # alerts are not meant to cover every label
                f1=f1 if behavior != ALERT else None,
                fp_per_hour=rate,
                delay_p50_s=statistics.median(delays) if delays else None,
                exposure_h=hours,
                fp_ci_low=lo,
                fp_ci_high=hi,
                fp_warmup=fp_warm,
                warmup_h=warm_s / 3600.0,
            )
        )
    return rows


def warmup_table(scores: list[Score], warmup_s: float) -> list[str]:
    """False positives of the start-up stretch apart from the rest (rows that have any exposure)."""
    lines = [
        f"| Row | FP in the first {warmup_s:g} s | Hours | FP / hour (95% CI) | FP after | Hours | FP / hour (95% CI) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for s in scores:
        after, after_h = s.fp - s.fp_warmup, s.exposure_h - s.warmup_h
        lines.append(
            f"| {s.behavior.replace(ALERT, 'all alerts')} | {s.fp_warmup} | {s.warmup_h:.2f} | "
            f"{ci_text(rate_ci(s.fp_warmup, s.warmup_h))} | {after} | {after_h:.2f} | {ci_text(rate_ci(after, after_h))} |"
        )
    return lines


@dataclass
class SubjectRow:
    subject: str
    videos: int
    hours: float  # where a false alert can happen
    alerts: int
    false_alerts: int
    fp_per_hour: float | None
    fp_ci_low: float | None
    fp_ci_high: float | None
    episodes: int  # labelled episodes of any behaviour
    caught: int  # of them answered by an alert
    false_by: dict[str, int]  # behaviour -> false positives (which rule disturbs this person)
    windows: WindowCounts | None = None  # drowsiness FAR / MAR windows at eval.min_level


def score_by_subject(
    episodes: list[Episode],
    predictions: list[Prediction],
    durations_s: dict[str, float],
    subjects: dict[str, str],
    tolerance_s: float = 1.0,
    levels: Levels | None = None,
    cfg: EvalConfig | None = None,
) -> list[SubjectRow]:
    """One row per person (a video without a subject is its own person), worst false-alert rate first."""
    groups: dict[str, list[str]] = {}
    for video in durations_s:
        groups.setdefault(subjects.get(video, video), []).append(video)
    rows = []
    for subject, videos in groups.items():
        durs = {v: durations_s[v] for v in videos}
        by_name = {s.behavior: s for s in score(episodes, predictions, durs, tolerance_s)}
        alert = by_name[ALERT]
        windows = None
        if levels and cfg is not None:
            lv = {v: levels[v] for v in videos if v in levels}
            windows = dict(window_rows(episodes, durs, lv, cfg, tolerance_s))[f"Drowsiness, level ≥ L{cfg.min_level}"]
        rows.append(
            SubjectRow(
                subject=subject,
                videos=len(videos),
                hours=alert.exposure_h,
                alerts=alert.predictions,
                false_alerts=alert.fp,
                fp_per_hour=alert.fp_per_hour,
                fp_ci_low=alert.fp_ci_low,
                fp_ci_high=alert.fp_ci_high,
                episodes=alert.episodes,
                caught=alert.tp,
                false_by={b: by_name[b].fp for b in BEHAVIORS if by_name[b].fp},
                windows=windows,
            )
        )
    return sorted(rows, key=lambda r: (-(r.fp_per_hour or 0.0), -r.false_alerts, r.subject))


def subject_report(rows: list[SubjectRow], worst: int = 5) -> list[str]:
    """Distribution over people, then the worst few. Per-person rates are on minutes of video: the
    CI is the honest part, so nobody is called pass / fail here."""
    if not rows:
        return []
    rates = sorted(r.fp_per_hour for r in rows if r.fp_per_hour is not None)
    with_false = sum(1 for r in rows if r.false_alerts)
    total_false = sum(r.false_alerts for r in rows)
    top = sorted(rows, key=lambda r: -r.false_alerts)[: max(1, len(rows) // 10)]
    lines = [
        f"{len(rows)} people. False alerts: {total_false} in all, from {with_false} of them "
        f"({_fmt(_ratio(with_false, len(rows)), True)}); the {len(top)} with the most have "
        f"{sum(r.false_alerts for r in top)} ({_fmt(_ratio(sum(r.false_alerts for r in top), total_false), True)}).",
    ]
    if rates:
        q = lambda f: rates[min(len(rates) - 1, int(f * (len(rates) - 1) + 0.5))]  # noqa: E731
        lines.append(
            f"False alerts per hour across people: median {q(0.5):.1f}, p90 {q(0.9):.1f}, highest {rates[-1]:.1f}. "
            "One person has minutes of video, so a single person's rate has a very wide CI: compare groups, "
            "not individuals."
        )
    lines += [
        "",
        f"The {min(worst, len(rows))} people with the highest false-alert rate:",
        "",
        "| Person | Videos | Hours | Alerts | False | False / hour (95% CI) | Episodes answered | False by behaviour | FAR windows |",
        "|---|---:|---:|---:|---:|---:|---:|---|---:|",
    ]
    for r in rows[:worst]:
        far = "–" if r.windows is None or not r.windows.awake else f"{r.windows.false_alarms}/{r.windows.awake}"
        lines.append(
            f"| {r.subject} | {r.videos} | {r.hours:.2f} | {r.alerts} | {r.false_alerts} | "
            f"{ci_text((r.fp_per_hour, r.fp_ci_low, r.fp_ci_high))} | {r.caught}/{r.episodes} | "
            f"{', '.join(f'{b} {n}' for b, n in sorted(r.false_by.items())) or '–'} | {far} |"
        )
    return lines


def window_rows(
    episodes: list[Episode], durations_s: dict[str, float], levels: Levels, cfg: EvalConfig, tolerance_s: float = 1.0
) -> list[tuple[str, WindowCounts]]:
    """FAR / MAR window counts, drowsiness and distraction apart, at cfg.min_level and at L2.

    Unlabelled time counts as awake (the label file lists every episode of its videos), as for
    false positives per hour. Videos without recorded levels are left out.
    """
    rows = []
    for branch, behaviors in (("drowsy", DROWSY_BEHAVIORS), ("distraction", DISTRACTION_BEHAVIORS)):
        for lv in sorted({cfg.min_level, 2}):
            total = WindowCounts()
            for video, dur in durations_s.items():
                series = levels.get(video, {}).get(branch)
                if series is None:
                    continue
                pos = [(e.start_s, e.end_s) for e in episodes if e.video == video and e.behavior in behaviors]
                level_cfg = EvalConfig(cfg.window_s, cfg.warmup_s, cfg.positive_frac, lv)
                total += window_scores(dur, pos, [(0.0, dur)], series, level_cfg, tolerance_s)
            name = "Drowsiness" if branch == "drowsy" else "Distraction"
            rows.append((f"{name}, level ≥ L{lv}", total))
    return rows


def _fmt(v: float | None, pct: bool = False, digits: int = 2) -> str:
    if v is None:
        return "–"
    return f"{v * 100:.1f}%" if pct else f"{v:.{digits}f}"


def report(
    scores: list[Score],
    durations_s: dict[str, float],
    tolerance_s: float,
    windows: list[tuple[str, WindowCounts]] | None = None,
    cfg: EvalConfig | None = None,
    by_subject: list[SubjectRow] | None = None,
) -> str:
    hours = sum(durations_s.values()) / 3600.0
    lines = [
        "# DriverGuard - accuracy evaluation",
        "",
        f"{len(durations_s)} videos, {hours * 60:.1f} min of driving, match tolerance ±{tolerance_s:g} s.",
        "",
        "## Events and alerts",
        "",
        "| Behaviour | Episodes | Predictions | TP | FP | Dup | Precision | Recall | F1 | Hours | FP / hour (95% CI) | Delay p50 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for s in scores:
        name = f"**{s.behavior.replace(ALERT, 'all alerts')}**" if s.behavior.startswith(ALERT) else s.behavior
        lines.append(
            f"| {name} | {s.episodes} | {s.predictions} | {s.tp} | {s.fp} | {s.duplicates} | "
            f"{_fmt(s.precision, True)} | {_fmt(s.recall, True)} | {_fmt(s.f1)} | {s.exposure_h:.2f} | "
            f"{ci_text((s.fp_per_hour, s.fp_ci_low, s.fp_ci_high))} | {_fmt(s.delay_p50_s, digits=1)} s |"
        )
    lines += [
        "",
        "TP / FP / Dup: matched episodes / predictions outside every episode / extra predictions in an "
        "already matched episode. Delay: prediction time minus episode start (negative = inside the "
        "tolerance before the labelled start). *all alerts*: every emitted alert (L1-L3; then per level) "
        "scored against every labelled episode, whatever its behaviour; recall is not meaningful there. "
        "Hours: where a false positive of the row can happen (video time minus the row's episodes ± "
        "tolerance). FP / hour with an exact Poisson 95 % CI: a few false positives on little time say "
        "little, so no PRD verdict (≤ 1.0 / h) can be drawn from a CI that still spans it.",
    ]
    if cfg is not None and any(s.warmup_h > 0 for s in scores):
        lines += [
            "",
            "## False positives: start-up apart",
            "",
            f"The first {cfg.warmup_s:g} s of every video (`eval.warmup_s`: baselines and the PERCLOS window are "
            "still filling) against the rest. Same false positives and hours as above, split in two.",
            "",
        ] + warmup_table(scores, cfg.warmup_s)
    if windows and cfg is not None:
        lines += ["", "## FAR / MAR on windows", ""] + window_table(windows, cfg)
    if by_subject:
        lines += ["", "## Per person", ""] + subject_report(by_subject)
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
    path: Path,
    thresholds: dict[str, Any],
    speed_kmh: float,
    use_phone: bool,
    levels_out: dict[str, list[int]] | None = None,
) -> tuple[list[Prediction], float]:
    """Predictions and duration of one video. levels_out, when given, gets the highest drowsiness /
    distraction risk level of every second (for FAR / MAR windows)."""
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
    try:  # release the file even if a frame fails, so long runs do not leak handles
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
                if levels_out is not None:
                    sec = int(t)
                    for branch, reasons in (("drowsy", DROWSY_REASONS), ("distraction", DISTRACTION_REASONS)):
                        series = levels_out.setdefault(branch, [])
                        while len(series) <= sec:
                            series.append(0)
                        series[sec] = max(series[sec], branch_level(r.risk.hits, reasons))
                i += 1
    finally:
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
    subjects = read_subjects(args.labels)
    levels: Levels = {}
    if args.cmd == "score":
        predictions, durations, levels = load_predictions(args.predictions)
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
            levels[video] = {}
            preds, dur = run_video(Path(args.videos) / video, thresholds, args.speed, not args.no_phone, levels[video])
            predictions += preds
            durations[video] = dur
            print(
                f"[eval] {video}: {dur:.0f} s, {len(preds)} detections, {time.perf_counter() - t0:.0f} s",
                file=sys.stderr,
            )
        if args.save:
            save_predictions(args.save, predictions, durations, levels)

    from edge_agent.config import load_thresholds

    cfg = EvalConfig.from_dict(load_thresholds(getattr(args, "config", None)).get("eval"))
    scores = score(episodes, predictions, durations, args.tolerance, cfg.warmup_s)
    windows = window_rows(episodes, durations, levels, cfg, args.tolerance) if levels else None
    people = (
        score_by_subject(episodes, predictions, durations, subjects, args.tolerance, levels, cfg) if subjects else None
    )
    text = report(scores, durations, args.tolerance, windows, cfg, people)
    print(text)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    if args.json:
        Path(args.json).write_text(json.dumps([asdict(s) for s in scores], indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
