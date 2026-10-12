"""Block 13 - Local HUD server (in-car).

A tiny HTTP server on the device (127.0.0.1 only, never exposed to the network) that
the in-car HUD screen talks to:
- GET  /state     current level, reasons, scores, speed and the latest alerts (with the numbers behind
                  each one); M65: `trip` (continuous driving, the drowsy_score of the last
                  hud.trend_minutes minutes) and `incident` (since when the driver is not monitored,
                  camera reopen attempts, whether the backend has the event). The agent keeps them for
                  the whole trip, so a HUD that reloads shows them again at once
- POST /feedback  {"event_id": ...}: the driver pressed "false alarm" on an alert
- POST /vehicle   {"action": "change_driver"}: "Đổi tài xế"; {"action": "enroll_start" | "enroll_later"}:
                  the driver's answer on the enrollment consent screen ("Đồng ý" / "Để sau");
                  {"action": "presence_ok"}: the tap on "Bạn còn ở đó không?" (M44). The main
                  loop applies them (parked / driving is not a button: it follows the speed)
- POST /end-trip  the driver pressed "end trip": the main loop builds the trip summary
                  (block 11), sends it to the backend, and the reply carries it for the HUD

Who may call it (M84): the request must name this machine in `Host` (a page that reaches
127.0.0.1 under another name, DNS rebinding, is refused), a POST that carries an `Origin` must
come from an allowed one, and a POST with a body must be `application/json`. A browser sends
`Origin` with every cross-origin POST, so another page open on this machine can no longer end the
trip, change the driver or answer "Bạn còn ở đó không?".

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

from edge_agent.analysis.drowsiness import DrowsinessConfig
from edge_agent.config import config_from_dict
from edge_agent.context.vehicle_context import in_hours
from edge_agent.decision.alert_manager import LEVEL_ACTIONS
from edge_agent.decision.pipeline import DecisionResult
from edge_agent.decision.risk_engine import RiskConfig

log = logging.getLogger("driverguard.hud")

MAX_BODY = 1024
VEHICLE_ACTIONS = ("change_driver", "enroll_start", "enroll_later", "presence_ok")


@dataclass(frozen=True)
class HudConfig:
    feedback_window_s: float = 120.0  # the driver can flag an alert for this long after it fired
    processing_error_s: float = 1.0  # frames failing this long: "processing error" (not monitored)
    low_fps_below: float = 14.5  # smoothed FPS below this ...
    low_fps_s: float = 5.0  # ... for this long: "alerts may be late"
    fps_smoothing: float = 0.9  # weight of the last FPS value against the newest frame gap
    trend_minutes: int = 15  # minutes of drowsy_score in the HUD's fatigue chart (M65)
    recent_alerts: int = 10  # alerts kept for the HUD
    end_trip_wait_s: float = 10.0  # POST /end-trip waits this long for the main loop's summary
    summary_wait_s: float = 3.0  # the main loop waits this long for the HUD to fetch it
    # The screen's own numbers (frontend/src/hud), sent with every state as `display`:
    poll_s: float = 0.3
    state_timeout_s: float = 1.0
    link_down_failures: int = 3
    stale_s: float = 3.0
    chime_to_voice_s: float = 0.7
    alarm_repeat_s: float = 1.5
    presence_repeat_s: float = 2.0
    gain_1: float = 0.12  # hud.gain: loudness per level
    gain_2: float = 0.25
    gain_3: float = 0.35
    # Local hours in which the calm screens are dimmed. The screen's own window: block 10's
    # context.night_hours is about the score, and neither moves the other.
    dim_hours: tuple[tuple[float, float], ...] = ((18.0, 6.0),)

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> HudConfig:
        """Build the config from the `hud` section of thresholds.yaml; an unknown key is an error."""
        d = dict(d or {})
        if "dim_hours" in d:
            d["dim_hours"] = tuple((float(a), float(b)) for a, b in d["dim_hours"])
        return config_from_dict(cls, d, "hud")


def hud_display(thresholds: dict[str, Any]) -> dict[str, Any]:
    """What the screen needs from thresholds.yaml to show and sound a state: it keeps no number of its
    own. Sent with every state (`display`), and written to frontend/src/lib/defaults.gen.json by
    tools/web_defaults.py for the time before the first state. Two numbers are another block's: the
    eye tile says "open" for closures up to a blink and turns red where the L3 rule starts."""
    cfg = HudConfig.from_dict(thresholds.get("hud"))
    risk = RiskConfig.from_dict(thresholds.get("risk"))
    return {
        "poll_s": cfg.poll_s,
        "state_timeout_s": cfg.state_timeout_s,
        "link_down_failures": cfg.link_down_failures,
        "stale_s": cfg.stale_s,
        "chime_to_voice_s": cfg.chime_to_voice_s,
        "alarm_repeat_s": cfg.alarm_repeat_s,
        "presence_repeat_s": cfg.presence_repeat_s,
        "gain": [0.0, cfg.gain_1, cfg.gain_2, cfg.gain_3],  # by level
        "feedback_window_s": cfg.feedback_window_s,
        "blink_max_s": DrowsinessConfig.from_dict(thresholds.get("drowsiness")).blink_max_s,
        "microsleep_l3_s": risk.microsleep_l3_s,
        "score_l1": risk.drowsy_l1,
        "score_l2": risk.drowsy_l2,
    }


class HudState:
    """Latest decision snapshot shared between the main loop and the HUD server. Thread-safe."""

    def __init__(self, config: HudConfig | None = None, display: dict[str, Any] | None = None) -> None:
        """display: hud_display(thresholds), handed to the screen with every state (None: left out)."""
        self.config = config or HudConfig()
        self.display = display
        self._lock = threading.Lock()
        self._snapshot: dict[str, Any] = {"connected": False, "level": 0, "reasons": []}
        self._alerts: deque[dict[str, Any]] = deque(maxlen=self.config.recent_alerts)
        self._camera_lost = False
        self._processing_error = False  # frames keep failing: not monitored (M28)
        self._low_fps = False  # FPS too low for a while: alerts may be late (M28)
        self._too_slow = False  # under 2 FPS for a while: nothing can be timed, not monitored (M96)
        self._phone_unavailable = False  # the phone detector gives no fresh results (M50)
        # M65: since when the driver is not monitored (camera lost / processing error), how many times
        # the camera was reopened meanwhile, and whether the backend has the event (None: not known here).
        self._incident: dict[str, Any] | None = None
        self.false_alarms = 0  # flagged by the driver this trip (for the trip summary)
        self._end_requested = threading.Event()
        self._summary_ready = threading.Event()
        self._summary_delivered = threading.Event()
        self._summary: dict[str, Any] | None = None
        self._vehicle: dict[str, Any] = {
            "source": None,
            "connected": False,
            "speed_kmh": 0.0,
            "turn_signal": None,
            "driving": False,
        }
        self._actions: deque[str] = deque(maxlen=8)

    # ------------------------------------------------------------------ vehicle buttons
    def request_vehicle(self, action: str) -> str:
        """'queued', or 'unknown'."""
        if action not in VEHICLE_ACTIONS:
            return "unknown"
        with self._lock:
            self._actions.append(action)
        return "queued"

    def take_actions(self) -> list[str]:
        """The vehicle button presses queued since the last call, oldest first."""
        with self._lock:
            actions = list(self._actions)
            self._actions.clear()
        return actions

    def set_vehicle(self, state: dict[str, Any]) -> None:
        """Set the vehicle state shown by the HUD (speed source, parked / driving)."""
        with self._lock:
            self._vehicle = dict(state)

    def update(self, r: DecisionResult, fps: float, trip: dict[str, Any] | None = None) -> None:
        """trip: TripCollector.hud_view (M65): continuous driving and the recent minutes. It lives in
        the agent for the whole trip, so a HUD that reloads reads it back at once."""
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
            "night": c.night,  # block 10's window: the score's night factor
            "dim": in_hours(c.clock_hour, self.config.dim_hours),  # the screen's window: calm screens dimmed
            "eyes_closed_s": round(r.drowsiness.closed_duration, 2),
            "perclos_60s": round(r.drowsiness.perclos_60s, 3),
            "fps": round(fps, 1),
            "unavailable": r.risk.unavailable,  # face lost / unreadable while rolling: not monitored (FR-6)
            "unavailable_reason": r.risk.unavailable_reason,  # no_face, camera_blocked, low_light, ...
            "quality": {"issue": r.quality.issue, "score": round(r.quality.score, 2)},  # block 6 stage
            "presence": {  # M44: "Bạn còn ở đó không?" while the driver is out of view
                "asking": r.presence.asking,
                "remaining_s": round(r.presence.remaining_s, 1),
                "unanswered": r.presence.unanswered,
            },
            "enrollment": {  # driver enrollment: the HUD guides the steps (words, voice, beep)
                "status": r.enrollment.status,
                "progress": round(r.enrollment.progress, 2),
                "hint": r.enrollment.hint,
                "attempts": r.enrollment.attempts,
                "duration_s": None if r.enrollment.duration_s is None else round(r.enrollment.duration_s, 1),
            },
        }
        if trip is not None:
            snapshot["trip"] = trip
        with self._lock:
            self._snapshot = snapshot

    def set_camera_lost(self, lost: bool) -> None:
        """The camera is lost (or back): the driver is not being monitored."""
        with self._lock:
            self._camera_lost = lost

    def set_processing_error(self, error: bool) -> None:
        """Frames keep failing: the HUD shows it. The snapshot is kept fresh, so the HUD says "processing
        error" rather than "no data from the camera"."""
        with self._lock:
            self._processing_error = error
            self._snapshot = {**self._snapshot, "updated_at": time.time()}

    def set_too_slow(self, slow: bool) -> None:
        """The loop is too slow for the decision blocks to time anything: shown as "monitoring unavailable"
        with the reason `slow_loop`, whatever block 9 says about the face."""
        with self._lock:
            self._too_slow = slow

    def set_low_fps(self, low: bool) -> None:
        """The loop has been too slow for a while (or recovered): alerts may be late."""
        with self._lock:
            self._low_fps = low

    def set_phone_unavailable(self, unavailable: bool) -> None:
        """Phones are not being detected (or are again)."""
        with self._lock:
            self._phone_unavailable = unavailable

    # ------------------------------------------------------------------ not monitored (M65)
    def start_incident(self, kind: str, event_id: str | None, since: float | None = None) -> None:
        """kind: "camera_lost" or "processing_error". event_id: the system event sent for it."""
        with self._lock:
            self._incident = {
                "kind": kind,
                "since": time.time() if since is None else since,
                "attempts": None,  # camera reopen attempts, set by the device loop
                "event_id": event_id,
                "reported": None,  # True once the backend accepted the event; None: no publisher here
            }

    def end_incident(self, kind: str) -> None:
        """The running incident is over, when it is of this kind."""
        with self._lock:
            if self._incident is not None and self._incident["kind"] == kind:
                self._incident = None

    def set_incident_attempts(self, attempts: int) -> None:
        """Set how many times the camera was reopened during the running incident."""
        with self._lock:
            if self._incident is not None:
                self._incident["attempts"] = attempts

    def incident_event_id(self) -> str | None:
        """The id of the system event sent for the running incident, or None."""
        with self._lock:
            return None if self._incident is None else self._incident["event_id"]

    def set_incident_reported(self, reported: bool) -> None:
        """Whether the backend accepted the event of the running incident."""
        with self._lock:
            if self._incident is not None:
                self._incident["reported"] = reported

    def add_alert(
        self, event_id: str, level: int, reasons: tuple[str, ...], metrics: dict[str, Any] | None = None
    ) -> None:
        """metrics: what the alert's detail line says (M65): off_road_s, eyes_closed_s, phone_ratio,
        turn_signal at the moment it fired."""
        with self._lock:
            self._alerts.append(
                {
                    "event_id": event_id,
                    "level": level,
                    "reasons": list(reasons),
                    "at": time.time(),
                    "feedback": None,
                    "metrics": dict(metrics or {}),
                }
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
        """The driver pressed "end trip": the main loop builds the summary."""
        self._end_requested.set()

    @property
    def end_requested(self) -> bool:
        """True once the end of the trip was requested."""
        return self._end_requested.is_set()

    def set_summary(self, summary: dict[str, Any]) -> None:
        """The main loop built the trip summary: hand it to the waiting HUD request."""
        with self._lock:
            self._summary = summary
        self._summary_ready.set()

    def wait_summary(self, timeout: float) -> dict[str, Any] | None:
        """Wait up to `timeout` seconds for the trip summary; None when it did not come."""
        if not self._summary_ready.wait(timeout):
            return None
        with self._lock:
            return self._summary

    def mark_delivered(self) -> None:
        """The HUD has received the trip summary."""
        self._summary_delivered.set()

    def wait_delivered(self, timeout: float) -> bool:
        """The main loop waits for the HUD to have the summary before the server stops."""
        return self._summary_delivered.wait(timeout)

    def to_json(self) -> dict[str, Any]:
        """The state the HUD polls: the last snapshot plus the health flags, the incident and the alerts."""
        with self._lock:
            return {
                **self._snapshot,
                "camera_lost": self._camera_lost,  # driver not monitored, reconnecting
                "processing_error": self._processing_error,  # frames keep failing: not monitored (M28)
                "low_fps": self._low_fps,  # too slow for a while: alerts may be late (M28)
                **({"unavailable": True, "unavailable_reason": "slow_loop"} if self._too_slow else {}),  # M96
                "phone_unavailable": self._phone_unavailable,  # phones are not being detected (M50)
                "incident": None if self._incident is None else dict(self._incident),  # M65
                "trip_ended": self._summary is not None,
                "vehicle": dict(self._vehicle),  # speed source, parked / driving by the speed
                "feedback_window_s": self.config.feedback_window_s,  # the HUD hides the button after it
                **({} if self.display is None else {"display": dict(self.display)}),
                "alerts": [dict(a) for a in reversed(self._alerts)],
            }


DEFAULT_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")
LOCAL_HOSTS = ("127.0.0.1", "localhost")  # the names this server answers to (it only binds 127.0.0.1)


def host_name(header: str | None) -> str:
    """`Host` header without its port, lowercased ("" when missing)."""
    return (header or "").strip().rsplit(":", 1)[0].lower()


def make_handler(
    state: HudState, on_false_alarm: Callable[[str], None], allowed_origins: tuple[str, ...]
) -> type[BaseHTTPRequestHandler]:
    """The request handler class of the HUD server, bound to this state. Local requests only."""

    class Handler(BaseHTTPRequestHandler):
        server_version = "DriverGuardHUD/1"

        def log_message(self, fmt: str, *args: Any) -> None:  # keep the terminal for alerts
            """Send the access log to the debug logger, not the terminal."""
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

        def _local(self) -> bool:
            """False (and 403 sent) when the request does not name this machine in `Host`."""
            if host_name(self.headers.get("Host")) in LOCAL_HOSTS:
                return True
            self._json(403, {"detail": "host not allowed"})
            return False

        def do_OPTIONS(self) -> None:  # noqa: N802 - http.server naming
            """CORS preflight."""
            if not self._local():
                return
            self.send_response(204)
            self._cors()
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            """GET /state: the current HUD state."""
            if not self._local():
                return
            if self.path.split("?")[0] == "/state":
                self._json(200, state.to_json())
            else:
                self._json(404, {"detail": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            """POST /end-trip, /feedback (false alarm) or /vehicle (button), from an allowed origin only."""
            if not self._local():
                return
            origin = self.headers.get("Origin")
            if origin is not None and origin not in allowed_origins:
                self._json(403, {"detail": "origin not allowed"})
                return
            if self.path == "/end-trip":
                state.request_end()
                summary = state.wait_summary(state.config.end_trip_wait_s)
                if summary is None:
                    self._json(503, {"detail": "the agent did not answer"})
                    return
                self._json(200, {"summary": summary})
                state.mark_delivered()
                return
            if self.path not in ("/feedback", "/vehicle"):
                self._json(404, {"detail": "not found"})
                return
            if self.headers.get_content_type() != "application/json":
                self._json(415, {"detail": "expected application/json"})
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
        """The port the server listens on."""
        return self._httpd.server_address[1]

    def start(self) -> HudServer:
        """Serve on a background thread."""
        self._thread = threading.Thread(target=self._httpd.serve_forever, name="HudServer", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        """Stop serving and close the socket."""
        self._httpd.shutdown()
        self._httpd.server_close()
