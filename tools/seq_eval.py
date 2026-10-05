"""M7 - Evaluate DriverGuard on frame-labelled and clip-labelled driving videos.

Two datasets that tools/dataset.py cannot score as they are:

- FL3D (Kaggle matjazmuc/frame-level-driver-drowsiness-detection-fl3d): one label per frame
  (alert / microsleep / yawning) for 44 NITYMED night-driving videos (Kaggle
  nikospetrellis/nitymed, 25 FPS). FL3D ships face crops; here the full pipeline runs on the
  original NITYMED videos (what the camera really sees) and the frame labels are matched by
  frame index.
- SUST-DDD (Sivas University, 2074 phone-camera clips of 10 s, real driving): one label per
  clip, drowsy (d_*.mp4) or not (n_*.mp4).

Step 1 `trace` runs blocks 2-12 on every video (fresh state per video, every frame, time =
frame_index / fps) and keeps one row of numbers per frame (EAR, MAR, pose, eye state, PERCLOS,
events, risk level, alerts). The eye-state CNN is also run on every frame as a diagnostic
column (`p_cnn`), separate from what the pipeline used (`p_closed`). Traces hold metadata only,
no image; frames stay in RAM.

Step 2 `fl3d` / `sust` / `yawdd` score the traces and write a markdown report. False alarms per
hour come with the hours they are measured on and an exact Poisson 95 % CI, split by reason and
level; FL3D and YawDD also get FAR / MAR on fixed windows (tools/metrics.py, thresholds.yaml
`eval`). SUST clips (10 s) are shorter than the start-up stretch left out of the windows.

    python tools/seq_eval.py trace fl3d --out data/eval_traces/fl3d.pkl --workers 8
    python tools/seq_eval.py fl3d --traces data/eval_traces/fl3d.pkl --out eval/results/dataset_fl3d.md
    python tools/seq_eval.py trace sust --out data/eval_traces/sust.pkl --workers 8
    python tools/seq_eval.py sust --traces data/eval_traces/sust.pkl --out eval/results/dataset_sust_ddd.md
    python tools/seq_eval.py yawdd --traces data/eval_traces/yawdd_v2.pkl --replay block5 --out eval/results/dataset_yawdd.md
"""

from __future__ import annotations

import argparse
import json
import pickle
import re
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from edge_agent.config import PROJECT_ROOT  # noqa: E402
from tools.metrics import (  # noqa: E402
    DISTRACTION_REASONS,
    DROWSY_REASONS,
    EvalConfig,
    WindowCounts,
    branch_level,
    ci_text,
    per_second_max,
    rate_ci,
    window_scores,
    window_table,
)

FL3D_ROOT = (
    PROJECT_ROOT
    / "data/kaggle/datasets/matjazmuc/frame-level-driver-drowsiness-detection-fl3d/versions/1/classification_frames"
)
NITYMED_ROOT = PROJECT_ROOT / "data/kaggle/datasets/nikospetrellis/nitymed/versions/1/DSM_Dataset-HDTV720"
SUST_ROOT = PROJECT_ROOT / "data/sust-ddd/SUST Driver Drowsiness Dataset"
YAWDD_ROOT = PROJECT_ROOT / "data/kaggle/datasets/enider/yawdd-dataset/versions/4/Mirror"

COLUMNS = (
    "t face reliable ear ear_base mar pitch yaw p_closed p_cnn eye_closed closed_duration "
    "perclos perclos_ready yawning masked off_road no_face_s level drowsy_score "
    "ear_l ear_r face_bright is_ir blink"  # raw inputs of block 5, so its trigger can be replayed
    " brow"  # browOuterUp blendshape (v2 brow-raise signal of block 7); traces made before v2 lack it
).split()


# --------------------------------------------------------------------------- tracing (models)


def trace_video(path: Path, thresholds: dict[str, Any], speed_kmh: float = 60.0, use_phone: bool = True) -> dict:
    """Blocks 2-12 on one video; per-frame numbers, events and alerts (same wiring as tools/eval.py)."""
    import cv2

    from edge_agent.capture import Frame
    from edge_agent.context.can_sim import CanSimulator, scenario_from_dict
    from edge_agent.decision.pipeline import DecisionPipeline
    from edge_agent.perception import PreprocessConfig, Preprocessor
    from edge_agent.perception.eye_state import EyeStateConfig, EyeStateEstimator, face_brightness, make_estimator
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
    rows: list[tuple] = []
    events: list[tuple[int, str]] = []
    alerts: list[tuple[int, int, tuple[str, ...]]] = []
    try:
        if not cap.isOpened():
            raise RuntimeError(f"cannot open {path}")
        fps = cap.get(cv2.CAP_PROP_FPS)
        fps = fps if 0 < fps < 1000 else 30.0
        preprocessor = Preprocessor(PreprocessConfig.from_dict(thresholds.get("preprocess")))
        extractor = FeatureExtractor(FeatureConfig.from_dict(thresholds.get("features")))
        eye_cfg = EyeStateConfig.from_dict(thresholds.get("eye_state"))
        eye_state = make_estimator(eye_cfg)
        eye_diag = EyeStateEstimator(replace(eye_cfg, enabled=True, always_run=True, source="cnn"))
        phone_cfg = replace(PhoneDetectorConfig.from_dict(thresholds.get("phone")), num_threads=1)
        yolo = YoloPhoneModel(phone_cfg) if use_phone else None
        yolo_every = max(1, round(fps / phone_cfg.target_fps))
        pipeline = DecisionPipeline(thresholds)
        can = CanSimulator(scenario_from_dict({"start_clock": "12:00", "timeline": [{"t": 0, "speed_kmh": speed_kmh}]}))
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
                diag = eye_diag.estimate(pre, lm, feats)
                if eye_state is not None:
                    feats = eye_state(pre, lm, feats)
                r = pipeline.step(feats, phone_flag, can.sample(t))
                d = r.drowsiness
                rows.append(
                    (
                        t,
                        feats.face_found,
                        feats.face_reliable,
                        feats.ear,
                        d.ear_open_baseline,
                        feats.mar,
                        feats.pitch,
                        feats.yaw,
                        feats.p_closed,
                        None if diag is None else diag.p_closed,
                        None if d.eye_closed is None else int(d.eye_closed),
                        d.closed_duration,
                        d.perclos_60s,
                        d.perclos_ready,
                        d.yawning,
                        d.closure_masked,
                        r.distraction.off_road,
                        r.distraction.no_face_duration,
                        r.risk.level,
                        r.risk.drowsy_score,
                        feats.ear_left,
                        feats.ear_right,
                        face_brightness(pre, lm) if lm is not None else None,
                        pre.is_ir,
                        feats.eye_blink,
                        feats.brow_up,
                    )
                )
                events += [(i, ev) for ev in d.events]
                if r.alert.new_alert is not None:
                    alerts.append((i, r.alert.new_alert.level, tuple(r.alert.new_alert.reasons)))
                i += 1
    finally:
        cap.release()
    cols = {name: np.array([np.nan if v is None else float(v) for v in col]) for name, col in zip(COLUMNS, zip(*rows))}
    return {"fps": fps, "n": len(rows), "cols": cols, "events": events, "alerts": alerts}


def _trace_job(args: tuple[str, str, dict[str, Any], float, bool]) -> tuple[str, dict | str]:
    key, path, thresholds, speed, use_phone = args
    try:
        return key, trace_video(Path(path), thresholds, speed, use_phone)
    except Exception as e:  # one broken clip must not stop a 2000-clip run
        return key, f"{type(e).__name__}: {e}"


def dataset_videos(name: str, limit: int | None = None) -> dict[str, Path]:
    if name == "fl3d":
        wanted = {p.name.removesuffix("_720") for p in FL3D_ROOT.iterdir() if p.is_dir()}
        found = {p.stem.removesuffix("_720"): p for p in NITYMED_ROOT.rglob("*.mp4")}
        return {k: found[k] for k in sorted(wanted) if k in found}
    if name == "sust":
        vids = {f"{p.parent.name}/{p.name}": p for p in sorted(SUST_ROOT.rglob("*.mp4"))}
        if limit:  # evenly spaced clips of each class
            out: dict[str, Path] = {}
            for cls in ("drowsiness", "not drowsiness"):
                keys = [k for k in vids if k.startswith(cls + "/")]
                step = max(1, len(keys) // limit)
                out |= {k: vids[k] for k in keys[::step][:limit]}
            return out
        return vids
    if name == "yawdd":  # regression check of what-if thresholds (Talking / Normal clips must stay quiet)
        return {p.relative_to(YAWDD_ROOT).as_posix(): p for p in sorted(YAWDD_ROOT.rglob("*.avi"))}
    raise ValueError(name)


def run_traces(
    name: str, out: str, workers: int, speed: float, use_phone: bool, limit: int | None, sets: list[str] = ()
) -> None:
    from multiprocessing import get_context

    from edge_agent.config import load_thresholds

    thresholds = load_thresholds()
    for a in sets:  # what-if on blocks 2-6 too (e.g. when the eye CNN is called)
        set_threshold(thresholds, a)
    videos = dataset_videos(name, limit)
    done: dict[str, Any] = {}
    if Path(out).exists():  # resume an interrupted run
        done = pickle.loads(Path(out).read_bytes())
    jobs = [(k, str(p), thresholds, speed, use_phone) for k, p in videos.items() if k not in done]
    print(f"[seq_eval] {name}: {len(videos)} videos, {len(jobs)} to trace, {workers} workers", file=sys.stderr)
    t0 = time.perf_counter()
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with get_context("spawn").Pool(workers) as pool:
        for n, (key, res) in enumerate(pool.imap_unordered(_trace_job, jobs), 1):
            done[key] = res
            if isinstance(res, str):
                print(f"[seq_eval] {key}: {res}", file=sys.stderr)
            if n % 50 == 0 or n == len(jobs):
                Path(out).write_bytes(pickle.dumps(done))
                rate = n / (time.perf_counter() - t0)
                print(f"[seq_eval] {n}/{len(jobs)}, {rate:.1f} videos/s", file=sys.stderr)
    Path(out).write_bytes(pickle.dumps(done))


# --------------------------------------------------------------------------- what-if replay (blocks 7-12 only)


def replay(tr: dict, thresholds: dict[str, Any], eye: str = "trace", observe: Any = None) -> dict:
    """Blocks 7-12 again on a trace's features, e.g. with other thresholds, without re-running the models.

    eye: which p_closed block 7 gets. "trace" = what the pipeline used (reproduces the run),
    "ear" = never the CNN (EAR only), "cnn" = the CNN on every frame, "block5" = block 5 decided
    again with `thresholds` (trigger + hold, score from eye_state.source; needs the raw columns
    of a trace made after the block 5 fix). No phone flag (none is traced).
    observe: called as observe(i, pipeline, result) after every frame, for tools that need more than
    the returned columns (tools/blink_duration.py reads block 7's blink timings).
    """
    from edge_agent.context.can_sim import CanSimulator, scenario_from_dict
    from edge_agent.decision.pipeline import DecisionPipeline
    from edge_agent.perception.features import FrameFeatures

    c = tr["cols"]
    if eye == "block5":
        pcol = block5_scores(c, thresholds)
    else:
        pcol = {"trace": c["p_closed"], "cnn": c["p_cnn"], "ear": np.full(tr["n"], np.nan)}[eye]
    blink = c.get("blink", np.full(tr["n"], np.nan))
    brow = c.get("brow", np.full(tr["n"], np.nan))
    pipeline = DecisionPipeline(thresholds)
    can = CanSimulator(scenario_from_dict({"start_clock": "12:00", "timeline": [{"t": 0, "speed_kmh": 60.0}]}))
    out = {
        k: np.empty(tr["n"])
        for k in (
            "eye_closed",
            "closed_duration",
            "masked",
            "yawning",
            "level",
            "drowsy_score",
            "drowsy_level",  # per branch, for FAR / MAR windows
            "distraction_level",
        )
    }
    events: list[tuple[int, str]] = []
    alerts: list[tuple[int, int, tuple[str, ...]]] = []

    def val(x: float) -> float | None:
        return None if np.isnan(x) else float(x)

    for i in range(tr["n"]):
        face = bool(c["face"][i])
        f = FrameFeatures(
            frame_id=i,
            timestamp=float(c["t"][i]),
            face_found=face,
            face_conf=1.0 if c["reliable"][i] == 1 else 0.0,
            face_reliable=bool(c["reliable"][i] == 1),
            ear=val(c["ear"][i]),
            mar=val(c["mar"][i]),
            pitch=val(c["pitch"][i]),
            yaw=val(c["yaw"][i]),
            eye_blink=val(blink[i]),
            brow_up=val(brow[i]),
            p_closed=val(pcol[i]) if face else None,
        )
        r = pipeline.step(f, None, can.sample(f.timestamp))
        d = r.drowsiness
        out["eye_closed"][i] = np.nan if d.eye_closed is None else float(d.eye_closed)
        out["closed_duration"][i] = d.closed_duration
        out["masked"][i] = d.closure_masked
        out["yawning"][i] = d.yawning
        out["level"][i] = r.risk.level
        out["drowsy_score"][i] = r.risk.drowsy_score
        out["drowsy_level"][i] = branch_level(r.risk.hits, DROWSY_REASONS)
        out["distraction_level"][i] = branch_level(r.risk.hits, DISTRACTION_REASONS)
        events += [(i, ev) for ev in d.events]
        if r.alert.new_alert is not None:
            alerts.append((i, r.alert.new_alert.level, tuple(r.alert.new_alert.reasons)))
        if observe is not None:
            observe(i, pipeline, r)
    return {**tr, "cols": {**c, **out}, "events": events, "alerts": alerts}


def block5_scores(c: dict[str, np.ndarray], thresholds: dict[str, Any]) -> np.ndarray:
    """p_closed per frame as block 5 would give it with these thresholds (NaN = EAR decides)."""
    from edge_agent.perception.eye_state import EyeStateConfig, EyeStateEstimator, trigger_from_values

    cfg = EyeStateConfig.from_dict(thresholds.get("eye_state"))
    if not cfg.enabled:
        return np.full(len(c["t"]), np.nan)
    est = EyeStateEstimator(cfg, classifier=lambda crops: np.zeros(len(crops)))  # scores come from the trace
    score = c["blink"] if cfg.source == "blendshape" else c["p_cnn"]
    out = np.full(len(c["t"]), np.nan)
    for i in range(len(c["t"])):
        if c["face"][i] != 1 or np.isnan(c["face_bright"][i]):
            continue  # no landmarks: block 5 does nothing
        el, er = c["ear_l"][i], c["ear_r"][i]
        reason = trigger_from_values(
            cfg,
            bool(c["is_ir"][i] == 1),
            float(c["face_bright"][i]),
            None if np.isnan(el) else float(el),
            None if np.isnan(er) else float(er),
        )
        if est.decide(float(c["t"][i]), reason) is not None:
            out[i] = score[i]
    return out


def set_threshold(thresholds: dict[str, Any], assignment: str) -> None:
    """In place: "drowsiness.eye.cnn_closed=0.5" (value parsed as YAML)."""
    import yaml

    key, value = assignment.split("=", 1)
    node = thresholds
    *path, last = key.split(".")
    for k in path:
        node = node[k]
    if last not in node:
        raise KeyError(f"unknown threshold {key}")
    node[last] = yaml.safe_load(value)


def _replay_job(args: tuple[str, dict, dict[str, Any], str]) -> tuple[str, dict]:
    key, tr, thresholds, eye = args
    return key, replay(tr, thresholds, eye)


def replay_all(traces: dict, thresholds: dict[str, Any], eye: str, workers: int) -> dict:
    from multiprocessing import get_context

    ok = {k: v for k, v in traces.items() if not isinstance(v, str)}
    jobs = [(k, v, thresholds, eye) for k, v in ok.items()]
    with get_context("spawn").Pool(workers) as pool:
        return dict(pool.imap_unordered(_replay_job, jobs, chunksize=8))


# --------------------------------------------------------------------------- metrics (pure)


def auc(pos: np.ndarray, neg: np.ndarray) -> float | None:
    """ROC AUC = P(score of a positive > score of a negative), ties count half. NaN scores dropped."""
    pos, neg = pos[~np.isnan(pos)], neg[~np.isnan(neg)]
    if len(pos) == 0 or len(neg) == 0:
        return None
    allv = np.concatenate([pos, neg])
    order = allv.argsort(kind="mergesort")
    ranks = np.empty(len(allv))
    sv = allv[order]
    i = 0
    while i < len(sv):  # average ranks of ties
        j = i
        while j + 1 < len(sv) and sv[j + 1] == sv[i]:
            j += 1
        ranks[order[i : j + 1]] = (i + j) / 2.0 + 1
        i = j + 1
    return float((ranks[: len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def prf(pred: np.ndarray, truth: np.ndarray) -> dict[str, float | int | None]:
    tp = int(np.sum(pred & truth))
    fp = int(np.sum(pred & ~truth))
    fn = int(np.sum(~pred & truth))
    tn = int(np.sum(~pred & ~truth))
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": p,
        "recall": r,
        "fpr": fp / (fp + tn) if fp + tn else None,
        "f1": 2 * p * r / (p + r) if p and r else 0.0,
    }


@dataclass(frozen=True)
class Run:
    label: str
    start: int  # first frame
    end: int  # last frame (inclusive)

    def seconds(self, fps: float) -> float:
        return (self.end - self.start + 1) / fps


def label_runs(labels: dict[int, str], max_gap: int) -> list[Run]:
    """Frame labels -> runs of one label; frames up to max_gap apart (unlabelled between) are joined."""
    runs: list[Run] = []
    for f in sorted(labels):
        s = labels[f]
        if runs and runs[-1].label == s and f - runs[-1].end <= max_gap + 1:
            runs[-1] = replace(runs[-1], end=f)
        else:
            runs.append(Run(s, f, f))
    return runs


def label_at(labels: dict[int, str], frame: int, max_gap: int) -> str | None:
    """Label of the frame, or of the nearest labelled frame within max_gap; None = unlabelled region."""
    for d in range(max_gap + 1):
        for f in (frame - d, frame + d):
            if f in labels:
                return labels[f]
    return None


def classify_predictions(
    frames: list[int], positive: list[Run], labels: dict[int, str], tol: int, max_gap: int
) -> Counter:
    """Each prediction frame: `hit` (inside a positive run +- tol), `fp` (on a labelled alert frame,
    away from every positive run) or `other` (another drowsy label / unlabelled region)."""
    c: Counter = Counter()
    for f in frames:
        if any(r.start - tol <= f <= r.end + tol for r in positive):
            c["hit"] += 1
        elif label_at(labels, f, max_gap) == "alert":
            c["fp"] += 1
        else:
            c["other"] += 1
    return c


def detected(run: Run, frames: list[int], tol: int) -> int | None:
    """Delay (frames from run start) of the first prediction inside run +- tol, None if missed."""
    hits = [f for f in frames if run.start - tol <= f <= run.end + tol]
    return min(hits) - run.start if hits else None


# --------------------------------------------------------------------------- reports


def _p(v: float | None) -> str:
    return "–" if v is None else f"{v * 100:.1f}%"


def _f(v: float | None, d: int = 2) -> str:
    return "–" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:.{d}f}"


def load_fl3d_labels(root: Path = FL3D_ROOT) -> dict[str, dict[int, str]]:
    data = json.loads((root / "annotations_all.json").read_text(encoding="utf-8"))
    out: dict[str, dict[int, str]] = defaultdict(dict)
    for k, v in data.items():
        m = re.search(r"(P\d+)_720/frame(\d+)\.jpg", k)
        if m:
            out[m.group(1)][int(m.group(2))] = v["driver_state"]
    return dict(out)


def fl3d_frame_table(traces: dict, labels: dict[str, dict[int, str]], offset: int = 0) -> dict[str, np.ndarray]:
    """Stack per-frame columns of every labelled frame (+ label column)."""
    cols: dict[str, list] = defaultdict(list)
    for vid, tr in traces.items():
        if isinstance(tr, str) or vid not in labels:
            continue
        for f, s in labels[vid].items():
            i = f + offset
            if 0 <= i < tr["n"]:
                cols["label"].append(s)
                cols["video"].append(vid)
                for c in COLUMNS:  # traces made before a column existed: NaN
                    cols[c].append(tr["cols"][c][i] if c in tr["cols"] else np.nan)
    return {k: np.array(v) for k, v in cols.items()}


def fl3d_report(traces: dict, thresholds: dict[str, Any], tol_s: float = 1.0) -> str:
    labels = load_fl3d_labels()
    ok = {k: v for k, v in traces.items() if not isinstance(v, str)}
    fps = next(iter(ok.values()))["fps"]
    tol, gap = round(tol_s * fps), round(0.5 * fps)
    d_cfg = thresholds["drowsiness"]
    ms_min = float(d_cfg["microsleep_min_s"])
    l3_s = float(thresholds["risk"]["microsleep_l3_s"])
    mar_open = float(d_cfg["yawn"]["mar_open"])
    cnn_thr = float(d_cfg["eye"]["cnn_closed"])
    close_ratio = float(d_cfg["perclos_close_ratio"])
    minutes = sum(v["n"] / v["fps"] for v in ok.values()) / 60

    # alignment check: MAR AUC for yawning vs alert at a few frame offsets
    align = []
    for off in (-10, -5, -2, 0, 2, 5, 10):
        tb = fl3d_frame_table(ok, labels, off)
        align.append((off, auc(tb["mar"][tb["label"] == "yawning"], tb["mar"][tb["label"] == "alert"])))
    tb = fl3d_frame_table(ok, labels)
    lab = tb["label"]
    n_lab = Counter(lab)
    lines = [
        "# DriverGuard - evaluation on FL3D (frame labels) / NITYMED (videos)",
        "",
        f"{len(ok)} NITYMED night-driving videos, {minutes:.1f} min at {fps:g} FPS, full pipeline (blocks 2-12, YOLO on, "
        f"simulated 60 km/h). FL3D labels {len(lab)} of their frames: "
        + ", ".join(f"{k} {v}" for k, v in sorted(n_lab.items()))
        + ". Frames FL3D left out (outside its crops) are unlabelled and not scored.",
        "",
        "Frame alignment check (FL3D `frameN` = video frame N + offset), AUC of MAR for yawning vs alert: "
        + ", ".join(f"{o:+d}: {_f(a, 3)}" for o, a in align)
        + ".",
        "",
        "## 1. Measurability (blocks 3, 6)",
        "",
        "| Label | Frames | Face found | Face reliable (face_conf ≥ min) | Eye state judged (eye_closed not None) | CNN used by pipeline |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for s in ("alert", "microsleep", "yawning"):
        m = lab == s
        lines.append(
            f"| {s} | {m.sum()} | {_p(np.nanmean(tb['face'][m]))} | {_p(np.nanmean(tb['reliable'][m]))} | "
            f"{_p(np.mean(~np.isnan(tb['eye_closed'][m])))} | {_p(np.mean(~np.isnan(tb['p_closed'][m])))} |"
        )

    # ---- per-frame eye closure
    ear_ratio = tb["ear"] / tb["ear_base"]
    pos, neg = lab == "microsleep", lab == "alert"
    lines += [
        "",
        "## 2. Per frame: eyes closed (FL3D `microsleep`) vs `alert`",
        "",
        "AUC = chance that a microsleep frame scores more closed than an alert frame (0.5 = no signal). "
        "Rates over all labelled frames; a frame the system cannot judge counts as not closed.",
        "",
        "| Signal | AUC (measured frames) | Rule | Precision | Recall | FPR (alert frames called closed) |",
        "|---|---:|---|---:|---:|---:|",
    ]
    ec = tb["eye_closed"]
    sig = [
        ("block 7 eye_closed (hysteresis, EAR or CNN)", ec, "eye_closed == 1", ec == 1),
        ("EAR / open-eye baseline (block 6/7)", -ear_ratio, f"< {close_ratio} (PERCLOS rule)", ear_ratio < close_ratio),
        (
            "EAR / baseline, deep",
            -ear_ratio,
            f"≤ {d_cfg['microsleep_deep']['ear_ratio']} (deep closure)",
            ear_ratio <= float(d_cfg["microsleep_deep"]["ear_ratio"]),
        ),
        ("raw EAR", -tb["ear"], "–", None),
        ("CNN p_closed, every frame (block 5 diag)", tb["p_cnn"], f"≥ {cnn_thr}", tb["p_cnn"] >= cnn_thr),
    ]
    blink_thr = float(d_cfg["microsleep_deep"].get("blink", 0.5)) or 0.5
    if not np.all(np.isnan(tb["blink"])):  # traces made with blendshapes on
        sig.append(("MediaPipe eyeBlink blendshape (block 3)", tb["blink"], f"≥ {blink_thr}", tb["blink"] >= blink_thr))
    for name, score, rule, pred in sig:
        a = auc(score[pos], score[neg])
        if pred is None:
            lines.append(f"| {name} | {_f(a, 3)} | {rule} | – | – | – |")
            continue
        m = prf(pred[pos | neg], pos[pos | neg])
        lines.append(f"| {name} | {_f(a, 3)} | {rule} | {_p(m['precision'])} | {_p(m['recall'])} | {_p(m['fpr'])} |")

    # ---- per-frame yawning
    pos, neg = lab == "yawning", lab == "alert"
    lines += [
        "",
        "## 3. Per frame: yawning vs alert",
        "",
        "| Signal | AUC | Rule | Precision | Recall | FPR |",
        "|---|---:|---|---:|---:|---:|",
    ]
    for name, score, rule, pred in [
        ("MAR (block 6)", tb["mar"], f"≥ {mar_open}", tb["mar"] >= mar_open),
        ("block 7 yawning flag", tb["yawning"], "yawning", tb["yawning"] == 1),
        ("block 7 microsleep mask (yawn / talk)", tb["masked"], "masked", tb["masked"] == 1),
    ]:
        a = auc(score[pos], score[neg])
        m = prf(pred[pos | neg], pos[pos | neg])
        lines.append(f"| {name} | {_f(a, 3)} | {rule} | {_p(m['precision'])} | {_p(m['recall'])} | {_p(m['fpr'])} |")

    # ---- episodes
    bins = [(0, ms_min), (ms_min, l3_s), (l3_s, 3.0), (3.0, 1e9)]
    per_bin: dict[tuple, list] = defaultdict(list)
    delays_ms: list[float] = []
    yawn_det, yawn_n, yawn_delay = 0, 0, []
    l3_det, l3_n, l3_level = 0, 0, 0
    pred_class: dict[str, Counter] = defaultdict(Counter)
    alert_rows = []
    alert_minutes = 0.0
    eval_cfg = EvalConfig.from_dict(thresholds.get("eval"))
    win_levels = sorted({eval_cfg.min_level, 2})
    windows = {lv: WindowCounts() for lv in win_levels}
    for vid, tr in ok.items():
        lb = labels.get(vid, {})
        runs = label_runs(lb, gap)
        ms_runs = [r for r in runs if r.label == "microsleep"]
        yw_runs = [r for r in runs if r.label == "yawning"]
        drowsy_runs = ms_runs + yw_runs
        # FAR / MAR windows: drowsy = microsleep / yawning runs, awake = runs labelled alert
        secs = lambda rs: [(r.start / fps, (r.end + 1) / fps) for r in rs]  # noqa: E731
        col = tr["cols"].get("drowsy_level", tr["cols"]["level"])  # traces scored without replay: any reason
        per_sec = per_second_max(tr["cols"]["t"], [int(v) for v in np.nan_to_num(col)], tr["n"] / fps)
        for lv in win_levels:
            lv_cfg = EvalConfig(eval_cfg.window_s, eval_cfg.warmup_s, eval_cfg.positive_frac, lv)
            awake = secs([r for r in runs if r.label == "alert"])
            windows[lv] += window_scores(tr["n"] / fps, secs(drowsy_runs), awake, per_sec, lv_cfg, tol_s)
        ev = defaultdict(list)
        for f, e in tr["events"]:
            ev[e].append(f)
        l3 = [f for f, lv, _ in tr["alerts"] if lv == 3]
        for r in ms_runs:
            dur = r.seconds(fps)
            b = next(b for b in bins if b[0] <= dur < b[1])
            dl = detected(r, ev["microsleep"], tol)
            per_bin[b].append(dl is not None)
            if dur >= ms_min and dl is not None:
                delays_ms.append(dl / fps)
            if dur >= l3_s:
                l3_n += 1
                l3_det += detected(r, l3, tol) is not None
                lo, hi = max(0, r.start - tol), min(tr["n"], r.end + tol + 1)
                l3_level += bool(np.any(tr["cols"]["level"][lo:hi] >= 3))
        for r in yw_runs:
            yawn_n += 1
            dl = detected(r, ev["yawn"], tol)
            if dl is not None:
                yawn_det += 1
                yawn_delay.append(dl / fps)
        pred_class["microsleep event"] += classify_predictions(ev["microsleep"], ms_runs, lb, tol, gap)
        pred_class["yawn event"] += classify_predictions(ev["yawn"], yw_runs, lb, tol, gap)
        pred_class["nod event"] += classify_predictions(ev["nod"], ms_runs, lb, tol, gap)
        pred_class["perclos_high event"] += classify_predictions(ev["perclos_high"], drowsy_runs, lb, tol, gap)
        alert_minutes += sum(1 for s in lb.values() if s == "alert") / fps / 60
        for f, lv, reasons in tr["alerts"]:
            c = classify_predictions([f], drowsy_runs, lb, round(3.0 * fps), gap)
            kind = next(iter(c))
            pred_class[f"L{lv} alert"] += c
            alert_rows.append((vid, f / fps, lv, ",".join(reasons), kind))
    lines += [
        "",
        "## 4. Episodes (runs of one label, gaps ≤ 0.5 s joined)",
        "",
        f"Detected = the event falls inside the run ± {tol_s:g} s.",
        "",
        "| Labelled microsleep run | Runs | Microsleep event detected |",
        "|---|---:|---:|",
    ]
    for b in bins:
        v = per_bin[b]
        name = f"{b[0]:g}–{b[1]:g} s" if b[1] < 1e8 else f"≥ {b[0]:g} s"
        lines.append(f"| {name} | {len(v)} | {sum(v)} ({_p(sum(v) / len(v) if v else None)}) |")
    lines += [
        "",
        f"- Microsleep ≥ {ms_min:g} s: delay p50 {_f(float(np.median(delays_ms)) if delays_ms else None, 2)} s after the labelled start.",
        f"- Microsleep ≥ {l3_s:g} s (should reach L3 at once): {l3_det}/{l3_n} got a new L3 alert ({_p(l3_det / l3_n if l3_n else None)}); "
        f"risk level 3 reached on {l3_level}/{l3_n} ({_p(l3_level / l3_n if l3_n else None)}) (no new alert: L3 was still active, or its cooldown).",
        f"- Yawning runs: {yawn_det}/{yawn_n} got a yawn event ({_p(yawn_det / yawn_n if yawn_n else None)}), "
        f"delay p50 {_f(float(np.median(yawn_delay)) if yawn_delay else None, 2)} s.",
        "",
        "## 5. Where predictions land",
        "",
        f"hit = inside a matching labelled run ± {tol_s:g} s (alerts: any microsleep / yawning run ± 3 s); "
        "false = on a frame labelled `alert`, away from every drowsy run; other = another drowsy label or an "
        f"unlabelled stretch. {alert_minutes:.1f} min ({alert_minutes / 60:.2f} h) of frames are labelled alert: "
        "false alarms per hour are over those hours, with an exact Poisson 95 % CI. A few false alarms on "
        "26 minutes say little: no PRD verdict (≤ 1.0 / h) while the CI still spans it.",
        "",
        "| Prediction | Total | Hit | False | Other | False / hour of alert frames (95% CI) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    alert_h = alert_minutes / 60
    for k in ("microsleep event", "yawn event", "nod event", "perclos_high event", "L1 alert", "L2 alert", "L3 alert"):
        c = pred_class[k]
        tot = sum(c.values())
        lines.append(f"| {k} | {tot} | {c['hit']} | {c['fp']} | {c['other']} | {ci_text(rate_ci(c['fp'], alert_h))} |")
    reasons = Counter()
    false_by = Counter()
    for _, _, lv, rs, kind in alert_rows:
        for r in rs.split(","):
            reasons[(r, kind)] += 1
            false_by[(r, lv)] += kind == "fp"
    lines += ["", "Alerts by reason: " + ", ".join(f"{r} {k} {n}" for (r, k), n in sorted(reasons.items())) + "."]
    lines += [
        "",
        "False alerts by reason and level (an alert with two reasons counts under both):",
        "",
        "| Reason | Level | False | False / hour (95% CI) |",
        "|---|---:|---:|---:|",
    ]
    for (r, lv), n in sorted(false_by.items()):
        lines.append(f"| {r} | L{lv} | {n} | {ci_text(rate_ci(n, alert_h))} |")
    lines += ["", "## 5b. FAR / MAR on windows (drowsiness)", ""]
    lines += window_table([(f"Drowsiness, level ≥ L{lv}", windows[lv]) for lv in win_levels], eval_cfg)
    lines += [
        "",
        "Drowsy = FL3D microsleep / yawning frames; awake = frames labelled alert; frames FL3D left out are "
        "unlabelled. Distraction is not labelled in FL3D.",
        "",
        "Read with care: the videos are ~1 min (30 s start-up left out) and dense with microsleep / yawning runs, "
        "so few windows qualify. FL3D `alert` frames sit between the microsleeps of the same drowsy actor, and "
        "`drowsy_score` is meant to stay up for minutes after a microsleep: a high FAR here is not an awake driver "
        "disturbed. FAR / MAR are for long recordings (UTA-RLDD, DMD).",
    ]
    lines += [
        "",
        "## 6. Per video",
        "",
        "| Video | Min | Face | Microsleep runs ≥1 s (detected) | Yawn runs (detected) | Alerts L1/L2/L3 | False alerts |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for vid, tr in sorted(ok.items()):
        lb = labels.get(vid, {})
        runs = label_runs(lb, gap)
        ev = defaultdict(list)
        for f, e in tr["events"]:
            ev[e].append(f)
        ms = [r for r in runs if r.label == "microsleep" and r.seconds(fps) >= ms_min]
        yw = [r for r in runs if r.label == "yawning"]
        lv = Counter(a[1] for a in tr["alerts"])
        fa = sum(1 for a in alert_rows if a[0] == vid and a[4] == "fp")
        lines.append(
            f"| {vid} | {tr['n'] / fps / 60:.1f} | {_p(np.nanmean(tr['cols']['face']))} | "
            f"{len(ms)} ({sum(detected(r, ev['microsleep'], tol) is not None for r in ms)}) | "
            f"{len(yw)} ({sum(detected(r, ev['yawn'], tol) is not None for r in yw)}) | "
            f"{lv[1]}/{lv[2]}/{lv[3]} | {fa} |"
        )
    fa_list = [a for a in alert_rows if a[4] == "fp"]
    if fa_list:
        lines += [
            "",
            "False alerts (video, time, level, reasons): "
            + "; ".join(f"{v} {t:.1f}s L{lv} {r}" for v, t, lv, r, _ in fa_list)
            + ".",
        ]
    return "\n".join(lines) + "\n"


def sust_features(tr: dict, thresholds: dict[str, Any]) -> dict[str, float]:
    """Clip-level numbers from one trace."""
    c = tr["cols"]
    fps = tr["fps"]
    ev = Counter(e for _, e in tr["events"])
    base_init = float(thresholds["drowsiness"]["eye"]["baseline_init"])
    measured = ~np.isnan(c["ear"]) & (c["reliable"] == 1)
    ear = c["ear"][measured]
    # clip-own baseline: 90th percentile of the clip's EAR (what block 7 would learn after 10 s)
    own_base = float(np.percentile(ear, 90)) if len(ear) >= fps else np.nan
    pc = c["p_cnn"][~np.isnan(c["p_cnn"])]
    mar = c["mar"][~np.isnan(c["mar"])]
    pitch = c["pitch"][measured]
    ec = c["eye_closed"][~np.isnan(c["eye_closed"])]
    return {
        "face_rate": float(np.mean(c["face"])),
        "reliable_rate": float(np.mean(c["reliable"])),
        "any_alert": float(len(tr["alerts"]) > 0),
        "max_level": float(np.max(c["level"])) if tr["n"] else 0.0,
        "max_drowsy_score": float(np.max(c["drowsy_score"])) if tr["n"] else 0.0,
        "microsleep_events": float(ev["microsleep"]),
        "yawn_events": float(ev["yawn"]),
        "nod_events": float(ev["nod"]),
        "blinks_per_min": ev["blink"] / (tr["n"] / fps) * 60 if tr["n"] else np.nan,
        "max_closed_duration": float(np.max(c["closed_duration"])) if tr["n"] else 0.0,
        "closed_frac_block7": float(np.mean(ec == 1)) if len(ec) else np.nan,
        "perclos_init_base": float(np.mean(ear < 0.65 * base_init)) if len(ear) else np.nan,
        "perclos_own_base": float(np.mean(ear < 0.65 * own_base)) if len(ear) and not np.isnan(own_base) else np.nan,
        "ear_mean": float(np.mean(ear)) if len(ear) else np.nan,
        "ear_p10": float(np.percentile(ear, 10)) if len(ear) else np.nan,
        "cnn_closed_frac": float(np.mean(pc >= 0.6)) if len(pc) else np.nan,
        "cnn_mean": float(np.mean(pc)) if len(pc) else np.nan,
        "mar_max": float(np.max(mar)) if len(mar) else np.nan,
        "mar_open_frac": float(np.mean(mar >= float(thresholds["drowsiness"]["yawn"]["mar_open"])))
        if len(mar)
        else np.nan,
        "pitch_std": float(np.std(pitch)) if len(pitch) > 1 else np.nan,
        "pitch_range": float(np.percentile(pitch, 95) - np.percentile(pitch, 5)) if len(pitch) > 1 else np.nan,
        "off_road_frac": float(np.mean(c["off_road"] == 1)),
        **blink_features(c),
    }


def blink_features(c: dict[str, np.ndarray]) -> dict[str, float]:
    """MediaPipe eyeBlink blendshape per clip (traces made with blendshapes on)."""
    b = c["blink"][~np.isnan(c["blink"])] if "blink" in c else np.array([])
    if len(b) == 0:
        return {}
    return {"blink_mean": float(np.mean(b)), "blink_closed_frac": float(np.mean(b >= 0.5))}


FEATURE_NOTES = {
    "any_alert": "system decision: any alert L1-L3",
    "max_level": "highest risk level in the clip",
    "max_drowsy_score": "block 9 drowsy_score",
    "microsleep_events": "block 7 events",
    "yawn_events": "block 7 events",
    "nod_events": "block 7 events",
    "blinks_per_min": "block 7 blink events / clip length",
    "max_closed_duration": "block 7 closed_duration",
    "closed_frac_block7": "block 7 eye_closed (short-window PERCLOS)",
    "perclos_init_base": "EAR < 0.65 x baseline_init (what block 7 uses in the first 10 s)",
    "perclos_own_base": "EAR < 0.65 x the clip's own p90 EAR",
    "ear_mean": "lower = more closed",
    "ear_p10": "lower = more closed",
    "cnn_closed_frac": "block 5 CNN p ≥ 0.6, every frame",
    "cnn_mean": "block 5 CNN mean p_closed",
    "mar_max": "block 6",
    "mar_open_frac": "MAR ≥ yawn.mar_open",
    "pitch_std": "head motion (nodding)",
    "pitch_range": "p95 - p5 pitch",
    "off_road_frac": "block 8 off_road",
    "face_rate": "block 3",
    "reliable_rate": "face_conf ≥ min_face_conf",
    "blink_mean": "block 3 MediaPipe eyeBlink, mean",
    "blink_closed_frac": "eyeBlink ≥ 0.5 (short-window PERCLOS, no baseline needed)",
}
LOWER_IS_DROWSY = {"ear_mean", "ear_p10"}


def sust_report(traces: dict, thresholds: dict[str, Any]) -> str:
    ok = {k: v for k, v in traces.items() if not isinstance(v, str) and v["n"] > 0}
    failed = [k for k, v in traces.items() if isinstance(v, str) or v["n"] == 0]
    feats = {k: sust_features(v, thresholds) for k, v in ok.items()}
    y = np.array([k.startswith("drowsiness/") for k in feats])
    names = list(next(iter(feats.values())))
    feat = {n: np.array([feats[k][n] for k in feats]) for n in names}
    hours_neg = sum(ok[k]["n"] / ok[k]["fps"] for k in feats if not k.startswith("drowsiness/")) / 3600
    hours_pos = sum(ok[k]["n"] / ok[k]["fps"] for k in feats if k.startswith("drowsiness/")) / 3600
    lines = [
        "# DriverGuard - evaluation on SUST-DDD (clip labels)",
        "",
        f"{len(ok)} clips of ~10 s ({y.sum()} drowsy, {(~y).sum()} not drowsy; {hours_pos * 60:.0f} + {hours_neg * 60:.0f} min), "
        "phone camera in the driver's own car, portrait 720x1280. Full pipeline (blocks 2-12, YOLO on, simulated "
        "60 km/h), fresh state per clip."
        + (f" {len(failed)} clips could not be read: {', '.join(failed[:10])}." if failed else ""),
        "",
        "Every clip is shorter than `drowsiness.perclos_min_coverage_s` (30 s) and `eye.baseline_min_data_s` (10 s): "
        "the PERCLOS term and the driver's own EAR baseline never start. The system can only alert on microsleep "
        "(closed_duration), nods, yawns there. The clip-level signals below show what a short window could use.",
        "",
        "## 1. System decision per clip",
        "",
        "| Rule | Drowsy clips flagged (recall) | Not-drowsy clips flagged (FPR) | Precision | Alerts / hour on not-drowsy clips (95% CI) |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, pred in [
        ("any alert L1-L3", feat["any_alert"] > 0),
        ("L2 or L3 reached", feat["max_level"] >= 2),
        ("L3 reached", feat["max_level"] >= 3),
        ("any microsleep event", feat["microsleep_events"] > 0),
        ("any yawn event", feat["yawn_events"] > 0),
        ("any nod event", feat["nod_events"] > 0),
    ]:
        m = prf(pred, y)
        n_alerts = sum(len(ok[k]["alerts"]) for k in feats if not k.startswith("drowsiness/"))
        per_h = ci_text(rate_ci(n_alerts, hours_neg)) if name.startswith("any alert") and hours_neg else ""
        lines.append(f"| {name} | {_p(m['recall'])} | {_p(m['fpr'])} | {_p(m['precision'])} | {per_h} |")
    reasons = Counter()
    for k in feats:
        for _, lv, rs in ok[k]["alerts"]:
            for r in rs:
                reasons[("drowsy" if k.startswith("drowsiness/") else "not_drowsy", f"L{lv} {r}")] += 1
    lines += [
        "",
        "Alerts by clip class and reason: " + ", ".join(f"{c}: {r} {n}" for (c, r), n in sorted(reasons.items())) + ".",
        "",
        f"Alerts on not-drowsy clips by reason and level ({hours_neg:.2f} h of clips, exact Poisson 95 % CI; "
        "the same driver's clips are not independent, so the CI is optimistic):",
        "",
        "| Reason | Level | Alerts | Per hour (95% CI) |",
        "|---|---:|---:|---:|",
    ]
    for (c, rl), n in sorted(reasons.items()):
        if c == "not_drowsy":
            lv, r = rl.split(" ", 1)
            lines.append(f"| {r} | {lv} | {n} | {ci_text(rate_ci(n, hours_neg))} |")
    lines += [
        "",
        "FAR / MAR on windows: not computed. Every clip (~10 s) is shorter than the start-up stretch the windows "
        "leave out (`eval.warmup_s`).",
    ]
    lines += [
        "",
        "## 2. How well each clip-level signal separates drowsy from not-drowsy clips",
        "",
        "AUC 0.5 = no information, 1.0 = perfect; oriented so that higher = drowsier (EAR: lower). "
        "Medians per class show the direction.",
        "",
        "| Signal | AUC | Median drowsy | Median not drowsy | Meaning |",
        "|---|---:|---:|---:|---|",
    ]
    rows = []
    for n in names:
        s = -feat[n] if n in LOWER_IS_DROWSY else feat[n]
        rows.append((auc(s[y], s[~y]), n))
    for a, n in sorted(rows, key=lambda r: -(r[0] or 0)):
        lines.append(
            f"| {n} | {_f(a, 3)} | {_f(float(np.nanmedian(feat[n][y])), 3)} | {_f(float(np.nanmedian(feat[n][~y])), 3)} | {FEATURE_NOTES.get(n, '')} |"
        )
    lines += [
        "",
        "## 3. Face measurability",
        "",
        f"- Face found on {_p(float(np.mean(feat['face_rate'])))} of frames; reliable (face_conf ≥ "
        f"{thresholds['features']['min_face_conf']}) on {_p(float(np.mean(feat['reliable_rate'])))}.",
        f"- Clips with a face on < 50 % of frames: {int(np.sum(feat['face_rate'] < 0.5))}; reliable on < 50 %: "
        f"{int(np.sum(feat['reliable_rate'] < 0.5))}.",
    ]
    return "\n".join(lines) + "\n"


def yawdd_report(traces: dict, thresholds: dict[str, Any]) -> str:
    """YawDD from traces, scored like tools/dataset.py + tools/eval.py (clip labels: a Yawning clip
    is one yawn episode covering the clip), plus FAR / MAR windows from the per-frame branch levels."""
    from tools import eval as ev
    from tools.dataset import label_of, load_presets

    preset = load_presets()["yawdd"]
    predictions: list = []
    durations: dict[str, float] = {}
    levels: dict[str, dict[str, list[int]]] = {}
    episodes = []
    for key, tr in sorted(traces.items()):
        if isinstance(tr, str) or tr["n"] == 0:
            continue
        lab = label_of(YAWDD_ROOT / key, YAWDD_ROOT.parent, preset)
        if lab is None:
            continue
        fps, c = tr["fps"], tr["cols"]
        dur = tr["n"] / fps
        durations[key] = dur
        if lab[0] == preset.positive:
            episodes.append(ev.Episode(key, "yawn", 0.0, round(dur, 3)))
        for i, e in tr["events"]:
            if e in ev.EVENT_TO_BEHAVIOR:
                predictions.append(ev.Prediction(key, ev.EVENT_TO_BEHAVIOR[e], i / fps))
        for i, lv, reasons in tr["alerts"]:
            predictions.append(ev.Prediction(key, ev.ALERT, i / fps, lv))
            for b in {ev.REASON_TO_BEHAVIOR[r] for r in reasons if r in ev.REASON_TO_BEHAVIOR}:
                predictions.append(ev.Prediction(key, b, i / fps, lv))
        levels[key] = {
            branch: per_second_max(c["t"], [int(v) for v in np.nan_to_num(c.get(f"{branch}_level", c["level"]))], dur)
            for branch in ("drowsy", "distraction")
        }
    cfg = EvalConfig.from_dict(thresholds.get("eval"))
    windows = ev.window_rows(episodes, durations, levels, cfg, tolerance_s=0.0)
    text = ev.report(ev.score(episodes, predictions, durations, tolerance_s=0.0), durations, 0.0, windows, cfg)
    return (
        f"Dataset: {preset.kaggle} ({preset.name}), clip-level labels, scored from traces "
        "(tools/seq_eval.py yawdd).\n\n" + text + "\nYawning clips count as drowsy windows (YawDD has no other "
        "drowsiness label); a car parked, no distraction label, so distraction windows are all awake.\n"
    )


# --------------------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    tr = sub.add_parser("trace", help="run the pipeline on every video and save per-frame traces")
    tr.add_argument("dataset", choices=("fl3d", "sust", "yawdd"))
    tr.add_argument("--out", required=True)
    tr.add_argument("--workers", type=int, default=4)
    tr.add_argument("--speed", type=float, default=60.0)
    tr.add_argument("--no-phone", action="store_true")
    tr.add_argument("--limit", type=int, default=None, help="sust: at most this many clips per class")
    tr.add_argument(
        "--set", action="append", default=[], help="what-if threshold, e.g. eye_state.low_light_brightness=0"
    )
    for name in ("fl3d", "sust", "yawdd"):
        s = sub.add_parser(name, help=f"score {name} traces")
        s.add_argument("--traces", required=True)
        s.add_argument("--out", default=None)
        s.add_argument(
            "--replay",
            choices=("trace", "ear", "cnn", "block5"),
            default=None,
            help="re-run blocks 7-12 on the traced features first: p_closed as traced / never (EAR only) / CNN always",
        )
        s.add_argument(
            "--set", action="append", default=[], help="what-if threshold, e.g. drowsiness.eye.cnn_closed=0.5"
        )
        s.add_argument("--workers", type=int, default=8)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = p.parse_args(argv)
    if args.cmd == "trace":
        run_traces(args.dataset, args.out, args.workers, args.speed, not args.no_phone, args.limit, args.set)
        return 0
    from edge_agent.config import load_thresholds

    thresholds = load_thresholds()
    for a in args.set:
        set_threshold(thresholds, a)
    traces = pickle.loads(Path(args.traces).read_bytes())
    if args.replay or args.set:
        traces = replay_all(traces, thresholds, args.replay or "trace", args.workers)
    text = {"fl3d": fl3d_report, "sust": sust_report, "yawdd": yawdd_report}[args.cmd](traces, thresholds)
    if args.replay or args.set:
        note = f"Blocks {'5, ' if args.replay == 'block5' else ''}7-12 replayed from the traces with config/thresholds.yaml"
        note += f" and {', '.join(args.set)}." if args.set else "."
        head, _, rest = text.partition("\n\n")
        text = f"{head}\n\n{note}\n\n{rest}"
    print(text)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
