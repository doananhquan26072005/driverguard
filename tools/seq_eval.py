"""M7 - Evaluate DriverGuard on frame-labelled and clip-labelled driving videos.

Two datasets that tools/dataset.py cannot score as they are:

- FL3D (Kaggle matjazmuc/frame-level-driver-drowsiness-detection-fl3d): one label per frame
  (alert / microsleep / yawning) for 44 NITYMED night-driving videos (Kaggle
  nikospetrellis/nitymed, 25 FPS). FL3D ships face crops; here the full pipeline runs on the
  original NITYMED videos (what the camera really sees) and the frame labels are matched by
  frame index.
- SUST-DDD (Sivas University, 2074 phone-camera clips of 10 s, real driving): one label per
  clip, drowsy (d_*.mp4) or not (n_*.mp4).

Step 1 `trace` runs blocks 2-12 on every video (fresh state per video, every frame, time = the
container's timestamp of the frame, see VideoClock) and keeps one row of numbers per frame (EAR, MAR, pose, eye state, PERCLOS,
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
import math
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
from edge_agent.perception.features import IRIS, iris_offsets  # noqa: E402, F401 (tools import them from here)
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
    # M39 (own recordings; traces made before it lack these). Block 4: phone flag, kind, best box.
    " roll phone_flag phone_kind phone_score phone_x1 phone_y1 phone_x2 phone_y2"
    " face_x1 face_y1 face_x2 face_y2"  # face box the driver zone was built on (pixels of the 640-wide image)
    " off_road_s phone_ratio off_road_ratio glance_count turned_away unavailable distraction_score"  # blocks 8, 9
    # Where the eyes look and how open the mouth is (MediaPipe blendshapes, 0..1), per eye.
    " look_down_l look_down_r look_up_l look_up_r look_in_l look_in_r look_out_l look_out_r jaw_open mouth_close"
    " iris_x_l iris_y_l iris_x_r iris_y_r"  # iris centre against the eye corners (iris_offsets)
    " perclos_p80 perclos_p80_s"  # M40: PERCLOS by the P80 definition and its eye-data coverage (measured only)
    " scene_bright scene_contrast sharpness"  # M43: frame quality numbers (traces made before it lack them)
    " gaze_down_deg gaze_down_s"  # block 8: gaze-down angle and how long it has stayed down (measured only)
).split()
PHONE_KIND_CODES = {"unknown": 0.0, "call": 1.0, "text": 2.0}  # phone_kind column; NaN = no phone
PHONE_KIND_NAMES = {v: k for k, v in PHONE_KIND_CODES.items()}
BLENDSHAPE_COLUMNS = {
    "look_down_l": "eyeLookDownLeft",
    "look_down_r": "eyeLookDownRight",
    "look_up_l": "eyeLookUpLeft",
    "look_up_r": "eyeLookUpRight",
    "look_in_l": "eyeLookInLeft",
    "look_in_r": "eyeLookInRight",
    "look_out_l": "eyeLookOutLeft",
    "look_out_r": "eyeLookOutRight",
    "jaw_open": "jawOpen",
    "mouth_close": "mouthClose",
}
# --------------------------------------------------------------------------- tracing (models)


class Tracer:
    """Blocks 2-12 frame by frame (same wiring as tools/eval.py), keeping one row of numbers per frame.

    Used on video files (`trace_video`: time from VideoClock, YOLO every `yolo_every` frames)
    and on a live camera (tools/record_trace.py: the caller's clock, YOLO at phone.target_fps).
    Only numbers are kept: the image given to `step` is not stored.
    """

    def __init__(
        self,
        thresholds: dict[str, Any],
        speed_kmh: float | None = None,
        use_phone: bool = True,
        yolo_every: int | None = None,
    ) -> None:
        from edge_agent.decision.pipeline import DecisionPipeline
        from edge_agent.perception import PreprocessConfig, Preprocessor
        from edge_agent.perception.eye_state import EyeStateConfig, EyeStateEstimator, make_estimator
        from edge_agent.perception.features import FeatureConfig, FeatureExtractor
        from edge_agent.perception.landmarks import FaceLandmarkDetector, LandmarkConfig
        from edge_agent.perception.phone_detector import FaceBoxMemory, PhoneDetectorConfig, YoloPhoneModel

        self.preprocessor = Preprocessor(PreprocessConfig.from_dict(thresholds.get("preprocess")))
        self.extractor = FeatureExtractor(FeatureConfig.from_dict(thresholds.get("features")))
        eye_cfg = EyeStateConfig.from_dict(thresholds.get("eye_state"))
        self.eye_state = make_estimator(eye_cfg)
        self.eye_diag = EyeStateEstimator(replace(eye_cfg, enabled=True, always_run=True, source="cnn"))
        self.phone_cfg = replace(PhoneDetectorConfig.from_dict(thresholds.get("phone")), num_threads=1)
        self.yolo = YoloPhoneModel(self.phone_cfg) if use_phone else None
        self.yolo_every = yolo_every
        self.pipeline = DecisionPipeline(thresholds)
        self.can = replay_vehicle(thresholds, speed_kmh)
        self.landmarks = FaceLandmarkDetector(LandmarkConfig.from_dict(thresholds.get("landmarks")))
        self.face_memory = FaceBoxMemory(self.phone_cfg.face_memory_s)
        self.detections: tuple = ()
        self.last_yolo_t = -1e9
        self.rows: list[tuple] = []
        self.events: list[tuple[int, str]] = []
        self.alerts: list[tuple[int, int, tuple[str, ...]]] = []

    def close(self) -> None:
        """Release the landmark model."""
        self.landmarks.close()

    def __enter__(self) -> Tracer:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _yolo_due(self, i: int, t: float) -> bool:
        if self.yolo_every is not None:
            return i % self.yolo_every == 0
        return self.phone_cfg.target_fps > 0 and t - self.last_yolo_t >= 1.0 / self.phone_cfg.target_fps

    def step(self, image: np.ndarray, i: int, t: float) -> Any:
        """One frame at time t (seconds from the start). Returns the frame's DecisionResult."""
        from edge_agent.capture import Frame
        from edge_agent.perception import quality
        from edge_agent.perception.eye_state import face_brightness
        from edge_agent.perception.phone_detector import face_bbox, phone_kind, phone_near_face

        pre = self.preprocessor(Frame(image=image, frame_id=i, timestamp=t))
        lm = self.landmarks.detect(pre)
        if self.yolo is not None and self._yolo_due(i, t):
            self.detections, self.last_yolo_t = self.yolo(pre.image), t
        phone_flag = held = None
        face = self.face_memory.update(face_bbox(lm.points) if lm else None, t)
        if self.yolo is not None and t - self.last_yolo_t <= self.phone_cfg.max_result_age_s:
            phone_flag = phone_near_face(self.detections, face, self.phone_cfg)
            held = phone_kind(self.detections, face, self.phone_cfg)
        feats = self.extractor(lm, i, t)
        feats = replace(feats, **quality.measure(pre, lm, self.preprocessor.config.sample_stride))
        diag = self.eye_diag.estimate(pre, lm, feats)
        if self.eye_state is not None:
            feats = self.eye_state(pre, lm, feats)
        r = self.pipeline.step(feats, phone_flag, self.can.sample(t), held)
        d, x = r.drowsiness, r.distraction
        best = self.detections[0] if self.detections and phone_flag is not None else None
        phone_box = (None,) * 4 if best is None else best.bbox
        face_box = (None,) * 4 if face is None else face
        shapes = (lm.blendshapes or {}) if lm is not None else {}
        iris = iris_offsets(lm.points) if lm is not None else {}
        row = {
            "t": t,
            "face": feats.face_found,
            "reliable": feats.face_reliable,
            "ear": feats.ear,
            "ear_base": d.ear_open_baseline,
            "mar": feats.mar,
            "pitch": feats.pitch,
            "yaw": feats.yaw,
            "p_closed": feats.p_closed,
            "p_cnn": None if diag is None else diag.p_closed,
            "eye_closed": None if d.eye_closed is None else int(d.eye_closed),
            "closed_duration": d.closed_duration,
            "perclos": d.perclos_60s,
            "perclos_ready": d.perclos_ready,
            "yawning": d.yawning,
            "masked": d.closure_masked,
            "off_road": x.off_road,
            "no_face_s": x.no_face_duration,
            "level": r.risk.level,
            "drowsy_score": r.risk.drowsy_score,
            "ear_l": feats.ear_left,
            "ear_r": feats.ear_right,
            "face_bright": face_brightness(pre, lm) if lm is not None else None,
            "is_ir": pre.is_ir,
            "blink": feats.eye_blink,
            "brow": feats.brow_up,
            "roll": feats.roll,
            "phone_flag": phone_flag,
            "phone_kind": None if x.phone_kind is None else PHONE_KIND_CODES[x.phone_kind],
            "phone_score": None if best is None else best.score,
            **dict(zip(("phone_x1", "phone_y1", "phone_x2", "phone_y2"), phone_box, strict=True)),
            **dict(zip(("face_x1", "face_y1", "face_x2", "face_y2"), face_box, strict=True)),
            "off_road_s": x.off_road_duration,
            "phone_ratio": x.phone_ratio_2s,
            "off_road_ratio": x.off_road_ratio,
            "glance_count": x.glance_count,
            "turned_away": x.turned_away,
            "unavailable": r.risk.unavailable,
            "distraction_score": r.risk.distraction_score,
            **{col: shapes.get(name) for col, name in BLENDSHAPE_COLUMNS.items()},
            **{col: iris.get(col) for col in ("iris_x_l", "iris_y_l", "iris_x_r", "iris_y_r")},
            "perclos_p80": d.perclos_p80_60s,
            "perclos_p80_s": d.perclos_p80_coverage_s,
            "scene_bright": feats.scene_brightness,
            "scene_contrast": feats.scene_contrast,
            "sharpness": feats.sharpness,
            "gaze_down_deg": x.gaze_down_deg,
            "gaze_down_s": x.gaze_down_duration,
        }
        self.rows.append(tuple(row[c] for c in COLUMNS))
        self.events += [(i, ev) for ev in d.events]
        if r.alert.new_alert is not None:
            self.alerts.append((i, r.alert.new_alert.level, tuple(r.alert.new_alert.reasons)))
        return r

    def result(self, fps: float, clock: VideoClock | None = None) -> dict:
        """The trace: per-frame columns (NaN = not measured), events and alerts by frame index.

        `meta` says what made it (tools/metrics.py environment). clock: the VideoClock of a video file;
        the trace then also carries `clock` (where its times come from) and `duration_s`."""
        from tools.metrics import environment

        cols = {name: np.full(0, np.nan) for name in COLUMNS}
        if self.rows:
            cols = {
                name: np.array([np.nan if v is None else float(v) for v in col])
                for name, col in zip(COLUMNS, zip(*self.rows))
            }
        tr = {"fps": fps, "n": len(self.rows), "cols": cols, "events": self.events, "alerts": self.alerts}
        tr["meta"] = environment()
        if clock is not None:
            tr["clock"] = clock.summary()
            tr["duration_s"] = clock.duration_s
        return tr


class VideoClock:
    """Time of each frame of a video file, in seconds from its first frame.

    The time is the container's timestamp of the frame (OpenCV CAP_PROP_POS_MSEC read after the frame),
    so a video recorded at a varying frame rate keeps its real timing. frame index / fps is only right
    at a constant rate, and every time rule (eyes shut 1.5 s, PERCLOS over 60 s) and the hours behind
    a false-alarm rate are measured on this clock. A timestamp that is missing or does not move forward
    is replaced by one nominal frame after the previous time, and counted."""

    def __init__(self, fps: float) -> None:
        self.fps = fps
        self.frames = 0
        self.patched = 0  # frames whose timestamp could not be used
        self.offset_max = 0.0  # largest |time - frame index / fps| of any frame so far
        self._first_ms: float | None = None
        self._last = 0.0

    def time(self, pos_msec: float | None) -> float:
        usable = pos_msec is not None and math.isfinite(pos_msec)
        if self.frames == 0:
            self._first_ms = pos_msec if usable else None
            t = 0.0
        else:
            t = (pos_msec - self._first_ms) / 1000.0 if usable and self._first_ms is not None else -1.0
            if t <= self._last:
                t = self._last + 1.0 / self.fps
                self.patched += 1
        self.offset_max = max(self.offset_max, abs(t - self.frames / self.fps))
        self.frames += 1
        self._last = t
        return t

    @property
    def duration_s(self) -> float:
        """From the first frame to the end of the last one (shown for one nominal frame)."""
        return self._last + 1.0 / self.fps if self.frames else 0.0

    def summary(self) -> dict[str, Any]:
        """Where the times of a trace come from, and how far they are from frame index / fps."""
        by_index = self.frames / self.fps
        return {
            "source": "container" if self._first_ms is not None and self.patched < self.frames - 1 else "index",
            "patched_frames": self.patched,
            "duration_s": round(self.duration_s, 3),
            "index_duration_s": round(by_index, 3),
            "drift_s": round(self.duration_s - by_index, 3),
            "offset_max_s": round(self.offset_max, 3),
        }


def trace_seconds(tr: dict) -> float:
    """Length of a trace in seconds: what its clock measured when it has one (`duration_s`), else
    frames / fps (traces made before the clock, live recordings, traces with frames left out)."""
    if tr.get("duration_s") is not None:
        return float(tr["duration_s"])
    return tr["n"] / tr["fps"] if tr["n"] else 0.0


def frame_seconds(tr: dict, frame: int) -> float:
    """Time of a frame index on the trace's clock. One past the last frame is the end of the trace
    (labels given as frame ranges end there); beyond that the nominal rate carries on."""
    n = tr["n"]
    if 0 <= frame < n:
        return float(tr["cols"]["t"][frame])
    return trace_seconds(tr) + (frame - n) / tr["fps"]


def gap_stats(times: np.ndarray, fps: float, long_gap: float) -> dict[str, float]:
    """How even the frame times (seconds) are against the nominal rate. long_gap: a wait of this many
    nominal frames or more is counted as a long one (eval.clock_long_gap_frames)."""
    n = len(times)
    out = {"frames": n, "fps": round(fps, 3), "index_s": round(n / fps, 2) if fps > 0 else float("nan")}
    if n < 2 or fps <= 0:
        return out | {"clock_s": float("nan"), "drift_s": float("nan"), "offset_max_s": float("nan"), "long_gaps": 0}
    gaps = np.diff(times)
    clock_s = float(times[-1] - times[0]) + 1.0 / fps
    # The container FPS is an average, so the two clocks can agree at the end and still be seconds apart
    # in between (a stretch without frames): offset_max_s is the largest distance at any frame.
    offset = (times - times[0]) - np.arange(n) / fps
    return out | {
        "clock_s": round(clock_s, 2),
        "drift_s": round(clock_s - n / fps, 2),
        "offset_max_s": round(float(np.abs(offset).max()), 2),
        "gap_p50_ms": round(float(np.percentile(gaps, 50)) * 1000, 1),
        "gap_p95_ms": round(float(np.percentile(gaps, 95)) * 1000, 1),
        "gap_max_ms": round(float(gaps.max()) * 1000, 1),
        "long_gaps": int(np.sum(gaps >= long_gap / fps)),
    }


def video_clock(path: Path, thresholds: dict[str, Any]) -> dict[str, float]:
    """gap_stats of one video file. Frames are stepped through without running any model and no image
    is kept, so a 10-minute video takes seconds."""
    import cv2

    cfg = EvalConfig.from_dict(thresholds.get("eval"))
    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            raise RuntimeError(f"cannot open {path}")
        fps = cap.get(cv2.CAP_PROP_FPS)
        fps = fps if 0 < fps < 1000 else cfg.fallback_video_fps
        clock = VideoClock(fps)
        times = []
        while cap.grab():
            times.append(clock.time(cap.get(cv2.CAP_PROP_POS_MSEC)))
        return gap_stats(np.array(times), fps, cfg.clock_long_gap_frames) | {"patched": clock.patched}
    finally:
        cap.release()


def trace_video(path: Path, thresholds: dict[str, Any], speed_kmh: float | None = None, use_phone: bool = True) -> dict:
    """Blocks 2-12 on one video; per-frame numbers, events and alerts (same wiring as tools/eval.py)."""
    import cv2

    from edge_agent.perception.phone_detector import PhoneDetectorConfig

    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            raise RuntimeError(f"cannot open {path}")
        fps = cap.get(cv2.CAP_PROP_FPS)
        fps = fps if 0 < fps < 1000 else EvalConfig.from_dict(thresholds.get("eval")).fallback_video_fps
        yolo_every = max(1, round(fps / PhoneDetectorConfig.from_dict(thresholds.get("phone")).target_fps))
        clock = VideoClock(fps)
        with Tracer(thresholds, speed_kmh, use_phone, yolo_every) as tracer:
            i = 0
            while True:
                ok, image = cap.read()
                if not ok:
                    break
                tracer.step(image, i, clock.time(cap.get(cv2.CAP_PROP_POS_MSEC)))
                i += 1
            return tracer.result(fps, clock)
    finally:
        cap.release()


def _trace_job(args: tuple[str, str, dict[str, Any], float, bool]) -> tuple[str, dict | str]:
    key, path, thresholds, speed, use_phone = args
    try:
        return key, trace_video(Path(path), thresholds, speed, use_phone)
    except Exception as e:  # one broken clip must not stop a 2000-clip run
        return key, f"{type(e).__name__}: {e}"


def dataset_videos(name: str, limit: int | None = None) -> dict[str, Path]:
    """The videos of a dataset by key, at most `limit` of them."""
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
    """Trace every video of the dataset in parallel and save the traces to `out`."""
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


def replay_vehicle(thresholds: dict[str, Any], speed_kmh: float | None = None) -> Any:
    """The vehicle of a trace or replay: constant speed (None: eval.replay_speed_kmh), starting at
    eval.replay_clock_hour with eval.replay_drive_time_s already driven (noon and 0 by default: no
    night, no long drive)."""
    from edge_agent.context.can_sim import CanSimulator, Scenario, scenario_from_dict
    from tools.metrics import EvalConfig

    cfg = EvalConfig.from_dict(thresholds.get("eval"))
    speed_kmh = cfg.replay_speed_kmh if speed_kmh is None else speed_kmh
    base = scenario_from_dict({"timeline": [{"t": 0, "speed_kmh": speed_kmh}]})
    return CanSimulator(
        Scenario(
            base.name,
            base.keyframes,
            start_clock_s=(cfg.replay_clock_hour % 24.0) * 3600.0,
            initial_drive_time_s=cfg.replay_drive_time_s,
        )
    )


# --------------------------------------------------------------------------- what-if replay (blocks 7-12 only)


def replay(
    tr: dict,
    thresholds: dict[str, Any],
    eye: str = "trace",
    observe: Any = None,
    profile: dict[str, float] | None = None,
) -> dict:
    """Blocks 7-12 again on a trace's features, e.g. with other thresholds, without re-running the models.

    eye: which p_closed block 7 gets. "trace" = what the pipeline used (reproduces the run),
    "ear" = never the CNN (EAR only), "cnn" = the CNN on every frame, "block5" = block 5 decided
    again with `thresholds` (trigger + hold, score from eye_state.source; needs the raw columns
    of a trace made after the block 5 fix). The phone flag and kind come from the trace when it has
    them (made from M39 on); older traces have none, so no phone alert is replayed.
    observe: called as observe(i, pipeline, result) after every frame, for tools that need more than
    the returned columns (tools/blink_duration.py reads block 7's blink timings).
    profile: ear_open, mar_closed, road_yaw, road_pitch (and road_iris_y, block 8 only) handed to blocks
    7 and 8 before the first frame, as a finished driver enrollment does (tools/trace_studies.py personal).
    """
    from edge_agent.decision.pipeline import DecisionPipeline
    from edge_agent.perception.features import FrameFeatures

    c = tr["cols"]
    source = "cnn"  # the traces were made on the device path; "block5" follows eye_state.source
    if eye == "block5":
        source = (thresholds.get("eye_state") or {}).get("source", "cnn")
        pcol = block5_scores(c, thresholds)
    else:
        pcol = {"trace": c["p_closed"], "cnn": c["p_cnn"], "ear": np.full(tr["n"], np.nan)}[eye]
    blink = c.get("blink", np.full(tr["n"], np.nan))
    brow = c.get("brow", np.full(tr["n"], np.nan))
    phone = c.get("phone_flag", np.full(tr["n"], np.nan))
    kind = c.get("phone_kind", np.full(tr["n"], np.nan))
    # Frame quality numbers (M43): NaN = not measured, which is never an issue.
    q = {k: c.get(k, np.full(tr["n"], np.nan)) for k in ("face_bright", "scene_bright", "scene_contrast", "sharpness")}
    iris_y = (c["iris_y_l"] + c["iris_y_r"]) / 2.0 if "iris_y_l" in c else np.full(tr["n"], np.nan)
    pipeline = DecisionPipeline(thresholds)
    if profile is not None:
        pipeline.drowsiness.set_profile(**{k: v for k, v in profile.items() if k != "road_iris_y"})
        pipeline.distraction.set_road_pose(profile["road_yaw"], profile["road_pitch"], profile.get("road_iris_y"))
    can = replay_vehicle(thresholds)
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
            "off_road",
            "off_road_s",
            "off_road_ratio",
            "glance_count",
            "turned_away",
            "unavailable",
            "perclos",
            "perclos_ready",
            "perclos_s",  # eye-data seconds in the PERCLOS window
            "perclos_p80",
            "perclos_p80_s",
            "ear_base",
            "gaze_down_deg",
            "gaze_down_s",
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
            p_closed_source=source if face and not np.isnan(pcol[i]) else None,
            face_brightness=val(q["face_bright"][i]) if face else None,
            scene_brightness=val(q["scene_bright"][i]),
            scene_contrast=val(q["scene_contrast"][i]),
            sharpness=val(q["sharpness"][i]),
            iris_y=val(iris_y[i]) if face else None,
        )
        flag = None if np.isnan(phone[i]) else bool(phone[i])
        r = pipeline.step(f, flag, can.sample(f.timestamp), None if np.isnan(kind[i]) else PHONE_KIND_NAMES[kind[i]])
        d, x = r.drowsiness, r.distraction
        out["off_road"][i] = x.off_road
        out["off_road_s"][i] = x.off_road_duration
        out["off_road_ratio"][i] = x.off_road_ratio
        out["glance_count"][i] = x.glance_count
        out["turned_away"][i] = x.turned_away
        out["gaze_down_deg"][i] = np.nan if x.gaze_down_deg is None else x.gaze_down_deg
        out["gaze_down_s"][i] = x.gaze_down_duration
        out["unavailable"][i] = r.risk.unavailable
        out["perclos"][i] = d.perclos_60s
        out["perclos_ready"][i] = d.perclos_ready
        out["perclos_s"][i] = d.perclos_coverage_s
        out["perclos_p80"][i] = d.perclos_p80_60s
        out["perclos_p80_s"][i] = d.perclos_p80_coverage_s
        out["ear_base"][i] = d.ear_open_baseline
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


def resample_trace(tr: dict, fps: float, jitter_cv: float = 0.0, offset_s: float = 0.0, seed: int = 0) -> dict:
    """The trace as a slower loop would have seen it: fewer frames, each with the time it was taken.

    The loop asks for a frame every 1 / fps seconds from offset_s on and gets the first traced frame at or
    after that moment (a frame is never used twice). jitter_cv > 0 makes the waits uneven: log-normal with
    mean 1 / fps and this coefficient of variation, drawn from `seed`. Nothing is interpolated, so a trace
    cannot be made faster than it was recorded. The result replays like any trace: `fps` is the rate it
    reached (frames / duration, so n / fps is still the duration), `source_fps` the rate of the recording.
    Events and alerts of the original run move to the nearest kept frame."""
    c, n = tr["cols"], tr["n"]
    if n == 0 or fps <= 0:
        return tr
    t = c["t"]
    if jitter_cv > 0:
        sigma2 = math.log(1.0 + jitter_cv**2)
        count = int((t[-1] - offset_s) * fps * 1.5) + 16  # more waits than can fit
        waits = np.random.default_rng(seed).lognormal(-math.log(fps) - sigma2 / 2.0, math.sqrt(sigma2), count)
        asked = offset_s + np.concatenate(([0.0], np.cumsum(waits)))
    else:
        asked = offset_s + np.arange(int((t[-1] - offset_s) * fps) + 1) / fps
    idx = np.unique(np.searchsorted(t, asked - 1e-9))
    idx = idx[idx < n]

    def moved(rows: list[tuple]) -> list[tuple]:
        return [(int(min(np.searchsorted(idx, r[0]), len(idx) - 1)), *r[1:]) for r in rows]

    return {
        **tr,
        "fps": len(idx) * tr["fps"] / n,
        "source_fps": tr["fps"],
        "n": len(idx),
        "cols": {k: v[idx] for k, v in c.items()},
        "events": moved(tr["events"]),
        "alerts": moved(tr["alerts"]),
    }


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
    """Replay blocks 7-12 on every usable trace in parallel; results by video."""
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
    """Precision, recall, F1 and the confusion counts of boolean predictions against the truth."""
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
        """Length of the run in seconds at this frame rate."""
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
    """The FL3D frame labels: {video: {frame: label}}."""
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
    """The Markdown report on FL3D (frame-labelled eye closure and microsleep)."""
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
    minutes = sum(trace_seconds(v) for v in ok.values()) / 60

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
        # Labels are frame ranges; windows and levels are on the trace's clock. Label lengths and
        # detection delays below stay in frames / nominal FPS (NITYMED is recorded at a constant 25).
        secs = lambda rs: [(frame_seconds(tr, r.start), frame_seconds(tr, r.end + 1)) for r in rs]  # noqa: B023, E731
        col = tr["cols"].get("drowsy_level", tr["cols"]["level"])  # traces scored without replay: any reason
        per_sec = per_second_max(tr["cols"]["t"], [int(v) for v in np.nan_to_num(col)], trace_seconds(tr))
        for lv in win_levels:
            lv_cfg = EvalConfig(eval_cfg.window_s, eval_cfg.warmup_s, eval_cfg.positive_frac, lv)
            awake = secs([r for r in runs if r.label == "alert"])
            windows[lv] += window_scores(trace_seconds(tr), secs(drowsy_runs), awake, per_sec, lv_cfg, tol_s)
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
            alert_rows.append((vid, frame_seconds(tr, f), lv, ",".join(reasons), kind))
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
            f"| {vid} | {trace_seconds(tr) / 60:.1f} | {_p(np.nanmean(tr['cols']['face']))} | "
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
        "blinks_per_min": ev["blink"] / trace_seconds(tr) * 60 if tr["n"] else np.nan,
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
    """The Markdown report on SUST (clip-labelled drowsiness)."""
    ok = {k: v for k, v in traces.items() if not isinstance(v, str) and v["n"] > 0}
    failed = [k for k, v in traces.items() if isinstance(v, str) or v["n"] == 0]
    feats = {k: sust_features(v, thresholds) for k, v in ok.items()}
    y = np.array([k.startswith("drowsiness/") for k in feats])
    names = list(next(iter(feats.values())))
    feat = {n: np.array([feats[k][n] for k in feats]) for n in names}
    hours_neg = sum(trace_seconds(ok[k]) for k in feats if not k.startswith("drowsiness/")) / 3600
    hours_pos = sum(trace_seconds(ok[k]) for k in feats if k.startswith("drowsiness/")) / 3600
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


def yawdd_meta(key: str) -> dict[str, str] | None:
    """ "Mirror/Male_mirror Avi Videos/13-MaleGlasses-Yawning.avi" -> subject, eyewear, action.

    subject = gender + number + eyewear: the same number with and without glasses may be one person
    or two (not checked), so they are kept apart."""
    m = re.fullmatch(r"(\d+)-(Female|Male)([A-Za-z]*)-([A-Za-z]+)", Path(key).stem)
    if m is None:
        return None
    number, gender, extra, action = m.groups()
    eyewear = "sunglasses" if "SunGlasses" in extra else ("no glasses" if "NoGlasses" in extra else "glasses")
    return {
        "subject": f"{gender[0]}{number}-{eyewear.replace(' ', '')}",
        "eyewear": eyewear,
        "action": "yawning" if "yawning" in action.lower() else action.lower(),  # normal | talking | yawning
    }


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
        c = tr["cols"]
        dur = trace_seconds(tr)
        durations[key] = dur
        if lab[0] == preset.positive:
            episodes.append(ev.Episode(key, "yawn", 0.0, round(dur, 3)))
        for i, e in tr["events"]:
            if e in ev.EVENT_TO_BEHAVIOR:
                predictions.append(ev.Prediction(key, ev.EVENT_TO_BEHAVIOR[e], frame_seconds(tr, i)))
        for i, lv, reasons in tr["alerts"]:
            predictions.append(ev.Prediction(key, ev.ALERT, frame_seconds(tr, i), lv))
            for b in {ev.REASON_TO_BEHAVIOR[r] for r in reasons if r in ev.REASON_TO_BEHAVIOR}:
                predictions.append(ev.Prediction(key, b, frame_seconds(tr, i), lv))
        levels[key] = {
            branch: per_second_max(c["t"], [int(v) for v in np.nan_to_num(c.get(f"{branch}_level", c["level"]))], dur)
            for branch in ("drowsy", "distraction")
        }
    cfg = EvalConfig.from_dict(thresholds.get("eval"))
    windows = ev.window_rows(episodes, durations, levels, cfg, tolerance_s=0.0)
    subjects = {k: m["subject"] for k in durations if (m := yawdd_meta(k)) is not None}
    people = ev.score_by_subject(episodes, predictions, durations, subjects, 0.0, levels, cfg)
    scores = ev.score(episodes, predictions, durations, tolerance_s=0.0, warmup_s=cfg.warmup_s)
    text = ev.report(scores, durations, 0.0, windows, cfg, people)
    return (
        f"Dataset: {preset.kaggle} ({preset.name}), clip-level labels, scored from traces "
        "(tools/seq_eval.py yawdd).\n\n" + text + "\nYawning clips count as drowsy windows (YawDD has no other "
        "drowsiness label); a car parked, no distraction label, so distraction windows are all awake.\n"
        "A person = gender + number + eyewear in the file name (the same number with and without glasses is kept "
        "apart: not checked whether it is one person).\n"
    )


# --------------------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point (see the module doc). Returns the process exit code."""
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    tr = sub.add_parser("trace", help="run the pipeline on every video and save per-frame traces")
    tr.add_argument("dataset", choices=("fl3d", "sust", "yawdd"))
    tr.add_argument("--out", required=True)
    tr.add_argument("--workers", type=int, default=4)
    tr.add_argument("--speed", type=float, default=None, help="km/h (default: eval.replay_speed_kmh)")
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
    from tools.metrics import environment_text, provenance

    notes = []
    if args.replay or args.set:
        note = f"Blocks {'5, ' if args.replay == 'block5' else ''}7-12 replayed from the traces with config/thresholds.yaml"
        note += f" and {', '.join(args.set)}." if args.set else "."
        notes.append(note)
    else:
        notes.append(
            "Alerts and levels AS TRACED, not replayed with today's config/thresholds.yaml (pass --replay block5 for that)."
        )
    made = environment_text(tr.get("meta") for tr in traces.values() if not isinstance(tr, str))
    notes.append(f"{provenance([args.traces])} {made}")
    head, _, rest = text.partition("\n\n")
    text = f"{head}\n\n" + "\n\n".join(notes) + f"\n\n{rest}"
    print(text)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
