"""M7 - Evaluate DriverGuard on public (Kaggle) datasets.

Most public driver datasets are not timed video labels (what tools/eval.py needs) but
folders of still images per class, or clips labelled by file name. This tool maps them
to DriverGuard signals using config/datasets.yaml:

- eye_state (eye crops or faces): block 5 CNN p_closed; on faces also block 6 EAR
- yawn (faces): block 6 MAR vs drowsiness.yawn.mar_open
- phone (cabin images): block 4 YOLO, any phone and phone in the driver zone
- drowsy_frame (faces): single-frame proxy, eyes closed or mouth wide open
- video_yawn (clips): the full pipeline (blocks 2-12) through tools/eval.py, one episode per clip

For each signal: accuracy / precision / recall / F1 at the threshold in thresholds.yaml, and a
threshold sweep with the best F1, to tune thresholds on real data instead of guesses.

    pip install kagglehub                     # public datasets need no Kaggle account
    python tools/dataset.py list
    python tools/dataset.py download yawn_eye_mouth
    python tools/dataset.py eval yawn_eye_mouth --out eval/results/dataset_yawn_eye_mouth.md
    python tools/dataset.py eval state_farm --limit 200         # at most 200 files per class
    python tools/dataset.py eval mrl_eye --root D:/datasets/mrl  # already unpacked elsewhere
    python tools/dataset.py labels yawdd --out data/yawdd_labels.csv   # then tools/eval.py

Datasets go to data/kaggle/ (not in git). Images are read into RAM only; only metrics are written.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from collections import Counter
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from edge_agent.config import PROJECT_ROOT  # noqa: E402

PRESETS_PATH = PROJECT_ROOT / "config" / "datasets.yaml"
KAGGLE_CACHE = PROJECT_ROOT / "data" / "kaggle"
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
VIDEO_EXT = {".avi", ".mp4", ".mov", ".mkv"}
TASKS = ("eye_state", "yawn", "phone", "drowsy_frame", "video_yawn")
YOLO_SWEEP_CONF = 0.05  # YOLO keeps boxes down to this score so the sweep can go below conf_threshold


@dataclass(frozen=True)
class Preset:
    name: str
    kaggle: str
    task: str
    positive: str
    classes: dict[str, str]  # folder / suffix, lower case -> label
    input: str = "face"
    label_from: str = "folder"
    split: str | None = None
    description: str = ""

    @property
    def is_video(self) -> bool:
        """True for a preset whose samples are videos, not images."""
        return self.task.startswith("video_")


@dataclass(frozen=True)
class Sample:
    path: Path
    label: str
    group: str  # original class name (e.g. State Farm c6), for per-group rates


@dataclass
class Signal:
    """One scalar per sample; the sample is predicted positive when score is on the positive side of threshold."""

    name: str
    threshold: float  # the value configured in thresholds.yaml
    higher_is_positive: bool
    scores: list[float | None] = field(default_factory=list)  # None = not measurable (no face)


# --------------------------------------------------------------------------- presets and files


def load_presets(path: str | Path = PRESETS_PATH) -> dict[str, Preset]:
    """Load the dataset presets from their YAML file, by name."""
    import yaml

    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    presets = {}
    for name, d in raw.items():
        task = d["task"]
        if task not in TASKS:
            raise ValueError(f"{name}: unknown task {task!r} (expected one of {TASKS})")
        presets[name] = Preset(
            name=name,
            kaggle=d["kaggle"],
            task=task,
            positive=d["positive"],
            classes={str(k).lower(): str(v) for k, v in d["classes"].items()},
            input=d.get("input", "face"),
            label_from=d.get("label_from", "folder"),
            split=d.get("split"),
            description=d.get("description", ""),
        )
    return presets


def download(preset: Preset) -> Path:
    """Download (or reuse the cached copy of) the preset's Kaggle dataset; returns its root folder."""
    os.environ.setdefault("KAGGLEHUB_CACHE", str(KAGGLE_CACHE))
    try:
        import kagglehub
    except ImportError as e:
        raise SystemExit("kagglehub is not installed: pip install kagglehub (or pass --root to a local copy)") from e
    return Path(kagglehub.dataset_download(preset.kaggle))


def label_of(path: Path, root: Path, preset: Preset) -> tuple[str, str] | None:
    """(label, group) for a file, or None when it is not part of the preset (other split / class)."""
    parts = [p.lower() for p in path.relative_to(root).parts]
    if preset.split is not None and preset.split.lower() not in parts[:-1]:
        return None
    if preset.label_from == "stem_suffix":
        stem = path.name.split(".")[0]  # YawDD has names like "11-FemaleGlasses.avi.avi"
        key = stem.rsplit("-", 1)[-1].lower() if "-" in stem else ""
        return (preset.classes[key], key) if key in preset.classes else None
    for folder in reversed(parts[:-1]):  # the deepest matching folder wins
        if folder in preset.classes:
            return preset.classes[folder], folder
    return None


def collect_samples(root: Path, preset: Preset, limit_per_class: int | None = None) -> list[Sample]:
    """Every labelled file under root, sorted; with a limit, evenly spaced files of each class."""
    ext = VIDEO_EXT if preset.is_video else IMAGE_EXT
    by_label: dict[str, list[Sample]] = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in ext):
        found = label_of(path, root, preset)
        if found is not None:
            by_label.setdefault(found[0], []).append(Sample(path, found[0], found[1]))
    samples: list[Sample] = []
    for label in sorted(by_label):
        items = by_label[label]
        if limit_per_class is not None and len(items) > limit_per_class:
            step = len(items) / limit_per_class
            items = [items[int(i * step)] for i in range(limit_per_class)]
        samples += items
    return samples


# --------------------------------------------------------------------------- metrics (pure)


def confusion(pred: list[bool], truth: list[bool]) -> dict[str, Any]:
    """Confusion counts of boolean predictions against the truth, with the rates derived from them."""
    tp = sum(p and t for p, t in zip(pred, truth, strict=True))
    fp = sum(p and not t for p, t in zip(pred, truth, strict=True))
    fn = sum(t and not p for p, t in zip(pred, truth, strict=True))
    tn = len(pred) - tp - fp - fn
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * precision * recall / (precision + recall) if precision and recall else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "accuracy": (tp + tn) / len(pred) if pred else None,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "specificity": tn / (tn + fp) if tn + fp else None,
    }


def predict(signal: Signal, threshold: float) -> list[bool]:
    """Unmeasurable samples (None) are predicted negative: the system would not alert on them."""
    if signal.higher_is_positive:
        return [s is not None and s >= threshold for s in signal.scores]
    return [s is not None and s <= threshold for s in signal.scores]


def sweep(signal: Signal, truth: list[bool], steps: int = 100) -> list[tuple[float, dict[str, Any]]]:
    """Metrics at score quantiles (scores often pile up near 0 and 1) plus the configured threshold."""
    values = sorted(s for s in signal.scores if s is not None)
    if not values:
        return []
    grid = {signal.threshold} | {values[round(i * (len(values) - 1) / (steps - 1))] for i in range(steps)}
    return [(thr, confusion(predict(signal, thr), truth)) for thr in sorted(grid)]


def youden(m: dict[str, Any]) -> float:
    """Recall + specificity - 1: 0 for a signal no better than chance, even on a balanced set where
    "everything positive" already scores F1 0.67."""
    return (m["recall"] or 0.0) + (m["specificity"] or 0.0) - 1.0


def best_threshold(rows: list[tuple[float, dict[str, Any]]]) -> tuple[float, dict[str, Any]] | None:
    """The (threshold, metrics) row with the best Youden index, F1 breaking ties; None when empty."""
    return max(rows, key=lambda r: (youden(r[1]), r[1]["f1"]), default=None)


def _pct(v: float | None) -> str:
    return "–" if v is None else f"{v * 100:.1f}%"


def metric_tables(signals: list[Signal], truth: list[bool], note: str) -> list[str]:
    """Markdown: metrics at the configured threshold, then at the best-F1 threshold."""
    lines = [
        "",
        f"## At the configured threshold ({note})",
        "",
        "| Signal | Threshold | Accuracy | Precision | Recall | F1 | TP | FP | FN | TN |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for sig in signals:
        m = confusion(predict(sig, sig.threshold), truth)
        lines.append(
            f"| {sig.name} | {'≥' if sig.higher_is_positive else '≤'} {sig.threshold:.3g} | {_pct(m['accuracy'])} | "
            f"{_pct(m['precision'])} | {_pct(m['recall'])} | {m['f1']:.2f} | "
            f"{m['tp']} | {m['fp']} | {m['fn']} | {m['tn']} |"
        )
    lines += [
        "",
        f"## Best threshold on this data, max recall + specificity ({note})",
        "",
        "| Signal | Best threshold | Accuracy | Precision | Recall | Specificity | F1 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for sig in signals:
        best = best_threshold(sweep(sig, truth))
        if best is None:
            lines.append(f"| {sig.name} | – | – | – | – | – | – |")
            continue
        thr, m = best
        lines.append(
            f"| {sig.name} | {thr:.3g} | {_pct(m['accuracy'])} | {_pct(m['precision'])} | "
            f"{_pct(m['recall'])} | {_pct(m['specificity'])} | {m['f1']:.2f} |"
        )
    return lines


def report(preset: Preset, samples: list[Sample], signals: list[Signal], face_found: list[bool] | None) -> str:
    """The Markdown report of an image dataset: each signal against the labels."""
    truth = [s.label == preset.positive for s in samples]
    counts = Counter(s.label for s in samples)
    lines = [
        f"# DriverGuard - dataset evaluation: {preset.name}",
        "",
        f"Dataset: [{preset.kaggle}](https://www.kaggle.com/datasets/{preset.kaggle})"
        + (f", split `{preset.split}`" if preset.split else ""),
        f"{preset.description}",
        "",
        f"{len(samples)} images: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) + ".",
    ]
    n_pos = sum(truth)
    lines.append(
        f"Unit: one image. Positive (`{preset.positive}`): {n_pos} of {len(samples)} ({n_pos / len(samples):.1%}). "
        "Images are not grouped by person here: the same person can be on both sides of any split."
    )
    if face_found is not None:
        per_label = Counter(s.label for s, ok in zip(samples, face_found, strict=True) if ok)
        lines.append(
            "Face found (MediaPipe): "
            + ", ".join(f"{k} {per_label[k]}/{v} ({_pct(per_label[k] / v)})" for k, v in sorted(counts.items()))
            + ". No face = predicted negative."
        )
    lines += metric_tables(signals, truth, f"positive = `{preset.positive}`")
    if face_found is not None and not all(face_found):  # the same without the images MediaPipe missed
        keep = [i for i, ok in enumerate(face_found) if ok]
        subset = [replace(sig, scores=[sig.scores[i] for i in keep]) for sig in signals]
        lines += metric_tables(subset, [truth[i] for i in keep], f"only the {len(keep)} images with a face")
    groups = sorted({s.group for s in samples})
    if len(groups) > len(counts):  # several source classes per label (State Farm c0-c9): show each
        lines += ["", "## Predicted positive rate per source class", ""]
        lines += ["| Class | Label | n | " + " | ".join(sig.name for sig in signals) + " |"]
        lines += ["|---|---|---:|" + "---:|" * len(signals)]
        for g in groups:
            idx = [i for i, s in enumerate(samples) if s.group == g]
            rates = [sum(predict(sig, sig.threshold)[i] for i in idx) / len(idx) for sig in signals]
            label = samples[idx[0]].label
            lines.append(f"| {g} | {label} | {len(idx)} | " + " | ".join(_pct(r) for r in rates) + " |")
    lines += [
        "",
        "Still images: signals of a single frame, without the per-driver baselines and time rules of blocks "
        "7-8 (EAR uses `eye.baseline_init x eye.close_ratio`). A better threshold here is a hint to check "
        "with `tools/eval.py` on video before changing `config/thresholds.yaml`.",
    ]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- running the models on images


class ImageRunner:
    """Blocks 2-6 on still images, models loaded once."""

    def __init__(self, thresholds: dict[str, Any], preset: Preset) -> None:
        from edge_agent.perception import PreprocessConfig, Preprocessor
        from edge_agent.perception.eye_state import EyeStateConfig, EyeStateEstimator, OnnxEyeClassifier
        from edge_agent.perception.features import FeatureConfig, FeatureExtractor
        from edge_agent.perception.landmarks import FaceLandmarkDetector, LandmarkConfig
        from edge_agent.perception.phone_detector import PhoneDetectorConfig, YoloPhoneModel

        self.preset = preset
        self.preprocessor = Preprocessor(PreprocessConfig.from_dict(thresholds.get("preprocess")))
        eye_cfg = replace(EyeStateConfig.from_dict(thresholds.get("eye_state")), enabled=True, always_run=True)
        self.eye_classifier = OnnxEyeClassifier(eye_cfg) if preset.task in ("eye_state", "drowsy_frame") else None
        self.eye_estimator = EyeStateEstimator(eye_cfg, self.eye_classifier) if self.eye_classifier else None
        self.eye_size = eye_cfg.input_size
        self.landmarks = None
        if preset.input == "face":
            self.landmarks = FaceLandmarkDetector(
                LandmarkConfig.from_dict(thresholds.get("landmarks")), image_mode=True
            )
            self.extractor = FeatureExtractor(FeatureConfig.from_dict(thresholds.get("features")))
        self.phone_cfg = PhoneDetectorConfig.from_dict(thresholds.get("phone"))
        self.yolo = None
        if preset.task == "phone":
            self.yolo = YoloPhoneModel(replace(self.phone_cfg, conf_threshold=YOLO_SWEEP_CONF))

    def close(self) -> None:
        """Release the landmark model."""
        if self.landmarks is not None:
            self.landmarks.close()

    def measure(self, image: Any) -> dict[str, float | bool | None]:
        """Run the perception blocks on one image and return its measurements."""
        import cv2

        from edge_agent.capture import Frame
        from edge_agent.perception.phone_detector import driver_zone, face_bbox

        if self.preset.input == "eye_crop":  # the image is one eye: straight to the CNN
            crop = cv2.resize(image, (self.eye_size, self.eye_size), interpolation=cv2.INTER_AREA)
            return {"p_closed": float(self.eye_classifier(crop[None])[0])}

        pre = self.preprocessor(Frame(image=image, frame_id=0, timestamp=0.0))
        lm = self.landmarks.detect(pre)
        self.extractor.reset()
        f = self.extractor(lm, 0, 0.0)
        out: dict[str, float | bool | None] = {"face": lm is not None, "ear": f.ear, "mar": f.mar}
        if self.eye_estimator is not None:
            state = self.eye_estimator.estimate(pre, lm, f)
            out["p_closed"] = None if state is None else state.p_closed
        if self.yolo is not None:
            dets = self.yolo(pre.image)
            out["phone_any"] = max((d.score for d in dets), default=0.0)
            zone_score = None
            if lm is not None:
                zx1, zy1, zx2, zy2 = driver_zone(face_bbox(lm.points), self.phone_cfg)
                inside = [
                    d.score
                    for d in dets
                    if zx1 <= (d.bbox[0] + d.bbox[2]) / 2 <= zx2 and zy1 <= (d.bbox[1] + d.bbox[3]) / 2 <= zy2
                ]
                zone_score = max(inside, default=0.0)
            out["phone_zone"] = zone_score
        return out


def make_signals(preset: Preset, thresholds: dict[str, Any]) -> list[Signal]:
    """The signals (EAR, p_closed, MAR, ...) this preset is scored on, with their thresholds."""
    d = thresholds.get("drowsiness") or {}
    eye, yawn = d.get("eye") or {}, d.get("yawn") or {}
    ear_thr = float(eye.get("baseline_init", 0.28)) * float(eye.get("close_ratio", 0.65))
    cnn_thr = float(eye.get("cnn_closed", 0.6))
    mar_thr = float(yawn.get("mar_open", 0.45))
    phone_thr = float((thresholds.get("phone") or {}).get("conf_threshold", 0.35))
    cnn = Signal("p_closed (CNN, block 5)", cnn_thr, True)
    ear = Signal("EAR (block 6)", ear_thr, False)
    mar = Signal("MAR (block 6)", mar_thr, True)
    if preset.task == "eye_state":
        return [cnn] if preset.input == "eye_crop" else [ear, cnn]
    if preset.task == "yawn":
        return [mar]
    if preset.task == "phone":
        return [
            Signal("phone in driver zone (block 4)", phone_thr, True),
            Signal("any phone (block 4)", phone_thr, True),
        ]
    if preset.task == "drowsy_frame":
        # proxy score: how far past its threshold the most alarming cue is (> 0 = positive)
        return [ear, cnn, mar, Signal("eyes closed or yawn (EAR / MAR)", 0.0, True)]
    raise ValueError(f"{preset.task} is not an image task")


def fill_signals(signals: list[Signal], m: dict[str, Any]) -> None:
    """Add the measurements of one image to every signal."""
    for sig in signals:
        if sig.name.startswith("p_closed"):
            value = m.get("p_closed")
        elif sig.name.startswith("EAR"):
            value = m.get("ear")
        elif sig.name.startswith("MAR"):
            value = m.get("mar")
        elif sig.name.startswith("phone in driver zone"):
            value = m.get("phone_zone")
        elif sig.name.startswith("any phone"):
            value = m.get("phone_any")
        else:  # drowsy proxy: max of the normalised margins of EAR and MAR
            ear_sig, mar_sig = signals[0], signals[2]
            margins = []
            if m.get("ear") is not None:
                margins.append((ear_sig.threshold - m["ear"]) / ear_sig.threshold)
            if m.get("mar") is not None:
                margins.append((m["mar"] - mar_sig.threshold) / mar_sig.threshold)
            value = max(margins) if margins else None
        sig.scores.append(None if value is None else float(value))


def eval_images(preset: Preset, samples: list[Sample], thresholds: dict[str, Any]) -> str:
    """Measure every image of the preset and return the report."""
    import cv2

    signals = make_signals(preset, thresholds)
    runner = ImageRunner(thresholds, preset)
    face_found: list[bool] | None = [] if preset.input == "face" else None
    t0 = time.perf_counter()
    try:
        for i, s in enumerate(samples, 1):
            image = cv2.imread(str(s.path), cv2.IMREAD_COLOR)
            m = {} if image is None else runner.measure(image)
            fill_signals(signals, m)
            if face_found is not None:
                face_found.append(bool(m.get("face")))
            if i % 200 == 0 or i == len(samples):
                print(f"[dataset] {i}/{len(samples)} images, {time.perf_counter() - t0:.0f} s", file=sys.stderr)
    finally:
        runner.close()
    return report(preset, samples, signals, face_found)


# --------------------------------------------------------------------------- video presets -> tools/eval.py


def video_duration(path: Path) -> float:
    """Length of a video in seconds."""
    import cv2

    cap = cv2.VideoCapture(str(path))
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    finally:
        cap.release()
    return frames / fps if fps and 0 < fps < 1000 and frames > 0 else 0.0


def clip_label_rows(preset: Preset, samples: list[Sample], root: Path, durations: dict[str, float]) -> list[list[Any]]:
    """Rows for tools/eval.py: a positive clip is one episode covering the whole clip, others are `none`."""
    behavior = preset.task.removeprefix("video_")
    rows = []
    for s in samples:
        name = s.path.relative_to(root).as_posix()
        if s.label == preset.positive:
            rows.append([name, behavior, 0.0, round(durations[name], 3)])
        else:
            rows.append([name, "none", "", ""])
    return rows


def write_labels(path: str | Path, rows: list[list[Any]]) -> None:
    """Write the label rows (video, behavior, start_s, end_s) as CSV."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["video", "behavior", "start_s", "end_s"])
        w.writerows(rows)


def eval_videos(
    preset: Preset, samples: list[Sample], root: Path, thresholds: dict[str, Any], speed: float, save: str | None = None
) -> str:
    """Run the pipeline on every video of the preset and return the report."""
    from tools import eval as ev

    predictions, durations, levels = [], {}, {}
    for i, s in enumerate(samples, 1):
        name = s.path.relative_to(root).as_posix()
        t0 = time.perf_counter()
        levels[name] = {}
        preds, dur = ev.run_video(s.path, thresholds, speed, use_phone=False, levels_out=levels[name])
        predictions += [replace(p, video=name) for p in preds]
        durations[name] = dur
        print(f"[dataset] {i}/{len(samples)} {name}: {dur:.0f} s, {time.perf_counter() - t0:.0f} s", file=sys.stderr)
    if save:  # re-score or break down later with tools/eval.py score
        ev.save_predictions(save, predictions, durations, levels)
    rows = clip_label_rows(preset, samples, root, durations)
    episodes = [ev.Episode(r[0], r[1], float(r[2]), float(r[3])) for r in rows if r[1] != "none"]
    cfg = ev.EvalConfig.from_dict(thresholds.get("eval"))
    windows = ev.window_rows(episodes, durations, levels, cfg, tolerance_s=0.0)
    text = ev.report(ev.score(episodes, predictions, durations, tolerance_s=0.0), durations, 0.0, windows, cfg)
    return f"Dataset: {preset.kaggle} ({preset.name}), clip-level labels.\n\n" + text


# --------------------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point (see the module doc). Returns the process exit code."""
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--presets", default=str(PRESETS_PATH), help="dataset presets YAML")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="show the dataset presets")
    dl = sub.add_parser("download", help="download a preset's Kaggle dataset into data/kaggle/")
    ev_p = sub.add_parser("eval", help="run DriverGuard on a dataset and write the metrics")
    lb = sub.add_parser("labels", help="video presets: write a labels CSV for tools/eval.py")
    for s in (dl, ev_p, lb):
        s.add_argument("preset")
    for s in (ev_p, lb):
        s.add_argument("--root", default=None, help="local dataset folder (default: download with kagglehub)")
        s.add_argument("--limit", type=int, default=None, help="at most this many files per class")
    ev_p.add_argument("--config", default=None, help="thresholds.yaml to evaluate (default: config/thresholds.yaml)")
    ev_p.add_argument("--speed", type=float, default=60.0, help="video presets: simulated speed, km/h")
    ev_p.add_argument("--out", default=None, help="also write the markdown report here")
    ev_p.add_argument("--save", default=None, help="video presets: write the predictions JSON here")
    lb.add_argument("--out", required=True, help="labels CSV to write")
    if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp1252: the report has ≥, ≤
        sys.stdout.reconfigure(encoding="utf-8")
    args = p.parse_args(argv)

    presets = load_presets(args.presets)
    if args.cmd == "list":
        for pr in presets.values():
            print(f"{pr.name:16s} {pr.task:13s} {pr.kaggle}\n{'':16s} {pr.description}")
        return 0
    if args.preset not in presets:
        p.error(f"unknown preset {args.preset!r}, one of: {', '.join(presets)}")
    preset = presets[args.preset]
    if args.cmd == "download":
        print(f"[dataset] {preset.name}: {download(preset)}")
        return 0

    root = Path(args.root) if args.root else download(preset)
    samples = collect_samples(root, preset, args.limit)
    if not samples:
        p.error(f"no labelled files for {preset.name} under {root}: check --root / split / classes")
    print(f"[dataset] {preset.name}: {len(samples)} files under {root}", file=sys.stderr)

    if args.cmd == "labels":
        if not preset.is_video:
            p.error("labels is for video presets; image presets are scored with `eval`")
        durations = {s.path.relative_to(root).as_posix(): video_duration(s.path) for s in samples}
        write_labels(args.out, clip_label_rows(preset, samples, root, durations))
        print(f"[dataset] wrote {args.out}. Next:\n  python tools/eval.py run --labels {args.out} --videos {root}")
        return 0

    from edge_agent.config import load_thresholds

    thresholds = load_thresholds(args.config)
    if preset.is_video:
        text = eval_videos(preset, samples, root, thresholds, args.speed, args.save)
    else:
        text = eval_images(preset, samples, thresholds)
    print(text)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
