"""Phone branch against how and when YOLO runs, on 3MDAD: 50 drivers in a real car, face camera.

    python tools/phone_study.py detect --out data/eval_traces/3mdad_phone.pkl
    python tools/phone_study.py detect --out ... --model 416=/tmp/yolov8n_416.onnx --model 320=...
    python tools/phone_study.py report --dets data/eval_traces/3mdad_phone.pkl --out eval/results/phone_web_3mdad.md

Why: the page (#/live) does not run YOLO on every frame. A frame uses the newest answer, which is
one inference + up to one period old (frontend/src/live/pace.ts). Changing how often YOLO runs, how
long a run takes or the model's input size changes which answer every frame sees, and so the
`phone` alert of blocks 8, 9, 12. The traces keep no image, so this cannot be replayed from them.

`detect` runs YOLO once on EVERY frame of the dataset (the plain 640-wide frame, as block 4 gets it
on the device and on the page) and keeps the phone boxes, numbers only. `report` then plays any
schedule on those boxes: which frame would have been given to the detector, when its answer would
have been back, what each frame would have seen; blocks 7-12 are replayed on the existing trace
(data/eval_traces/3mdad_day.pkl, tools/gaze_study.py) with that phone flag, and the alerts are
counted against the action labels. Messages and calls (AC5-AC8) are the positives. "Taking a picture"
(AC9) is done with a phone in the hand: neither a positive nor a negative here, shown apart. The other
eleven actions (radio, GPS, drinking, smoking ...) are hard negatives.

The limits of tools/gaze_study.py apply: acted, 3-5 s per action, an assumed 30 FPS, one camera
position. A `phone` alert needs about 1.7 s, so a 3-5 s sequence has little room: the numbers
compare schedules and models with each other, they are not the recall of a real drive.
"""

from __future__ import annotations

import argparse
import copy
import pickle
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from edge_agent.config import PROJECT_ROOT, load_thresholds  # noqa: E402
from tools.gaze_study import ACTIONS, ROOT, frames_of  # noqa: E402
from tools.metrics import rate_ci  # noqa: E402

PHONE_ACTIONS = (5, 6, 7, 8)  # writing a message (right, left hand), phone call (right, left hand)
HELD_ACTIONS = (9,)  # taking a picture: a phone is in the hand, so an alert there is not a false one
KEEP_SCORE = 0.10  # boxes kept by `detect`; the configured phone.conf_threshold is applied by `report`
DEFAULT_MODEL = "640"


# --------------------------------------------------------------------------- schedules (pure)


@dataclass(frozen=True)
class Schedule:
    """How the detector is run. rule: "pacer" = frontend/src/live/pace.ts (the frame nearest the due
    time), "legacy" = the page before M67 (the first frame at least one period after the last run).
    latency_s: from the frame's time to its answer being usable (preparation + inference)."""

    name: str
    fps: float
    latency_s: float
    rule: str = "pacer"
    model: str = DEFAULT_MODEL


def launches(times: np.ndarray, s: Schedule) -> list[int]:
    """Indices of the frames handed to the detector: about `s.fps` a second, never while the previous
    answer is still out (it comes back `s.latency_s` after its frame)."""
    taken: list[int] = []
    if s.fps <= 0:
        return taken
    period = 1.0 / s.fps
    due = -np.inf
    busy_until = -np.inf
    last_t: float | None = None
    for i, t in enumerate(times):
        dt = 0.0 if last_t is None else max(t - last_t, 0.0)
        last_t = t
        if t < busy_until:
            continue
        if s.rule == "legacy":
            if taken and t - times[taken[-1]] < period:
                continue
        else:
            if t + dt / 2 < due:
                continue
            due = due + period if t - due < max(dt, 1e-3) else t + period
        taken.append(i)
        busy_until = t + s.latency_s
    return taken


def result_in_use(times: np.ndarray, taken: list[int], latency_s: float, max_age_s: float) -> np.ndarray:
    """Per frame: the index of the frame whose answer is the newest one back, -1 when there is none
    or it is older than `max_age_s` (block 8 then reads "unknown")."""
    out = np.full(len(times), -1, dtype=np.int64)
    k = -1  # newest launch whose answer is back
    for i, t in enumerate(times):
        while k + 1 < len(taken) and times[taken[k + 1]] + latency_s <= t + 1e-9:
            k += 1
        if k >= 0 and t - times[taken[k]] <= max_age_s + 1e-9:
            out[i] = taken[k]
    return out


def ages_ms(times: np.ndarray, used: np.ndarray) -> np.ndarray:
    """Age of the answer in use on the frames that have one, in ms."""
    known = used >= 0
    return (times[known] - times[used[known]]) * 1000.0


# --------------------------------------------------------------------------- phone flag per frame


def boxes_of(det: dict[str, np.ndarray], n: int, min_score: float) -> list[list[tuple[float, ...]]]:
    """Ragged per-frame boxes [(x1, y1, x2, y2, score), ...], best first, at `min_score` or more."""
    per_frame: list[list[tuple[float, ...]]] = [[] for _ in range(n)]
    for i, box, score in zip(det["idx"], det["boxes"], det["scores"], strict=True):
        if score >= min_score:
            per_frame[int(i)].append((*map(float, box), float(score)))
    for boxes in per_frame:
        boxes.sort(key=lambda b: -b[4])
    return per_frame


def phone_columns(
    tr: dict, per_frame: list[list[tuple[float, ...]]], used: np.ndarray, thresholds: dict[str, Any]
) -> tuple[np.ndarray, np.ndarray]:
    """(phone_flag, phone_kind) columns as block 4 gives them: the answer in use against the CURRENT
    frame's face box (the trace's, which already carries FaceBoxMemory); NaN = unknown."""
    from edge_agent.perception.phone_detector import PhoneDetection, PhoneDetectorConfig, phone_kind, phone_near_face
    from tools.seq_eval import PHONE_KIND_CODES

    cfg = PhoneDetectorConfig.from_dict(thresholds.get("phone"))
    c = tr["cols"]
    n = tr["n"]
    flag = np.full(n, np.nan)
    kind = np.full(n, np.nan)
    for i in range(n):
        j = used[i]
        if j < 0:
            continue
        dets = tuple(PhoneDetection(bbox=b[:4], score=b[4]) for b in per_frame[j])
        face = (
            None
            if np.isnan(c["face_x1"][i])
            else tuple(float(c[k][i]) for k in ("face_x1", "face_y1", "face_x2", "face_y2"))
        )
        flag[i] = float(phone_near_face(dets, face, cfg))
        held = phone_kind(dets, face, cfg)
        if held is not None:
            kind[i] = PHONE_KIND_CODES[held]
    return flag, kind


def action_spans(tr: dict) -> dict[int, tuple[float, float]]:
    return {int(name[2:]): (a, b) for name, a, b in tr["labels"]}


@dataclass
class Score:
    """One schedule over all drivers."""

    sequences: int = 0  # phone sequences (driver x action AC5-AC8)
    alerted: int = 0  # ... with a `phone` alert inside the sequence
    by_action: dict[int, list[int]] | None = None  # action -> [alerted, sequences]
    latency_s: list[float] | None = None  # sequence start -> first `phone` alert
    false_alerts: int = 0  # `phone` alerts outside every phone / picture sequence (+ tolerance)
    held_alerts: int = 0  # `phone` alerts while taking a picture (AC9): counted on neither side
    negative_h: float = 0.0  # hours of video of the negative actions
    pos_frames: int = 0  # frames with a known answer inside phone sequences
    pos_flagged: int = 0
    neg_frames: int = 0  # ... outside
    neg_flagged: int = 0
    unknown: int = 0  # frames without a usable answer
    frames: int = 0
    ages: list[np.ndarray] | None = None
    per_start: dict[int, list[int]] | None = None  # starting frame -> [sequences alerted, false alerts]

    def __post_init__(self) -> None:
        self.by_action = {a: [0, 0] for a in PHONE_ACTIONS}
        self.latency_s = []
        self.ages = []
        self.per_start = {}


def score_driver(
    tr: dict, flag: np.ndarray, alerts: list[tuple[int, int, tuple[str, ...]]], tol_s: float, sc: Score
) -> None:
    """Add one driver. An alert up to `tol_s` after a phone sequence ended still belongs to it: the
    rule needs ~1.7 s and the alert manager holds a level for seconds."""
    t = tr["cols"]["t"]
    spans = action_spans(tr)
    phone_spans = [(a, *spans[a]) for a in PHONE_ACTIONS if a in spans]
    held_spans = [spans[a] for a in HELD_ACTIONS if a in spans]
    inside = np.zeros(tr["n"], bool)
    held = np.zeros(tr["n"], bool)
    for _, s, e in phone_spans:
        inside |= (t >= s - 1e-9) & (t <= e + 1e-9)
    for s, e in held_spans:
        held |= (t >= s - 1e-9) & (t <= e + 1e-9)
    outside = ~inside & ~held
    known = ~np.isnan(flag)
    sc.frames += tr["n"]
    sc.unknown += int((~known).sum())
    sc.pos_frames += int((inside & known).sum())
    sc.pos_flagged += int(np.nansum(flag[inside & known]))
    sc.neg_frames += int((outside & known).sum())
    sc.neg_flagged += int(np.nansum(flag[outside & known]))
    sc.negative_h += float(outside.sum()) / tr["fps"] / 3600.0
    phone_alerts = [float(t[i]) for i, _, reasons in alerts if "phone" in reasons]
    for a, s, e in phone_spans:
        sc.sequences += 1
        sc.by_action[a][1] += 1
        hits = [x for x in phone_alerts if s <= x <= e]
        if hits:
            sc.alerted += 1
            sc.by_action[a][0] += 1
            sc.latency_s.append(hits[0] - s)
    for x in phone_alerts:
        if any(s <= x <= e + tol_s for _, s, e in phone_spans):
            continue
        if any(s <= x <= e + tol_s for s, e in held_spans):
            sc.held_alerts += 1
        else:
            sc.false_alerts += 1


def evaluate(
    traces: dict[str, dict],
    dets: dict[str, dict],
    s: Schedule,
    thresholds: dict[str, Any],
    tol_s: float,
    starts: int = 1,
) -> Score:
    """All drivers under schedule `s`, once per starting frame 0 .. starts - 1 of the detector, summed.
    Which frames the detector happens to get moves a borderline sequence across the alert rule: one
    start alone cannot tell that from an effect of the schedule."""
    from tools.seq_eval import replay

    max_age = float(thresholds["phone"]["max_result_age_s"])
    conf = float(thresholds["phone"]["conf_threshold"])
    sc = Score()
    for key, tr in traces.items():
        det = dets[key]
        if det["n"] != tr["n"]:
            raise SystemExit(f"{key}: {det['n']} frames of detections against {tr['n']} in the trace")
        t = tr["cols"]["t"]
        per_frame = boxes_of(det["models"][s.model], tr["n"], conf)
        for first in range(starts):
            taken = [first + i for i in launches(t[first:], s)]
            used = result_in_use(t, taken, s.latency_s, max_age)
            flag, kind = phone_columns(tr, per_frame, used, thresholds)
            played = copy.copy(tr)
            played["cols"] = {**tr["cols"], "phone_flag": flag, "phone_kind": kind}
            out = replay(played, thresholds)
            before = (sc.alerted, sc.false_alerts)
            score_driver(tr, flag, out["alerts"], tol_s, sc)
            tally = sc.per_start.setdefault(first, [0, 0])
            tally[0] += sc.alerted - before[0]
            tally[1] += sc.false_alerts - before[1]
            sc.ages.append(ages_ms(t, used))
    return sc


def every_kth(
    traces: dict[str, dict], dets: dict[str, dict], k: int, delay_frames: int, thresholds: dict[str, Any], tol_s: float
) -> list[tuple[int, int]]:
    """The plainest schedule there is, every k-th frame with the answer back `delay_frames` later, from
    each of its k possible first frames: [(sequences alerted, false alerts), ...]. The spread over the
    offsets is what the choice of frames alone does to the result."""
    from tools.seq_eval import replay

    max_age = float(thresholds["phone"]["max_result_age_s"])
    conf = float(thresholds["phone"]["conf_threshold"])
    scores = [Score() for _ in range(k)]
    for key, tr in traces.items():
        t = tr["cols"]["t"]
        per_frame = boxes_of(dets[key]["models"][DEFAULT_MODEL], tr["n"], conf)
        for offset, sc in enumerate(scores):
            used = result_in_use(t, list(range(offset, tr["n"], k)), delay_frames / tr["fps"] - 1e-6, max_age)
            flag, kind = phone_columns(tr, per_frame, used, thresholds)
            played = copy.copy(tr)
            played["cols"] = {**tr["cols"], "phone_flag": flag, "phone_kind": kind}
            score_driver(tr, flag, replay(played, thresholds)["alerts"], tol_s, sc)
    return [(sc.alerted, sc.false_alerts) for sc in scores]


# --------------------------------------------------------------------------- detect (model)


def detect_driver(args: tuple[str, dict[str, tuple[str, int]], int]) -> tuple[str, dict]:
    """YOLO on every frame of one driver, in the order tools/gaze_study.py traced them."""
    import cv2

    from edge_agent.capture import Frame
    from edge_agent.perception.onnx import load_ort
    from edge_agent.perception.phone_detector import PhoneDetectorConfig, decode_yolov8, letterbox
    from edge_agent.perception.preprocess import PreprocessConfig, Preprocessor

    subject, models, threads = args
    ort = load_ort()
    th = load_thresholds()
    cfg = PhoneDetectorConfig.from_dict(th.get("phone"))
    pre = Preprocessor(PreprocessConfig.from_dict(th.get("preprocess")))
    sessions = {}
    for name, (path, size) in models.items():
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = threads
        opts.inter_op_num_threads = 1
        sess = ort.InferenceSession(path, opts, providers=["CPUExecutionProvider"])
        sessions[name] = (sess, sess.get_inputs()[0].name, size)
    found: dict[str, dict[str, list]] = {name: {"idx": [], "boxes": [], "scores": []} for name in models}
    i = 0
    for action in ACTIONS:
        for p in frames_of(ROOT / subject / f"AC{action}"):
            image = cv2.imread(str(p))
            if image is None:
                continue
            frame = pre(Frame(image=image, frame_id=i, timestamp=0.0)).image  # the 640-wide frame block 4 gets
            h, w = frame.shape[:2]
            for name, (sess, input_name, size) in sessions.items():
                boxed, scale, pad = letterbox(frame, size)
                blob = cv2.dnn.blobFromImage(boxed, 1.0 / 255.0, swapRB=True)
                output = sess.run(None, {input_name: blob})[0]
                for d in decode_yolov8(output, cfg.class_id, KEEP_SCORE, cfg.iou_threshold, scale, pad, (w, h)):
                    found[name]["idx"].append(i)
                    found[name]["boxes"].append(d.bbox)
                    found[name]["scores"].append(d.score)
            i += 1
    packed = {
        name: {
            "idx": np.asarray(f["idx"], dtype=np.int32),
            "boxes": np.asarray(f["boxes"], dtype=np.float32).reshape(-1, 4),
            "scores": np.asarray(f["scores"], dtype=np.float32),
        }
        for name, f in found.items()
    }
    return subject, {"n": i, "models": packed}


def run_detect(out: Path, models: dict[str, tuple[str, int]], workers: int, threads: int, limit: int | None) -> None:
    from multiprocessing import Pool

    subjects = sorted((p.name for p in ROOT.iterdir() if p.is_dir()), key=lambda s: int(s[1:]))[:limit]
    if not subjects:
        raise SystemExit(f"no 3MDAD subjects under {ROOT}")
    with Pool(workers) as pool:
        done = dict(pool.imap_unordered(detect_driver, [(s, models, threads) for s in subjects]))
    dets = {f"D{int(s[1:]):02d}": done[s] for s in subjects}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(
        pickle.dumps(
            {"models": {k: {"path": Path(p).name, "size": size} for k, (p, size) in models.items()}, "drivers": dets}
        )
    )
    frames = sum(d["n"] for d in dets.values())
    print(f"[phone_study] {len(dets)} drivers, {frames} frames, models {', '.join(models)} -> {out} (boxes only)")


# --------------------------------------------------------------------------- report


def _pct(k: int, n: int) -> str:
    return f"{k} / {n} ({100.0 * k / n:.1f} %)" if n else "–"


def _q(a: np.ndarray, p: float) -> str:
    return f"{np.percentile(a, p):.0f}" if len(a) else "–"


def _spread(sc: Score, k: int) -> str:
    """Lowest - highest count over the starting frames (k: 0 = sequences alerted, 1 = false alerts)."""
    counts = [v[k] for v in sc.per_start.values()]
    return f"{min(counts)}–{max(counts)}" if counts else "–"


def score_row(s: Schedule, sc: Score) -> str:
    ages = np.concatenate(sc.ages) if sc.ages else np.array([])
    lat = np.asarray(sc.latency_s)
    rate, lo, hi = rate_ci(sc.false_alerts, sc.negative_h)
    per_h = "–" if rate is None else f"{rate:.1f} ({lo:.1f}–{hi:.1f})"
    precision = sc.alerted / (sc.alerted + sc.false_alerts) if sc.alerted + sc.false_alerts else float("nan")
    return (
        f"| {s.name} | {s.fps:g} | {s.latency_s * 1000:.0f} | {_q(ages, 50)} / {_q(ages, 95)} | "
        f"{_pct(sc.alerted, sc.sequences)} | {_spread(sc, 0)} | {precision:.1%} | {sc.false_alerts} | {_spread(sc, 1)} | "
        f"{per_h} | {sc.held_alerts} | "
        f"{(f'{np.median(lat):.2f} / {np.percentile(lat, 95):.2f}') if len(lat) else '–'} | "
        f"{_pct(sc.pos_flagged, sc.pos_frames)} | {_pct(sc.neg_flagged, sc.neg_frames)} | "
        f"{100.0 * sc.unknown / sc.frames:.1f} % |"
    )


TABLE_HEAD = [
    "| Schedule | Runs / s asked | Answer back after (ms) | Age in use p50 / p95 (ms) | Phone sequences with a `phone` alert (recall), all starts | "
    "... per start, of 200 | Precision of the alerts | False `phone` alerts (in the 11 other actions), all starts | ... per start | ... per hour (95 % CI) | "
    "`phone` alerts while taking a picture | Sequence start to alert, median / p95 (s) | Frames seeing a phone, inside phone sequences | ... outside | Frames without an answer |",
    "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
]


def frame_level(
    traces: dict[str, dict], dets: dict[str, dict], model: str, thresholds: dict[str, Any]
) -> dict[str, Any]:
    """The model alone, every frame its own answer: how often it sees a phone in the driver zone, per action."""
    conf = float(thresholds["phone"]["conf_threshold"])
    by_action = {a: [0, 0, 0] for a in ACTIONS}  # frames, phone anywhere, phone in the driver zone
    for key, tr in traces.items():
        n = tr["n"]
        per_frame = boxes_of(dets[key]["models"][model], n, conf)
        own = np.arange(n)
        flag, _ = phone_columns(tr, per_frame, own, thresholds)
        anywhere = np.array([bool(b) for b in per_frame])
        t = tr["cols"]["t"]
        for a, (s, e) in action_spans(tr).items():
            m = (t >= s - 1e-9) & (t <= e + 1e-9)
            by_action[a][0] += int(m.sum())
            by_action[a][1] += int(anywhere[m].sum())
            by_action[a][2] += int(np.nansum(flag[m]))
    return by_action


def report(
    traces: dict[str, dict],
    det_doc: dict[str, Any],
    thresholds: dict[str, Any],
    schedules: list[Schedule],
    size_schedule: Schedule,
    tol_s: float,
    starts: int = 6,
) -> str:
    dets = det_doc["drivers"]
    frames = sum(t["n"] for t in traces.values())
    fps = next(iter(traces.values()))["fps"]
    ph = thresholds["phone"]
    lines = [
        "# DriverGuard - the phone branch against how and when YOLO runs (3MDAD)",
        "",
        f"`tools/phone_study.py`. 3MDAD day set, face camera (`RGB2`): {len(traces)} drivers, {frames} frames, "
        f"{frames / fps / 3600:.2f} h at an assumed {fps:g} FPS. YOLO ran once on every frame (the plain 640-wide frame "
        "block 4 gets); every schedule below is then played on those boxes: which frame the detector would have been "
        "given, when its answer would have been back, what each frame would have seen. Blocks 7-12 are replayed on the "
        "trace of `tools/gaze_study.py` with that phone flag. Numbers only, no image kept.",
        "",
        "Positives: the 4 phone actions (message right / left hand, call right / left hand), one sequence per driver "
        'and action. "Taking a picture" (AC9) is done with a phone in the hand: its alerts are counted on neither side. '
        f"Negatives: the other 11 actions. An alert up to {tol_s:g} s after a sequence still belongs to it. Thresholds as configured: score >= {ph['conf_threshold']}, driver zone, `phone_ratio` "
        f"{thresholds['risk']['distraction']['phone_ratio']} over {thresholds['distraction']['phone_window_s']:g} s, "
        f"answers older than {ph['max_result_age_s'] * 1000:.0f} ms unknown.",
        "",
        "Acted sequences of 3-5 s at one camera position: a `phone` alert needs about 1.7 s, so the recall here is far "
        "below a real call. Read the rows against each other.",
        "",
        f"Every row is played {starts} times, the detector starting on frame 0 .. {starts - 1}, and summed: which frames it "
        "happens to get moves a borderline sequence across the alert rule, and one start alone cannot tell that from an "
        "effect of the schedule. The starts share the same video, so the summed counts are not independent samples: the "
        "per-hour interval is the one of the summed count over the summed hours, an optimistic one.",
        "",
        "## 1. Same model (640), different schedules",
        "",
        *TABLE_HEAD,
    ]
    scores = {s.name: evaluate(traces, dets, s, thresholds, tol_s, starts) for s in schedules}
    lines += [score_row(s, scores[s.name]) for s in schedules]
    lines += [
        "",
        "Per phone action (sequences with a `phone` alert):",
        "",
        "| Schedule | " + " | ".join(f"AC{a} {ACTIONS[a]}" for a in PHONE_ACTIONS) + " |",
        "|---|" + "---:|" * len(PHONE_ACTIONS),
    ]
    for s in schedules:
        sc = scores[s.name]
        lines.append(
            f"| {s.name} | " + " | ".join(f"{sc.by_action[a][0]} / {sc.by_action[a][1]}" for a in PHONE_ACTIONS) + " |"
        )

    lines += [
        "",
        "### How much the choice of frames alone moves the result",
        "",
        "Every k-th frame, the answer back 3 frames later (100 ms), from each of the k possible first frames. No rule of "
        "the page is involved: the spread over the offsets is sampling luck, and a difference between two rows of the "
        "table above that is smaller than it is not an effect of the schedule.",
        "",
        "| Every k-th frame | Runs / s | Phone sequences with a `phone` alert, per offset (of 200) | Mean | False `phone` alerts, per offset | Plays with a false alert |",
        "|---:|---:|---|---:|---|---:|",
    ]
    for k in (3, 6, 7):
        rows = every_kth(traces, dets, k, 3, thresholds, tol_s)
        lines.append(
            f"| {k} | {fps / k:.1f} | {', '.join(str(a) for a, _ in rows)} | {np.mean([a for a, _ in rows]):.1f} | "
            f"{', '.join(str(f) for _, f in rows)} | {sum(1 for _, f in rows if f)} / {k} |"
        )

    models = [m for m in det_doc["models"] if m != DEFAULT_MODEL]
    if models:
        lines += [
            "",
            "## 2. Smaller input, same pretrained weights re-exported (not in use)",
            "",
            f"Schedule of every row: {size_schedule.fps:g} runs / s, answer back after {size_schedule.latency_s * 1000:.0f} ms "
            "(the same for every size, so only what the model sees differs).",
            "",
            *[h.replace("| Schedule |", "| Input |") for h in TABLE_HEAD],
        ]
        for m in [DEFAULT_MODEL, *models]:
            s = Schedule(m, size_schedule.fps, size_schedule.latency_s, size_schedule.rule, m)
            lines.append(score_row(s, evaluate(traces, dets, s, thresholds, tol_s, starts)))
        lines += [
            "",
            "The model alone, every frame its own answer (share of the frames of an action with a phone box at the "
            "configured score: anywhere in the image / in the driver zone):",
            "",
            "| Action | Frames | " + " | ".join(f"{m}: anywhere / in zone" for m in [DEFAULT_MODEL, *models]) + " |",
            "|---|---:|" + "---:|" * (len(models) + 1),
        ]
        levels = {m: frame_level(traces, dets, m, thresholds) for m in [DEFAULT_MODEL, *models]}
        for a, title in ACTIONS.items():
            n = levels[DEFAULT_MODEL][a][0]
            cells = " | ".join(
                f"{100.0 * levels[m][a][1] / n:.1f} % / {100.0 * levels[m][a][2] / n:.1f} %" for m in levels
            )
            mark = " **(phone)**" if a in PHONE_ACTIONS else " (phone in the hand)" if a in HELD_ACTIONS else ""
            lines.append(f"| AC{a} {title}{mark} | {n} | {cells} |")
    return "\n".join(lines) + "\n"


# The page before and after M67, as measured in Chromium (eval/results/benchmark_live.md): the answer
# is back one preparation + one inference after its frame; before M67 MediaPipe (9 ms) ran first.
WEB_SCHEDULES = [
    Schedule("page before M67: wasm, 2 threads", 5, 0.105, "legacy"),
    Schedule("page after M67, no GPU: wasm, 2 threads", 5, 0.095),
    Schedule("page after M67, real GPU: WebGPU", 10, 0.020),
    Schedule("tried, not kept: wasm at 10 / s", 10, 0.100),
    Schedule("for reference: every frame, at once", 1000, 0.0),
]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("detect", help="YOLO on every frame of 3MDAD, boxes only")
    d.add_argument("--out", required=True)
    d.add_argument(
        "--model",
        action="append",
        default=[],
        help="NAME=PATH of another export, NAME = its input size (e.g. 416=/tmp/yolov8n_416.onnx)",
    )
    d.add_argument("--workers", type=int, default=5)
    d.add_argument("--threads", type=int, default=2, help="onnxruntime threads per worker")
    d.add_argument("--limit", type=int, default=None, help="first N drivers only")
    r = sub.add_parser("report", help="schedules played on the boxes, blocks 7-12 replayed")
    r.add_argument("--dets", required=True)
    r.add_argument("--traces", default=str(PROJECT_ROOT / "data/eval_traces/3mdad_day.pkl"))
    r.add_argument("--out", default=None)
    r.add_argument("--starts", type=int, default=6, help="starting frames of the detector each schedule is played from")
    r.add_argument(
        "--tolerance",
        type=float,
        default=None,
        help="seconds after a phone sequence an alert still belongs to it (default: eval.label_tolerance_s)",
    )
    args = p.parse_args(argv)
    th = load_thresholds()
    if args.cmd == "detect":
        cfg = th["phone"]
        models = {DEFAULT_MODEL: (str(PROJECT_ROOT / cfg["model_path"]), int(cfg["input_size"]))}
        for spec in args.model:
            name, path = spec.split("=", 1)
            models[name] = (path, int(name))
        run_detect(Path(args.out), models, args.workers, args.threads, args.limit)
        return 0
    det_doc = pickle.loads(Path(args.dets).read_bytes())
    traces = {k: v for k, v in pickle.loads(Path(args.traces).read_bytes()).items() if k in det_doc["drivers"]}
    tol = float(th["eval"]["label_tolerance_s"]) if args.tolerance is None else args.tolerance
    text = report(traces, det_doc, th, WEB_SCHEDULES, Schedule("size", 5, 0.095), tol, args.starts)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"[phone_study] report -> {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
