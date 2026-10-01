"""Block 13 - Local HUD server (in-car).

A tiny HTTP server on the device (127.0.0.1 only, never exposed to the network) that
the in-car HUD screen talks to:
- GET  /state     current level, reasons, scores, speed and the latest alerts
- POST /feedback  {"event_id": ...}: the driver pressed "false alarm" on an alert
- POST /vehicle   {"action": "park" | "drive" | "change_driver"}: "Tạm dừng", "Tiếp tục lái",
                  "Đổi tài xế" (park / drive only in the manual vehicle mode); the main loop applies it
- POST /end-trip  the driver pressed "end trip": the main loop builds the trip summary
                  (block 11), sends it to the backend, and the reply carries it for the HUD

Only numbers and short strings go through it - never images. Feedback is forwarded to
the backend by the metadata publisher (block 14), so it also survives offline periods.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from edge_agent.config import config_from_dict
from edge_agent.decision.alert_manager import LEVEL_ACTIONS
from edge_agent.decision.pipeline import DecisionResult

log = logging.getLogger("driverguard.hud")

MAX_BODY = 1024
VEHICLE_ACTIONS = ("park", "drive", "change_driver")
END_TRIP_WAIT_S = 10.0  # the main loop answers on its next frame


@dataclass(frozen=True)
class HudConfig:
    feedback_window_s: float = 120.0  # the driver can flag an alert for this long after it fired

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> HudConfig:
        return config_from_dict(cls, d, "hud")


class HudState:
    """Latest decision snapshot shared between the main loop and the HUD server. Thread-safe."""

    def __init__(self, config: HudConfig | None = None, recent_alerts: int = 10) -> None:
        self.config = config or HudConfig()
        self._lock = threading.Lock()
        self._snapshot: dict[str, Any] = {"connected": False, "level": 0, "reasons": []}
        self._alerts: deque[dict[str, Any]] = deque(maxlen=recent_alerts)
        self._camera_lost = False
        self.false_alarms = 0  # flagged by the driver this trip (for the trip summary)
        self._end_requested = threading.Event()
        self._summary_ready = threading.Event()
        self._summary_delivered = threading.Event()
        self._summary: dict[str, Any] | None = None
        self._vehicle: dict[str, Any] = {"manual": False, "driving": None}
        self._actions: deque[str] = deque(maxlen=8)

    # ------------------------------------------------------------------ vehicle buttons
    def request_vehicle(self, action: str) -> str:
        """'queued', or 'unsupported' (park / drive need the manual vehicle mode)."""
        if action not in VEHICLE_ACTIONS:
            return "unknown"
        with self._lock:
            if action != "change_driver" and not self._vehicle["manual"]:
                return "unsupported"
            self._actions.append(action)
        return "queued"

    def take_actions(self) -> list[str]:
        with self._lock:
            actions = list(self._actions)
            self._actions.clear()
        return actions

    def set_vehicle(self, state: dict[str, Any]) -> None:
        with self._lock:
            self._vehicle = dict(state)

    def update(self, r: DecisionResult, fps: float) -> None:
        c = r.context
        snapshot = {
            "connected": True,
            "updated_at": time.time(),
            "level": r.alert.active_level,
            "action": LEVEL_ACTIONS[r.alert.active_level],
            "reasons": list(r.alert.active_reasons),
            "drowsy_score": round(r.risk.drowsy_score, 1),
            "distraction_score": round(r.risk.distraction_score, 1),
            "speed_kmh": None if c.speed_kmh is None else round(c.speed_kmh, 1),
            "clock_hour": round(c.clock_hour, 3),
            "night": c.night,
            "eyes_closed_s": round(r.drowsiness.closed_duration, 2),
            "perclos_60s": round(r.drowsiness.perclos_60s, 3),
            "fps": round(fps, 1),
            "unavailable": r.risk.unavailable,  # face lost while moving: not monitored, no alerts (FR-6)
            "enrollment": {  # driver enrollment: the HUD guides the steps (words, voice, beep)
                "status": r.enrollment.status,
                "progress": round(r.enrollment.progress, 2),
                "hint": r.enrollment.hint,
                "attempts": r.enrollment.attempts,
                "duration_s": None if r.enrollment.duration_s is None else round(r.enrollment.duration_s, 1),
            },
        }
        with self._lock:
            self._snapshot = snapshot

    def set_camera_lost(self, lost: bool) -> None:
        with self._lock:
            self._camera_lost = lost

    def add_alert(self, event_id: str, level: int, reasons: tuple[str, ...]) -> None:
        with self._lock:
            self._alerts.append(
                {"event_id": event_id, "level": level, "reasons": list(reasons), "at": time.time(), "feedback": None}
            )

    def mark_false_alarm(self, event_id: str, now: float | None = None) -> str:
        """'ok', 'unknown' (no such recent alert), 'expired' or 'duplicate'."""
        now = time.time() if now is None else now
        with self._lock:
            for alert in self._alerts:
                if alert["event_id"] != event_id:
                    continue
                if alert["feedback"] is not None:
                    return "duplicate"
                if now - alert["at"] > self.config.feedback_window_s:
                    return "expired"
                alert["feedback"] = "false_alarm"
                self.false_alarms += 1
                return "ok"
        return "unknown"

    # ------------------------------------------------------------------ end of trip
    def request_end(self) -> None:
        self._end_requested.set()

    @property
    def end_requested(self) -> bool:
        return self._end_requested.is_set()

    def set_summary(self, summary: dict[str, Any]) -> None:
        """The main loop built the trip summary: hand it to the waiting HUD request."""
        with self._lock:
            self._summary = summary
        self._summary_ready.set()

    def wait_summary(self, timeout: float) -> dict[str, Any] | None:
        if not self._summary_ready.wait(timeout):
            return None
        with self._lock:
            return self._summary

    def mark_delivered(self) -> None:
        self._summary_delivered.set()

    def wait_delivered(self, timeout: float) -> bool:
        """The main loop waits for the HUD to have the summary before the server stops."""
        return self._summary_delivered.wait(timeout)

    def to_json(self) -> dict[str, Any]:
        with self._lock:
            return {
                **self._snapshot,
                "camera_lost": self._camera_lost,  # driver not monitored, reconnecting
                "trip_ended": self._summary is not None,
                "vehicle": dict(self._vehicle),  # manual mode: the HUD shows park / drive buttons
                "feedback_window_s": self.config.feedback_window_s,  # the HUD hides the button after it
                "alerts": [dict(a) for a in reversed(self._alerts)],
            }


DEFAULT_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")


def make_handler(
    state: HudState, on_false_alarm: Callable[[str], None], allowed_origins: tuple[str, ...]
) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "DriverGuardHUD/1"

        def log_message(self, fmt: str, *args: Any) -> None:  # keep the terminal for alerts
            log.debug(fmt, *args)

        def _cors(self) -> None:
            origin = self.headers.get("Origin")
            if origin and origin in allowed_origins:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                # Chrome asks before a public page (the hosted dashboard) calls 127.0.0.1
                if self.headers.get("Access-Control-Request-Private-Network") == "true":
                    self.send_header("Access-Control-Allow-Private-Network", "true")

        def _json(self, code: int, body: dict[str, Any]) -> None:
            data = json.dumps(body).encode()
            self.send_response(code)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_OPTIONS(self) -> None:  # noqa: N802 - http.server naming
            self.send_response(204)
            self._cors()
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            if self.path.split("?")[0] == "/state":
                self._json(200, state.to_json())
            else:
                self._json(404, {"detail": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path == "/end-trip":
                state.request_end()
                summary = state.wait_summary(END_TRIP_WAIT_S)
                if summary is None:
                    self._json(503, {"detail": "the agent did not answer"})
                    return
                self._json(200, {"summary": summary})
                state.mark_delivered()
                return
            if self.path not in ("/feedback", "/vehicle"):
                self._json(404, {"detail": "not found"})
                return
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > MAX_BODY:
                self._json(400, {"detail": "bad body"})
                return
            if self.path == "/vehicle":
                try:
                    action = str(json.loads(self.rfile.read(length))["action"])
                except (ValueError, KeyError, TypeError):
                    self._json(400, {"detail": 'expected {"action": ...}'})
                    return
                status = state.request_vehicle(action)
                self._json(202 if status == "queued" else 409, {"status": status})
                return
            try:
                event_id = str(json.loads(self.rfile.read(length))["event_id"])
            except (ValueError, KeyError, TypeError):
                self._json(400, {"detail": 'expected {"event_id": ...}'})
                return
            result = state.mark_false_alarm(event_id)
            if result == "ok":
                on_false_alarm(event_id)
                self._json(200, {"status": "recorded"})
            else:
                self._json(409 if result in ("duplicate", "expired") else 404, {"status": result})

    return Handler


class HudServer:
    def __init__(
        self,
        state: HudState,
        on_false_alarm: Callable[[str], None],
        port: int = 8765,
        allowed_origins: tuple[str, ...] = DEFAULT_ORIGINS,
    ) -> None:
        self.state = state
        self._httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(state, on_false_alarm, allowed_origins))
        self._thread: threading.Thread | None = None

    @property
    def port(self) -> int:
        return self._httpd.server_address[1]

    def start(self) -> HudServer:
        self._thread = threading.Thread(target=self._httpd.serve_forever, name="HudServer", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
