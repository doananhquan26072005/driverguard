"""Block 13 - HUD (minimal, M4).

Draws the active alert level as a coloured banner on the preview frame and formats
terminal lines for new alerts. The full driver HUD / dashboard is milestone M6.
Display only - frames are never written to disk.
"""

from __future__ import annotations

import cv2
import numpy as np

from edge_agent.decision.alert_manager import LEVEL_ACTIONS, Alert
from edge_agent.decision.pipeline import DecisionResult

LEVEL_COLORS = {0: (60, 160, 60), 1: (0, 200, 255), 2: (0, 120, 255), 3: (0, 0, 230)}  # BGR


def alert_line(alert: Alert) -> str:
    reasons = ", ".join(alert.reasons) or "-"
    return (
        f"[ALERT L{alert.level}] {reasons} -> {alert.action}  "
        f"(drowsy {alert.drowsy_score:.0f}, distraction {alert.distraction_score:.0f})"
    )


def status_line(r: DecisionResult, fps: float) -> str:
    c = r.context
    speed = "--" if c.speed_kmh is None else f"{c.speed_kmh:3.0f}"
    trend = "--" if r.trip.trend_15min is None else f"{r.trip.trend_15min:+.1f}/min"
    return (
        f"FPS {fps:4.1f} | L{r.alert.active_level} | drowsy {r.risk.drowsy_score:3.0f} "
        f"distraction {r.risk.distraction_score:3.0f} | PERCLOS {r.drowsiness.perclos_60s:.2f} "
        f"off_road {r.distraction.off_road_duration:3.1f}s phone {r.distraction.phone_ratio_2s:.2f} | "
        f"{speed} km/h{' night' if c.night else ''}{' turning' if c.turning else ''} | trend {trend}"
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
    box = out[h - 28 : h, :]
    box[:] = (box * 0.35).astype(np.uint8)
    cv2.putText(out, info, (10, h - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (230, 230, 230), 1, cv2.LINE_AA)
    return out
