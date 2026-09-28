"""Block 13 - Local HUD server (in-car).

A tiny HTTP server on the device (127.0.0.1 only, never exposed to the network) that
the in-car HUD screen talks to:
- GET  /state     current level, reasons, scores, speed and the latest alerts
- POST /feedback  {"event_id": ...}: the driver pressed "false alarm" on an alert

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
                return "ok"
        return "unknown"

    def to_json(self) -> dict[str, Any]:
        with self._lock:
            return {
                **self._snapshot,
                "camera_lost": self._camera_lost,  # driver not monitored, reconnecting
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
            if self.path != "/feedback":
                self._json(404, {"detail": "not found"})
                return
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > MAX_BODY:
                self._json(400, {"detail": "bad body"})
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
