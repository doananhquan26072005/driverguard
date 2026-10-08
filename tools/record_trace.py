"""M39 - Record numbers straight from the camera, with key-press labels. No image is ever stored.

CLAUDE.md forbids writing frames to disk, so the team cannot record videos of itself to tune on.
This tool runs the full pipeline (blocks 2-12, the same wiring as tools/seq_eval.py) on the live
camera and keeps one row of numbers per frame (EAR, MAR, head pose, eyeBlink, gaze and mouth
blendshapes, iris position, face box, phone box / flag / kind, levels, alerts), plus the labels
the person presses on the keyboard while acting. The preview window shows the frame; it is never
written anywhere.

    # one session per condition; tags say what the condition is
    python tools/record_trace.py record --out data/own_traces/quan.pkl --name mask_day \
        --tag person=quan --tag mask=medical --tag glasses=no --tag light=day
    # what was recorded
    python tools/record_trace.py report --traces data/own_traces/quan.pkl --out eval/results/own_recordings.md
    # the traces replay like any other (what-if thresholds, blocks 7-12 only)
    python tools/record_trace.py report --traces data/own_traces/quan.pkl --set drowsiness.microsleep_deep.bowed_ear_ratio=0.3

Keys while recording (press once when the action starts, again when it ends; several may be on):
    e eyes closed        d looking down at a phone   b looking at the dashboard   s looking to the side
    r looking behind     y yawning                   t talking                    n nodding (head drop)
    c phone at the ear   x phone held to text        a sitting still, eyes on the road
    q / Esc  stop and save

What the report measures:
- time to alert per kind of action: first matching alert / event after the key press, p50 / p95
  (PRD: p95 <= 3 s). The key press is a person's reaction, not ground truth: read delays with
  `eval.label_tolerance_s` in mind.
- alerts outside every label (and inside "talking" / "sitting still"): false alarms per hour, with CI.
- looking down vs eyes closed: EAR / baseline, eyeBlink, eyeLookDown, pitch per kind of action.
- mouth covered (mask): face found, MAR spread and reversals while sitting still, yawns counted
  against the labels, closed-eye spells that reached L3, grouped by the `mask` tag.
- call vs text: the recorded phone kind against the label.

A video file works as the source too (`--source clip.mp4 --script "eyes_closed@5-8,yawn@12-15"`),
for clips that already exist; time is then frame index / fps.
"""

from __future__ import annotations

import argparse
import pickle
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.metrics import EvalConfig, ci_text, rate_ci  # noqa: E402
from tools.seq_eval import PHONE_KIND_NAMES, Tracer, replay, set_threshold  # noqa: E402

Label = tuple[str, float, float]  # name, start_s, end_s

KEYS = {
    "e": "eyes_closed",
    "d": "look_down_phone",
    "b": "look_dashboard",
    "s": "look_side",
    "r": "look_behind",
    "y": "yawn",
    "t": "talking",
    "n": "nod",
    "c": "phone_call",
    "x": "phone_text",
    "a": "awake_still",
    "m": "look_mount",
    "g": "look_gear",
    "j": "eyes_down",
    "k": "eyes_side",
    "l": "glance_repeat",
    "w": "bow_eyes_closed",
    "v": "mirror_check",
    "p": "look_partial",
}
# What the system should answer each action with: ("alert", reason) or ("event", block 7 event).
# None: nothing; an alert inside such a label is a false alarm.
EXPECTED: dict[str, tuple[str, str] | None] = {
    "eyes_closed": ("alert", "microsleep"),
    "look_down_phone": ("alert", "off_road"),
    "look_dashboard": ("alert", "off_road"),
    "look_side": ("alert", "off_road"),
    "look_behind": ("alert", "off_road"),
    "phone_call": ("alert", "phone"),
    "phone_text": ("alert", "phone"),
    "yawn": ("event", "yawn"),
    "nod": ("event", "nod"),
    "talking": None,
    "awake_still": None,
    "look_mount": ("alert", "off_road"),  # phone on a low mount
    "look_gear": ("alert", "off_road"),
    "eyes_down": ("alert", "off_road"),  # eyes only, head kept still
    "eyes_side": ("alert", "off_road"),
    "glance_repeat": ("alert", "off_road"),  # short glances in a row, no single one long enough
    "bow_eyes_closed": ("alert", "microsleep"),  # head bowed and eyes really closed
    "mirror_check": None,  # a normal look at a mirror
    "look_partial": ("alert", "off_road"),  # head turned part of the way, held
}
QUIET = tuple(k for k, v in EXPECTED.items() if v is None)
PHONE_LABELS = {"phone_call": "call", "phone_text": "text"}


# --------------------------------------------------------------------------- labels (pure)


class LabelKeys:
    """Key presses -> labelled intervals: the first press of a label starts it, the next one ends it."""

    def __init__(self) -> None:
        self.open: dict[str, float] = {}
        self.done: list[Label] = []

    def press(self, key: str, t: float) -> str | None:
        """Returns the label the key belongs to, None for an unknown key."""
        label = KEYS.get(key)
        if label is None:
            return None
        if label in self.open:
            self.done.append((label, self.open.pop(label), t))
        else:
            self.open[label] = t
        return label

    def close(self, t: float) -> list[Label]:
        """End of the recording: labels still on end here. Sorted by start."""
        for label, start in self.open.items():
            self.done.append((label, start, t))
        self.open = {}
        return sorted(self.done, key=lambda x: (x[1], x[0]))


def parse_script(text: str) -> list[Label]:
    """ "eyes_closed@5-8,yawn@12-15.5" -> labels (for a video file, where no key can be pressed)."""
    out: list[Label] = []
    for part in filter(None, (p.strip() for p in text.split(","))):
        name, _, span = part.partition("@")
        start, _, end = span.partition("-")
        if name not in EXPECTED:
            raise ValueError(f"unknown label {name!r} (expected one of {sorted(EXPECTED)})")
        a, b = float(start), float(end)
        if b <= a:
            raise ValueError(f"{part}: end must be after start")
        out.append((name, a, b))
    return sorted(out, key=lambda x: (x[1], x[0]))


def parse_tags(items: Sequence[str]) -> dict[str, str]:
    tags = {}
    for item in items:
        key, sep, value = item.partition("=")
        if not sep or not key or not value:
            raise ValueError(f"tag must be key=value, got {item!r}")
        tags[key.strip()] = value.strip()
    return tags


# --------------------------------------------------------------------------- scoring (pure)


def percentile(values: Sequence[float], q: float) -> float | None:
    return float(np.percentile(np.asarray(values, dtype=float), q)) if len(values) else None


def answer_times(trace: dict, kind: str, what: str) -> list[float]:
    """Times (s) the system answered: alerts carrying reason `what`, or block 7 events `what`."""
    t = trace["cols"]["t"]
    if kind == "event":
        return [float(t[i]) for i, ev in trace["events"] if ev == what]
    times = [float(t[i]) for i, _, reasons in trace["alerts"] if what in reasons]
    if what == "microsleep":  # L3 still active from the closure before: no new alert, but the alarm is on
        level = trace["cols"]["level"]
        rising = np.flatnonzero((level[1:] >= 3) & (level[:-1] < 3)) + 1
        times += [float(t[i]) for i in rising]
        if len(level) and level[0] >= 3:
            times.append(float(t[0]))
    return sorted(times)


def time_to_alert(trace: dict, tolerance_s: float) -> list[dict[str, Any]]:
    """One row per label that expects an answer: its delay from the key press, None when missed."""
    rows = []
    for label, start, end in trace.get("labels", []):
        expected = EXPECTED.get(label)
        if expected is None:
            continue
        hits = [x for x in answer_times(trace, *expected) if start - tolerance_s <= x <= end + tolerance_s]
        rows.append(
            {"label": label, "start": start, "duration": end - start, "delay": hits[0] - start if hits else None}
        )
    return rows


def false_alarms(trace: dict, tolerance_s: float) -> tuple[list[tuple[float, int, tuple[str, ...]]], float]:
    """(alerts that answer no label, seconds where one can happen).

    An alert is explained when it falls inside a label that expects that reason (widened by the
    tolerance). Everything else is a false alarm, also inside the quiet labels (`QUIET`). The exposure
    is the recording minus the labelled actions that expect an alert (widened)."""
    t = trace["cols"]["t"]
    duration = float(t[-1] - t[0]) if len(t) > 1 else 0.0
    spans = defaultdict(list)
    for label, start, end in trace.get("labels", []):
        expected = EXPECTED.get(label)
        if expected is not None and expected[0] == "alert":
            spans[expected[1]].append((start - tolerance_s, end + tolerance_s))
    out = []
    for i, level, reasons in trace["alerts"]:
        when = float(t[i])
        explained = any(a <= when <= b for r in reasons for a, b in spans.get(r, []))
        if not explained:
            out.append((when, level, tuple(reasons)))
    covered = sorted(x for xs in spans.values() for x in xs)
    busy, edge = 0.0, float(t[0]) if len(t) else 0.0
    last = float(t[-1]) if len(t) else 0.0
    for a, b in covered:
        a, b = max(a, edge), min(b, last)
        if b > a:
            busy += b - a
            edge = b
    return out, max(0.0, duration - busy)


def mask_of(trace: dict, start: float, end: float) -> np.ndarray:
    t = trace["cols"]["t"]
    return (t >= start) & (t < end)


def label_frames(trace: dict, label: str) -> np.ndarray:
    """Frames inside any interval of `label`."""
    m = np.zeros(trace["n"], dtype=bool)
    for name, start, end in trace.get("labels", []):
        if name == label:
            m |= mask_of(trace, start, end)
    return m


def reversals(values: np.ndarray, swing: float) -> int:
    """Direction changes of at least `swing` (zigzag count): a still mouth has none, one jump (a yawn
    starting) has none, a yawn and back has one, talking has many."""
    v = values[~np.isnan(values)]
    if len(v) == 0:
        return 0
    count, direction, extreme = 0, 0, float(v[0])
    for x in v[1:]:
        if direction == 0:
            if abs(x - extreme) >= swing:
                direction, extreme = (1 if x > extreme else -1), float(x)
        elif (x - extreme) * direction > 0:
            extreme = float(x)  # still going the same way
        elif abs(x - extreme) >= swing:
            count, direction, extreme = count + 1, -direction, float(x)
    return count


def _col(trace: dict, name: str) -> np.ndarray:
    return trace["cols"].get(name, np.full(trace["n"], np.nan))


def _mean2(trace: dict, a: str, b: str) -> np.ndarray:
    """Mean of two per-frame columns (both eyes); a frame where only one is measured keeps that one."""
    x, y = _col(trace, a), _col(trace, b)
    both = np.where(np.isnan(x), y, np.where(np.isnan(y), x, (x + y) / 2.0))
    return both


# --------------------------------------------------------------------------- report


def _f(v: float | None, d: int = 2) -> str:
    return "–" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:.{d}f}"


def _pct(num: float, den: float) -> str:
    return "–" if den <= 0 else f"{100 * num / den:.0f}%"


def _stats(values: np.ndarray) -> str:
    v = values[~np.isnan(values)]
    if len(v) == 0:
        return "–"
    return f"{np.percentile(v, 10):.2f} / {np.percentile(v, 50):.2f} / {np.percentile(v, 90):.2f}"


def tag_text(trace: dict) -> str:
    return ", ".join(f"{k}={v}" for k, v in sorted(trace.get("tags", {}).items())) or "–"


def report(traces: dict[str, dict], thresholds: dict[str, Any], group_by: str = "mask") -> str:
    cfg = EvalConfig.from_dict(thresholds.get("eval"))
    tol = cfg.label_tolerance_s
    l3_s = float(thresholds["risk"]["microsleep_l3_s"])
    swing = float(thresholds["drowsiness"]["microsleep_mask"]["talk_swing"])
    ok = {k: v for k, v in sorted(traces.items()) if not isinstance(v, str) and v["n"] > 1}
    hours = sum(float(v["cols"]["t"][-1] - v["cols"]["t"][0]) for v in ok.values()) / 3600
    lines = [
        "# DriverGuard - own recordings (numbers from the camera, key-press labels)",
        "",
        f"{len(ok)} recordings, {hours * 60:.1f} min. Full pipeline (blocks 2-12) on the camera frames at a simulated "
        "constant speed; one row of numbers per frame, no image stored. Labels are key presses of the person "
        f"acting, matched ± {tol:g} s (`eval.label_tolerance_s`). Acted by the team: a development set, not evidence "
        "for real driving.",
        "",
        "## 1. Recordings",
        "",
        "| Recording | Tags | Min | FPS | Face found | Face reliable | Labels | Alerts L1/L2/L3 |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, tr in ok.items():
        c = tr["cols"]
        lv = Counter(a[1] for a in tr["alerts"])
        lines.append(
            f"| {name} | {tag_text(tr)} | {(c['t'][-1] - c['t'][0]) / 60:.1f} | {tr['fps']:.1f} | "
            f"{_pct(np.nansum(c['face']), tr['n'])} | {_pct(np.nansum(c['reliable']), tr['n'])} | "
            f"{len(tr.get('labels', []))} | {lv[1]}/{lv[2]}/{lv[3]} |"
        )

    # ---- time to alert
    by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for tr in ok.values():
        for row in time_to_alert(tr, tol):
            by_label[row["label"]].append(row)
    lines += [
        "",
        "## 2. Time to alert (PRD: p95 ≤ 3 s)",
        "",
        "Delay = first matching alert (or block 7 event) minus the key press. Eyes closed: only spells of at least "
        f"`risk.microsleep_l3_s` ({l3_s:g} s) are expected to reach L3; shorter ones are listed apart.",
        "",
        "| Action | Expected | Labelled | Answered | Delay p50 (s) | Delay p95 (s) | Slowest (s) |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for label in EXPECTED:
        rows = by_label.get(label, [])
        if not rows or EXPECTED[label] is None:
            continue
        groups = [(label, rows)]
        if label == "eyes_closed":
            groups = [
                (f"eyes_closed ≥ {l3_s:g} s", [r for r in rows if r["duration"] >= l3_s]),
                (f"eyes_closed < {l3_s:g} s", [r for r in rows if r["duration"] < l3_s]),
            ]
        for name, rs in groups:
            delays = [r["delay"] for r in rs if r["delay"] is not None]
            kind, what = EXPECTED[label]
            lines.append(
                f"| {name} | {kind} {what} | {len(rs)} | {len(delays)} ({_pct(len(delays), len(rs))}) | "
                f"{_f(percentile(delays, 50))} | {_f(percentile(delays, 95))} | {_f(max(delays) if delays else None)} |"
            )
    if not by_label:
        lines.append("| – | no labelled action yet | 0 | – | – | – | – |")

    # ---- false alarms
    fa_total, exposure, by_reason = 0, 0.0, Counter()
    quiet_alerts, quiet_s = 0, 0.0
    for tr in ok.values():
        fas, seconds = false_alarms(tr, tol)
        fa_total += len(fas)
        exposure += seconds
        for _, level, reasons in fas:
            for r in reasons:
                by_reason[(r, level)] += 1
        quiet = np.zeros(tr["n"], dtype=bool)
        for label in QUIET:
            quiet |= label_frames(tr, label)
        quiet_s += float(np.sum(quiet)) / tr["fps"] if tr["fps"] else 0.0
        quiet_alerts += sum(1 for i, _, _ in tr["alerts"] if quiet[i])
    lines += [
        "",
        "## 3. Alerts that answer no label",
        "",
        f"- {fa_total} alerts outside every labelled action that expects one, on {exposure / 3600:.2f} h: "
        f"{ci_text(rate_ci(fa_total, exposure / 3600))} per hour (exact Poisson 95 % CI). Unlabelled time is taken as "
        "normal driving posture; an action the person forgot to label counts against the system here.",
        f"- {quiet_alerts} alerts inside {' / '.join(f'`{q}`' for q in QUIET)} ({quiet_s / 60:.1f} min): "
        f"{ci_text(rate_ci(quiet_alerts, quiet_s / 3600))} per hour.",
    ]
    if by_reason:
        lines.append(
            "- By reason and level: " + ", ".join(f"{r} L{lv} {n}" for (r, lv), n in sorted(by_reason.items())) + "."
        )

    # ---- looking down vs eyes closed
    lines += [
        "",
        "## 4. Looking down or eyes closed (numbers per kind of action)",
        "",
        "p10 / p50 / p90 over the frames of the labelled intervals. EAR ratio = EAR / the open-eye baseline of that "
        "moment; pitch in degrees (> 0 = head down); eyeBlink, eyeLookDown: MediaPipe blendshapes (mean of both eyes).",
        "",
        "| Action | Frames | EAR ratio | eyeBlink | eyeLookDown | Pitch | Iris y | Block 7 closed | Masked |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label in (
        "awake_still",
        "eyes_closed",
        "bow_eyes_closed",
        "look_down_phone",
        "look_mount",
        "look_dashboard",
        "look_gear",
        "eyes_down",
        "eyes_side",
        "look_partial",
        "look_side",
        "glance_repeat",
        "mirror_check",
        "talking",
        "yawn",
    ):
        parts = defaultdict(list)
        frames = closed = masked = 0
        for tr in ok.values():
            m = label_frames(tr, label)
            if not m.any():
                continue
            c = tr["cols"]
            frames += int(m.sum())
            parts["ear"].append((c["ear"] / c["ear_base"])[m])
            parts["blink"].append(_col(tr, "blink")[m])
            parts["down"].append(_mean2(tr, "look_down_l", "look_down_r")[m])
            parts["pitch"].append(c["pitch"][m])
            parts["iris"].append(_mean2(tr, "iris_y_l", "iris_y_r")[m])
            closed += int(np.nansum(c["eye_closed"][m] == 1))
            masked += int(np.nansum(c["masked"][m] == 1))
        if not frames:
            continue
        cat = {k: np.concatenate(v) for k, v in parts.items()}
        lines.append(
            f"| {label} | {frames} | {_stats(cat['ear'])} | {_stats(cat['blink'])} | {_stats(cat['down'])} | "
            f"{_stats(cat['pitch'])} | {_stats(cat['iris'])} | {_pct(closed, frames)} | {_pct(masked, frames)} |"
        )

    # ---- mouth covered
    groups: dict[str, list[dict]] = defaultdict(list)
    for tr in ok.values():
        groups[tr.get("tags", {}).get(group_by, "not tagged")].append(tr)
    lines += [
        "",
        f"## 5. By `{group_by}` tag (mouth covered or not)",
        "",
        f"MAR reversals: direction changes of at least `microsleep_mask.talk_swing` ({swing:g}) per minute of "
        "`awake_still` (a still mouth should have none; many would switch the talking mask on and hide closed eyes). "
        f"L3 reached: labelled closed-eye spells of at least {l3_s:g} s during which the risk level got to 3.",
        "",
        f"| {group_by} | Min | Face found | MAR still (p10 / p50 / p90) | MAR reversals / min still | "
        "Masked while still | Yawns labelled | Yawn events in them | Yawn events elsewhere | "
        "Closed spells | L3 reached | Masked during them |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for value, trs in sorted(groups.items()):
        n = sum(t["n"] for t in trs)
        seconds = sum(float(t["cols"]["t"][-1] - t["cols"]["t"][0]) for t in trs)
        face = sum(float(np.nansum(t["cols"]["face"])) for t in trs)
        still_mar, still_rev, still_s, still_masked, still_n = [], 0, 0.0, 0, 0
        yawn_labels = yawn_hit = yawn_else = spells = l3 = 0
        closed_masked = closed_n = 0
        for t in trs:
            c = t["cols"]
            m = label_frames(t, "awake_still")
            still_mar.append(c["mar"][m])
            still_n += int(m.sum())
            still_masked += int(np.nansum(c["masked"][m] == 1))
            for name, start, end in t.get("labels", []):
                seg = mask_of(t, start, end)
                if name == "awake_still":
                    still_rev += reversals(c["mar"][seg], swing)
                    still_s += end - start
                elif name == "eyes_closed" and end - start >= l3_s:
                    spells += 1
                    wide = mask_of(t, start, end + tol)
                    l3 += bool(np.any(c["level"][wide] >= 3))
                    closed_n += int(seg.sum())
                    closed_masked += int(np.nansum(c["masked"][seg] == 1))
            yawns = [(a - tol, b + tol) for name, a, b in t.get("labels", []) if name == "yawn"]
            yawn_labels += len(yawns)
            times = [float(c["t"][i]) for i, ev in t["events"] if ev == "yawn"]
            yawn_hit += sum(any(a <= x <= b for x in times) for a, b in yawns)
            yawn_else += sum(not any(a <= x <= b for a, b in yawns) for x in times)
        mar = np.concatenate(still_mar) if still_mar else np.full(0, np.nan)
        lines.append(
            f"| {value} | {seconds / 60:.1f} | {_pct(face, n)} | {_stats(mar)} | "
            f"{_f(still_rev / (still_s / 60) if still_s > 0 else None, 1)} | {_pct(still_masked, still_n)} | "
            f"{yawn_labels} | {yawn_hit} | {yawn_else} | {spells} | {l3} ({_pct(l3, spells)}) | "
            f"{_pct(closed_masked, closed_n)} |"
        )

    # ---- call vs text
    confusion: Counter = Counter()
    seen = Counter()
    for tr in ok.values():
        flag, kind = _col(tr, "phone_flag"), _col(tr, "phone_kind")
        for label, want in PHONE_LABELS.items():
            m = label_frames(tr, label)
            seen[(want, "frames")] += int(m.sum())
            seen[(want, "phone")] += int(np.nansum(flag[m] == 1))
            for code, name in PHONE_KIND_NAMES.items():
                confusion[(want, name)] += int(np.nansum(kind[m] == code))
    lines += [
        "",
        "## 6. Call or text (block 4 `phone_kind` against the label)",
        "",
        "| Labelled | Frames | Phone in the driver zone | Recorded call | Recorded text | Recorded unknown |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for want in ("call", "text"):
        frames = seen[(want, "frames")]
        lines.append(
            f"| {want} | {frames} | {_pct(seen[(want, 'phone')], frames)} | {confusion[(want, 'call')]} | "
            f"{confusion[(want, 'text')]} | {confusion[(want, 'unknown')]} |"
        )
    if not any(seen.values()):
        lines.append("")
        lines.append("No `phone_call` / `phone_text` label recorded yet.")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- recording


def numbers_only(trace: dict) -> None:
    """Raise if the trace holds anything but per-frame scalars, events, alerts, labels and tags."""
    for name, col in trace["cols"].items():
        if not isinstance(col, np.ndarray) or col.ndim != 1 or col.dtype.kind != "f":
            raise ValueError(f"column {name} is not a 1-D float array: refusing to save")
    allowed = {"fps", "n", "cols", "events", "alerts", "labels", "tags", "source"}
    extra = set(trace) - allowed
    if extra:
        raise ValueError(f"unexpected trace fields {sorted(extra)}: refusing to save")


def frames_of(source: str, thresholds: dict[str, Any]) -> Iterator[tuple[np.ndarray, float]]:
    """(image, seconds from the start). A camera index: live frames on the wall clock; a file: every
    frame, time = frame index / fps (reproducible)."""
    import cv2

    from edge_agent.capture import CaptureConfig, FrameSource

    if source.isdigit():
        with FrameSource(source, CaptureConfig.from_dict(thresholds.get("capture"))) as camera:
            t0 = None
            while not camera.ended:
                frame = camera.read(timeout=0.5)
                if frame is None:
                    continue
                t0 = frame.timestamp if t0 is None else t0
                yield frame.image, frame.timestamp - t0
        return
    cap = cv2.VideoCapture(source)
    try:
        if not cap.isOpened():
            raise RuntimeError(f"cannot open {source}")
        fps = cap.get(cv2.CAP_PROP_FPS)
        fps = fps if 0 < fps < 1000 else 30.0
        i = 0
        while True:
            ok, image = cap.read()
            if not ok:
                return
            yield image, i / fps
            i += 1
    finally:
        cap.release()


def overlay(image: np.ndarray, t: float, level: int, on: Sequence[str], width: int = 960) -> np.ndarray:
    """Preview picture for the window (shown, never saved): time, level, labels that are on, the keys."""
    import cv2

    h, w = image.shape[:2]
    view = cv2.resize(image, (width, round(h * width / w)))
    legend = "  ".join(f"{k}:{v}" for k, v in KEYS.items())
    rows = [f"t {t:6.1f} s   level L{level}   REC (numbers only)", "ON: " + (", ".join(on) or "-")]
    rows += [legend[i : i + 96] for i in range(0, len(legend), 96)] + ["q / Esc: stop and save"]
    for k, text in enumerate(rows):
        y = 24 + 22 * k
        cv2.putText(view, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(view, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    return view


def record(args: argparse.Namespace, thresholds: dict[str, Any]) -> dict:
    import cv2

    keys = LabelKeys()
    window = "DriverGuard - record trace (no image is stored)"
    show = not args.no_window
    if show:
        cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    t = 0.0
    wall0 = time.perf_counter()
    with Tracer(thresholds, args.speed, not args.no_phone) as tracer:
        try:
            for i, (image, t) in enumerate(frames_of(args.source, thresholds)):
                r = tracer.step(image, i, t)
                if show:
                    cv2.imshow(window, overlay(image, t, r.alert.active_level, sorted(keys.open)))
                    key = cv2.waitKey(1) & 0xFF
                    if key in (ord("q"), 27):
                        break
                    if key != 255 and keys.press(chr(key), t) is None and chr(key).strip():
                        print(f"[record] key {chr(key)!r} is not a label", file=sys.stderr)
                if args.max_s and t >= args.max_s:
                    break
        except KeyboardInterrupt:
            print("[record] interrupted: saving what was recorded", file=sys.stderr)
        finally:
            if show:
                cv2.destroyAllWindows()
        n = len(tracer.rows)
        live = args.source.isdigit()
        fps = n / (time.perf_counter() - wall0) if live else (n - 1) / t if t > 0 else 0.0
        trace = tracer.result(fps)
    trace["labels"] = parse_script(args.script) if args.script else keys.close(t)
    trace["tags"] = parse_tags(args.tag)
    trace["source"] = "camera" if live else "file"
    return trace


def save(path: Path, name: str, trace: dict, overwrite: bool) -> None:
    numbers_only(trace)
    data = pickle.loads(path.read_bytes()) if path.exists() else {}
    if name in data and not overwrite:
        raise SystemExit(f"{path} already has a recording named {name!r}: pick another --name or pass --overwrite")
    data[name] = trace
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pickle.dumps(data))


def load(paths: Sequence[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for p in paths:
        for name, tr in pickle.loads(Path(p).read_bytes()).items():
            out[name if name not in out else f"{Path(p).stem}/{name}"] = tr
    return out


# --------------------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    rec = sub.add_parser("record", help="record numbers and labels from the camera")
    rec.add_argument("--out", required=True, help="trace file (.pkl); recordings are added to it")
    rec.add_argument("--name", required=True, help="name of this recording inside the file")
    rec.add_argument("--source", default="0", help="camera index, or a video file (with --script)")
    rec.add_argument("--tag", action="append", default=[], help="condition, e.g. mask=medical (repeatable)")
    rec.add_argument(
        "--speed", type=float, default=None, help="simulated vehicle speed, km/h (default: eval.replay_speed_kmh)"
    )
    rec.add_argument("--no-phone", action="store_true", help="skip YOLO")
    rec.add_argument("--no-window", action="store_true", help="no preview window (no key labels either)")
    rec.add_argument("--script", default=None, help='labels for a video file: "eyes_closed@5-8,yawn@12-15"')
    rec.add_argument("--max-s", type=float, default=0.0, help="stop after this many seconds (0 = until q)")
    rec.add_argument("--overwrite", action="store_true")
    rec.add_argument("--set", action="append", default=[], help="what-if threshold while recording")
    rep = sub.add_parser("report", help="score recorded traces")
    rep.add_argument("--traces", nargs="+", required=True)
    rep.add_argument("--out", default=None)
    rep.add_argument("--group-by", default="mask", help="tag the mouth table is grouped by")
    rep.add_argument("--set", action="append", default=[], help="what-if threshold: blocks 7-12 are replayed first")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = p.parse_args(argv)

    from edge_agent.config import load_thresholds

    thresholds = load_thresholds()
    for a in args.set:
        set_threshold(thresholds, a)
    if args.cmd == "record":
        parse_tags(args.tag)  # fail before the camera opens
        if args.script:
            parse_script(args.script)
        trace = record(args, thresholds)
        save(Path(args.out), args.name, trace, args.overwrite)
        print(
            f"[record] {args.name}: {trace['n']} frames, {trace['fps']:.1f} FPS, {len(trace['labels'])} labels, "
            f"{len(trace['alerts'])} alerts -> {args.out} (numbers only)"
        )
        return 0
    traces = load(args.traces)
    if args.set:
        traces = {k: replay(v, thresholds) for k, v in traces.items()}  # labels and tags are kept
    text = report(traces, thresholds, args.group_by)
    if args.set:
        head, _, rest = text.partition("\n\n")
        text = f"{head}\n\nBlocks 7-12 replayed with {', '.join(args.set)}.\n\n{rest}"
    print(text)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
