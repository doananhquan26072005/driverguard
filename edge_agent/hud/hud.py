"""Block 13 - the device build's preview-window banner and terminal lines.

Draws the active alert level as a coloured banner on the preview frame and formats
terminal lines for new alerts, enrollment and the trip summary. The driver HUD itself is the
web page (frontend/src/hud), fed by edge_agent/hud/server.py on the device and by
edge_agent/web/bridge.py on #/live. Display only - frames are never written to disk.
"""

from __future__ import annotations

import cv2
import numpy as np

from edge_agent.decision.alert_manager import LEVEL_ACTIONS, Alert
from edge_agent.decision.pipeline import DecisionResult

LEVEL_COLORS = {0: (60, 160, 60), 1: (0, 200, 255), 2: (0, 120, 255), 3: (0, 0, 230)}  # BGR


def alert_line(alert: Alert) -> str:
    """One terminal line for a new alert: level, reasons, action and both scores."""
    reasons = ", ".join(alert.reasons) or "-"
    return (
        f"[ALERT L{alert.level}] {reasons} -> {alert.action}  "
        f"(drowsy {alert.drowsy_score:.0f}, distraction {alert.distraction_score:.0f})"
    )


ENROLL_PROMPTS = {  # preview window / terminal; the in-car HUD words them in Vietnamese
    "look_camera": "Look straight at the camera",
    "look_road": "Look at the road ahead",
    "close_eyes": "Close your eyes until the beep",
    "waiting": "Stop the vehicle to enroll the driver",
    "failed": "Enrollment failed: retry at the next stop",
}


def enrollment_line(r: DecisionResult) -> str | None:
    """Enrollment progress for the terminal, None once done / off."""
    e = r.enrollment
    if e.status in ("done", "off"):
        return None
    hint = f" ({e.hint})" if e.hint else ""
    return f"[ENROLL] {e.status} {e.progress:.0%}{hint}"


def trip_summary_line(s: dict) -> str:
    """One terminal line for the end-of-trip summary (block 11)."""
    alerts = s["alerts_by_level"]
    return (
        f"{s['trip_id']}: {s['duration_s'] / 60:.0f} min, driving {s['driving_s'] / 60:.0f} min, "
        f"alerts L1/L2/L3 {alerts['1']}/{alerts['2']}/{alerts['3']}, rating {s['rating']}"
        f"{' (' + ', '.join(s['rating_reasons']) + ')' if s['rating_reasons'] else ''}"
    )


def status_line(r: DecisionResult, fps: float) -> str:
    """One terminal status line for the current frame: FPS, level, scores and the main metrics."""
    c = r.context
    speed = "--" if c.speed_kmh is None else f"{c.speed_kmh:3.0f}"
    trend = "--" if r.trip.trend_15min is None else f"{r.trip.trend_15min:+.1f}/min"
    return (
        f"FPS {fps:4.1f} | L{r.alert.active_level} | drowsy {r.risk.drowsy_score:3.0f} "
        f"distraction {r.risk.distraction_score:3.0f} | PERCLOS {r.drowsiness.perclos_60s:.2f} "
        f"off_road {r.distraction.off_road_duration:3.1f}s phone {r.distraction.phone_ratio_2s:.2f} | "
        f"{speed} km/h{' night' if c.night else ''}{' turning' if c.turning else ''} | trend {trend}"
        f"{'' if r.enrollment.enrolled else ' | not enrolled'}"
    )


def draw_hud(image: np.ndarray, r: DecisionResult, fps: float) -> np.ndarray:
    """Return a copy of `image` with a level banner on top and a score line at the bottom."""
    out = image.copy()
    h, w = out.shape[:2]
    level = r.alert.active_level
    cv2.rectangle(out, (0, 0), (w, 36), LEVEL_COLORS[level], -1)
    reasons = ", ".join(r.alert.active_reasons)
    title = f"L{level}  {LEVEL_ACTIONS[level]}" + (f"  |  {reasons}" if reasons else "")
    cv2.putText(out, title, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 1, cv2.LINE_AA)

    c = r.context
    speed = "--" if c.speed_kmh is None else f"{c.speed_kmh:.0f}"
    info = (
        f"drowsy {r.risk.drowsy_score:.0f}  distraction {r.risk.distraction_score:.0f}  "
        f"{speed} km/h  {int(c.clock_hour):02d}:{int(c.clock_hour % 1 * 60):02d}  FPS {fps:.0f}"
    )
    prompt = ENROLL_PROMPTS.get(r.enrollment.status)
    if prompt is not None:
        progress = f"  {r.enrollment.progress:.0%}" if r.enrollment.step_active else ""
        cv2.putText(out, prompt + progress, (10, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1, cv2.LINE_AA)
    box = out[h - 28 : h, :]
    box[:] = (box * 0.35).astype(np.uint8)
    cv2.putText(out, info, (10, h - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (230, 230, 230), 1, cv2.LINE_AA)
    return out
