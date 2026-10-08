"""One trip around blocks 6-14, shared by the device (edge_agent.main) and the browser (edge_agent.web.bridge).

Per frame, from the features of blocks 3-6: block 10 samples the vehicle (a link to the vehicle that
goes quiet while driving is a lost signal: the driver and the backend are told, and its time goes in
the summary), the DecisionPipeline
runs blocks 6 (enrollment) to 12, block 3's driver anchor is set once the driver is enrolled, the
HUD state (block 13) is updated, and the metadata records of block 14 are built. Between frames:
"Đổi tài xế", camera lost / back, "false alarm", and the end of the trip (block 11's summary).

HUD buttons between frames also include the enrollment consent answer (`enrollment_answer`) and the
driver's tap on the presence question (`presence_answer`, M44). A question nobody answers is the
system event `no_answer`; like every L3 alert it is sent at once, not with the next batch.

Loop health (M28): a frame that fails anywhere in blocks 2-14 goes to `frame_failed` (the callers catch
it and go on). Failing for `hud.processing_error_s` = "processing error" on the HUD (not monitored) and
`agent_error` to the backend; the next good frame clears it (`agent_recovered`). A smoothed FPS below
`hud.low_fps_below` for `hud.low_fps_s` = `low_fps` (alerts may be late) until it is back up
(`fps_restored`). Only the error's class name is logged, never data.

Heartbeat (M33): every `publisher.heartbeat_interval_s` of the caller's clock, and at once when the
monitoring state changes, a "heartbeat" record says the trip is alive and in which state
(MONITOR_STATES). `idle(clock)` keeps it going while no frame arrives (camera lost, loop stuck): after
`publisher.heartbeat_stalled_s` without a frame the state is "stalled". The end of the trip sends "ended",
so the backend can tell a finished trip from a device that went quiet.

Phone detector health (M50): with `phone_expected`, frames without a fresh block 4 result are
counted (PhoneHealth); most of a window unknown = `phone_detection_lost` on the HUD and to the
backend, until results come back (`phone_detection_restored`). Alerts of the other branches go on.

Road pose recalibrated (M80): block 8 took a head pose held off road for a long time as the road pose
(its baseline was wrong); `road_pose_recalibrated` tells the backend when, so a trip that began with
false "off road" alerts can be read for what it was.

A caller that times its own loop sets `perf` (publisher.perf_record, M49): it goes out with every
heartbeat, so a slow device says which stage is slow. Numbers only.

Every event carries `tags` (M41): "simulated" while the vehicle signals are not a real CAN bus
(today: always), so no number from a simulated drive can pass for a real one; and `versions`, what
this device runs (edge_agent/version.py), also in every heartbeat. No code path here forces a state
by hand: the "forced" tag of the PRD exists for the HUD preview page, which never sends anything.

Thresholds reloaded during the trip (M47): `apply_thresholds`, called by the device loop / the page
only while `parked`, restarts blocks 7, 8, 12 on the new numbers (the driver stays enrolled, the
summary goes on) and sends `config_applied` with the new version, or `config_refused`. `parked` is a
rest (block 10: standing still for context.rest_after_s), not any stop: at a red light the restart
would wipe what the drowsiness side knows about a driver who drives on in seconds (M79). A version
that changes a section the running trip cannot take (anything outside the pipeline's RELOADABLE:
capture, context, quality, ...) is refused whole, so `config_applied` and the version reported
always mean "exactly these thresholds are in use"; it is applied when the agent next starts.

Records go to `emit(kind, data)` with kind "event", "sample", "feedback", "summary" or "heartbeat": the device
hands them to MetadataPublisher, the browser queues them for its own POST. The callers keep only
their own I/O: camera, HTTP servers and preview window on the device, Pyodide on the web.

What the HUD shows of the running trip (M65) is read from the agent, not counted by the screen, so a
HUD that reloads loses nothing: continuous driving of the current driver and the drowsy_score of the
last `hud.trend_minutes` minutes (block 11's TripCollector.hud_view), the numbers behind each alert
(`alert_detail`), and since when the driver is not monitored (camera lost / processing error) with
the id of the system event sent for it; the device loop adds reopen attempts and whether the
backend has the event. The trip summary is built from the same collector, unchanged.

Pure logic on the timestamps it is given (plus a monotonic clock for camera-lost time): no
image, testable with fake sequences.
"""

from __future__ import annotations

import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from edge_agent.context.can_sim import CanSimulator, ExternalVehicle, VehicleSignals, hud_vehicle
from edge_agent.context.vehicle_context import ContextConfig
from edge_agent.decision.pipeline import RELOADABLE, DecisionPipeline, DecisionResult
from edge_agent.decision.presence import NO_ANSWER
from edge_agent.hud.server import HudConfig, HudState, hud_display
from edge_agent.io.publisher import (
    PublisherConfig,
    build_enrolled_event,
    build_event,
    build_feedback,
    build_heartbeat,
    build_sample,
    build_system_event,
)
from edge_agent.perception.features import FrameFeatures
from edge_agent.perception.landmarks import DriverSelector
from edge_agent.perception.phone_detector import PhoneDetectorConfig, PhoneHealth

Emit = Callable[[str, dict[str, Any]], None]

# Monitoring state in a heartbeat, most specific first (backend/schemas.py MonitorState).
MONITOR_STATES = ("ended", "camera_lost", "stalled", "error", "unavailable", "monitoring")


def new_trip_id(now: datetime | None = None) -> str:
    """Id of a new trip (the page's is frontend/src/live/tripId.ts). The local date and time are for a
    person reading it; the random part makes it unique, because a wrong clock or a changed time zone
    can give the same second twice and the backend keys a trip summary on (device_id, trip_id) (M82)."""
    return f"{(now or datetime.now()).strftime('trip-%Y%m%d-%H%M%S')}-{secrets.token_hex(3)}"


def alert_detail(r: DecisionResult, signals: VehicleSignals) -> dict[str, Any]:
    """The numbers behind an alert, for its detail line on the HUD (M65): how long the driver looked
    away, how long the eyes were closed, the phone share of the last 2 s, and the turn signal side
    (block 10, with its grace period) when it fired. Numbers only."""
    side = r.context.turn_side or signals.turn_signal
    return {
        "off_road_s": round(r.distraction.off_road_duration, 1),
        "eyes_closed_s": round(r.drowsiness.closed_duration, 1),
        "phone_ratio": round(r.distraction.phone_ratio_2s, 2),
        "turn_signal": side,
    }


@dataclass(frozen=True)
class FrameStep:
    result: DecisionResult
    signals: VehicleSignals
    event_id: str | None = None  # id of the alert raised on this frame, if any
    unavailable_changed: bool = False  # monitoring just became unavailable / was restored (FR-6)


class TripRuntime:
    """One trip: decisions, HUD state and metadata records. `t` is the caller's frame clock in seconds."""

    def __init__(
        self,
        thresholds: dict[str, Any],
        trip_id: str,
        vehicle: CanSimulator | ExternalVehicle,
        vehicle_source: str,
        selector: DriverSelector,
        emit: Emit | None = None,
        versions: dict[str, Any] | None = None,
        simulated: bool = True,
        phone_expected: bool = False,
    ) -> None:
        """versions: edge_agent.version.version_info(), sent with heartbeats and events (None: left out).
        simulated: the vehicle signals are simulated (no real CAN reader exists yet).
        phone_expected: block 4 is meant to run, so frames without a fresh result are watched (M50);
        False where it is switched off on purpose."""
        self.versions = versions
        self.perf: dict[str, Any] | None = None  # the caller's loop timings (publisher.perf_record), M49
        self.tags = ["simulated"] if simulated else []
        self.trip_id = trip_id
        self.vehicle = vehicle
        self.vehicle_source = vehicle_source  # shown on the HUD: "sim" or the scenario name
        self.selector = selector
        self._emit = emit
        self.stationary_kmh = ContextConfig.from_dict(thresholds.get("context")).stationary_kmh
        self.decisions = DecisionPipeline(thresholds)
        self.hud = HudState(HudConfig.from_dict(thresholds.get("hud")), hud_display(thresholds))
        self.started_at = datetime.now(UTC)
        self.fps = 0.0
        self.last_speed: float | None = None
        self._t0: float | None = None
        self._last_clock: float | None = None
        self._unavailable = False
        self._th = thresholds  # in use: what a reloaded version is compared with
        self._resting = False  # block 10 on the last frame: a rest, when new thresholds may be applied
        self._bins_sent = 0
        self._minute_max_level = 0
        self._minute_max_ratio = 0.0  # highest off_road_ratio (block 8) of the running minute
        self._lost_since: float | None = None  # monotonic time the camera was lost
        self._camera_lost_s = 0.0
        self._hud_cfg = HudConfig.from_dict(thresholds.get("hud"))
        self._failing_since: float | None = None  # frame time of the first failing frame in a row
        self._processing_error = False
        self.last_error: str | None = None  # class name of the last frame error (for the device log)
        self._low_fps_since: float | None = None
        self._low_fps = False
        self.phone_expected = phone_expected
        self._phone_health = PhoneHealth(PhoneDetectorConfig.from_dict(thresholds.get("phone")))
        self._signal_lost = False  # the vehicle link went quiet while driving (speed unknown)
        self._signal_lost_s = 0.0
        self._last_t: float | None = None
        self._pub_cfg = PublisherConfig.from_dict(thresholds.get("publisher"))
        self._clock: float | None = None  # latest caller clock seen (frames and idle calls)
        self._frame_clock: float | None = None  # ... of the last frame, good or failed
        self._beat_clock: float | None = None  # ... of the last periodic heartbeat
        self._beat_state: str | None = None
        self._ended = False
        self.hud.set_vehicle(self._vehicle_state(None))

    @property
    def started(self) -> bool:
        """At least one frame was processed (there is a trip to summarise)."""
        return self._t0 is not None

    def _record(self, kind: str, data: dict[str, Any]) -> None:
        if self._emit is None:
            return
        if kind == "event":
            data = {**data, "tags": list(self.tags)}
            if self.versions is not None:
                data["versions"] = self.versions
        self._emit(kind, data)

    def _system_event(self, reason: str, metrics: dict[str, Any] | None = None) -> str:
        """Returns the event_id (the HUD tells the driver once the backend has it, M65)."""
        event = build_system_event(reason, self.trip_id, self.last_speed, metrics=metrics)
        self._record("event", event)
        return event["event_id"]

    def _vehicle_state(self, signals: VehicleSignals | None) -> dict[str, Any]:
        connected = self.vehicle.connected if isinstance(self.vehicle, ExternalVehicle) else True
        return hud_vehicle(self.vehicle_source, connected, signals, self.stationary_kmh, self._signal_lost)

    def _track_vehicle_signal(self, t: float) -> None:
        """Vehicle link lost (driving or parked) / back: system event, and the lost time for the summary.
        Lost while driving the speed is unknown (monitored as moving); lost while parked it stays parked
        until a reading says the vehicle moves."""
        lost = isinstance(self.vehicle, ExternalVehicle) and self.vehicle.link_lost
        if lost and self._signal_lost and self._last_t is not None and t > self._last_t:
            self._signal_lost_s += t - self._last_t
        if lost != self._signal_lost:
            self._signal_lost = lost
            self._system_event("vehicle_signal_lost" if lost else "vehicle_signal_restored")

    # ------------------------------------------------------------------ heartbeat (M33)
    def monitor_state(self) -> str:
        """One of MONITOR_STATES: what the fleet overview shows for this vehicle."""
        if self._ended:
            return "ended"
        if self._lost_since is not None:
            return "camera_lost"
        stalled_s = self._pub_cfg.heartbeat_stalled_s
        if self._frame_clock is None or (self._clock is not None and self._clock - self._frame_clock >= stalled_s):
            return "stalled"
        if self._processing_error:
            return "error"
        return "unavailable" if self._unavailable else "monitoring"

    def _heartbeat(self, force: bool = False) -> None:
        """Emit a heartbeat when one is due, or when the monitoring state changed (or `force`)."""
        interval = self._pub_cfg.heartbeat_interval_s
        if interval <= 0:
            return
        state = self.monitor_state()
        due = self._beat_clock is None or (self._clock is not None and self._clock - self._beat_clock >= interval)
        if not (force or due or state != self._beat_state):
            return
        if due:
            self._beat_clock = self._clock
        self._beat_state = state
        moving = None if self.last_speed is None else self.last_speed >= self.stationary_kmh
        self._record("heartbeat", build_heartbeat(state, self.trip_id, moving, versions=self.versions, perf=self.perf))

    def idle(self, clock: float) -> None:
        """No frame right now (camera lost, waiting): keep the heartbeat going. Same clock as `step`."""
        self._clock = clock
        self._heartbeat()

    # ------------------------------------------------------------------ per frame
    def step(
        self,
        features: FrameFeatures,
        phone_flag: bool | None,
        t: float,
        clock: float | None = None,
        phone_kind: str | None = None,
    ) -> FrameStep:
        """One frame at time t. clock: what the FPS is measured on (the device's wall clock), default t.
        phone_kind: how the phone is held on this frame (block 4), recorded only."""
        if self._t0 is None:
            self._t0 = t
        signals = self.vehicle.sample(t - self._t0)  # 10 (CAN)
        self.last_speed = signals.speed_kmh
        self._track_vehicle_signal(t)
        self._last_t = t
        r = self.decisions.step(features, phone_flag, signals, phone_kind)  # 6 enrollment, 7, 8, 10, 11, 9, 12
        self._resting = r.context.resting
        changed = r.risk.unavailable != self._unavailable
        if changed:  # 9: face lost or unusable while moving / back (FR-6)
            self._unavailable = r.risk.unavailable
            if self._unavailable:
                self._system_event("monitoring_unavailable", {"cause": r.risk.unavailable_reason})
            else:
                self._system_event("monitoring_restored")
        self.hud.set_vehicle(self._vehicle_state(signals))  # 0 km/h = parked
        if r.distraction.recalibrated:  # 8: the road pose was wrong, set again (M80)
            self._system_event("road_pose_recalibrated")
        if r.presence.event == NO_ANSWER:  # 12: asked "Bạn còn ở đó không?", nobody answered (M44)
            self._system_event(NO_ANSWER)
        if "enrolled" in r.enrollment.events and r.enrollment.profile is not None:
            self.selector.set_anchor(r.enrollment.profile.anchor)  # 3: who the driver is
            self._record("event", build_enrolled_event(r, self.trip_id))

        clock = t if clock is None else clock
        self._clock = self._frame_clock = clock
        if self._last_clock is not None and clock > self._last_clock:
            dt = clock - self._last_clock
            keep = self._hud_cfg.fps_smoothing
            self.fps = 1.0 / dt if self.fps == 0 else keep * self.fps + (1.0 - keep) / dt
        self._last_clock = clock
        self._frame_ok()
        self._track_fps(clock)
        self._track_phone(t, phone_flag is not None)

        self.hud.update(r, self.fps, self.decisions.trip_log.hud_view(self._hud_cfg.trend_minutes))  # 13
        self._minute_max_level = max(self._minute_max_level, r.alert.active_level)
        self._minute_max_ratio = max(self._minute_max_ratio, r.distraction.off_road_ratio)
        event_id = None
        if r.alert.new_alert is not None:  # 13, 14
            event = build_event(r.alert.new_alert, r, self.trip_id)
            event_id = event["event_id"]
            self.hud.add_alert(event_id, r.alert.new_alert.level, r.alert.new_alert.reasons, alert_detail(r, signals))
            self._record("event", event)
        if r.trip.bins_completed < self._bins_sent:  # trip memory started again (driver change, reload, M79)
            self._bins_sent = r.trip.bins_completed
            self._minute_max_level = r.alert.active_level
            self._minute_max_ratio = r.distraction.off_road_ratio
        if r.trip.bins_completed > self._bins_sent:  # a minute just closed: one fatigue timeline point
            self._bins_sent = r.trip.bins_completed
            if r.trip.minute_scores:
                sample = build_sample(
                    r.trip.minute_scores[-1],
                    r.drowsiness.perclos_60s,
                    self._minute_max_level,
                    self.trip_id,
                    off_road_ratio=self._minute_max_ratio,
                )
                self._record("sample", sample)
            self._minute_max_level = r.alert.active_level
            self._minute_max_ratio = r.distraction.off_road_ratio
        self._heartbeat()  # 14: still alive
        return FrameStep(r, signals, event_id, changed)

    # ------------------------------------------------------------------ loop health (M28)
    def frame_failed(self, t: float, error: str, clock: float | None = None) -> None:
        """A frame failed in blocks 2-14 (the caller caught it and goes on). t: its frame time;
        clock: as in `step` (default t)."""
        self.last_error = error
        self._clock = self._frame_clock = t if clock is None else clock
        if self._failing_since is None:
            self._failing_since = t
        if not self._processing_error and t - self._failing_since >= self._hud_cfg.processing_error_s:
            self._processing_error = True
            self.hud.set_processing_error(True)
            self.hud.start_incident("processing_error", self._system_event("agent_error"))
        self._heartbeat()

    def _frame_ok(self) -> None:
        self._failing_since = None
        self.last_error = None
        if self._processing_error:
            self._processing_error = False
            self.hud.set_processing_error(False)
            self.hud.end_incident("processing_error")
            self._system_event("agent_recovered")

    def _track_fps(self, clock: float) -> None:
        cfg = self._hud_cfg
        if self.fps <= 0 or self.fps >= cfg.low_fps_below:
            self._low_fps_since = None
            if self._low_fps:
                self._low_fps = False
                self.hud.set_low_fps(False)
                self._system_event("fps_restored", {"fps": round(self.fps, 1)})
            return
        if self._low_fps_since is None:
            self._low_fps_since = clock
        if not self._low_fps and clock - self._low_fps_since >= cfg.low_fps_s:
            self._low_fps = True
            self.hud.set_low_fps(True)
            self._system_event("low_fps", {"fps": round(self.fps, 1)})

    def _track_phone(self, t: float, known: bool) -> None:
        """Block 4 gives no fresh results for most of a while (M50): phones are not detected, and
        nothing else would say so. The HUD shows it, the backend gets the event; back = restored."""
        if not self.phone_expected:
            return
        was = self._phone_health.unavailable
        now = self._phone_health.update(t, known)
        if now != was:
            self.hud.set_phone_unavailable(now)
            share = round(self._phone_health.unknown_share, 2)
            self._system_event(
                "phone_detection_lost" if now else "phone_detection_restored", {"phone_unknown_ratio": share}
            )

    # ------------------------------------------------------------------ HUD buttons, camera status
    @property
    def parked(self) -> bool:
        """The driver is resting (block 10 `resting` on the last frame), or no frame was processed yet:
        new thresholds may be applied. A shorter stop (a red light) is not enough, see the module doc."""
        return self._resting if self.started else True

    def needs_restart(self, thresholds: dict[str, Any]) -> list[str]:
        """Sections in which `thresholds` differ from the ones in use and that a running trip cannot take."""
        old = self._th
        return sorted(k for k in {*old, *thresholds} if k not in RELOADABLE and old.get(k) != thresholds.get(k))

    def apply_thresholds(self, thresholds: dict[str, Any], version: int, refused: bool = False) -> bool:
        """Thresholds reloaded from the backend (M47), between two frames, only while `parked`.
        refused: the version was inconsistent, the thresholds in use stay; the backend still learns
        which version this device runs (heartbeat and events) and that it ignored one. A version
        that `needs_restart` is refused the same way. Returns whether it is now in use."""
        refused = refused or bool(self.needs_restart(thresholds))
        if not refused:
            self.decisions.reconfigure(thresholds)
            self._th = thresholds
            self.hud.display = hud_display(thresholds)  # the screen follows the rules it shows
        if self.versions is not None:
            self.versions = {
                **self.versions,
                "thresholds_version": self.versions["thresholds_version"] if refused else version,
                "thresholds_ignored": refused,
            }
        self._system_event("config_refused" if refused else "config_applied")
        self._heartbeat(force=True)
        return not refused

    def change_driver(self) -> None:
        """ "Đổi tài xế": drop the previous driver's baselines and block 3's anchor; the new driver enrolls."""
        self.decisions.change_driver()
        self.selector.set_anchor(None)  # block 3: the largest face until the new driver enrolls
        self._system_event("driver_changed")

    def enrollment_answer(self, agree: bool) -> bool:
        """Enrollment consent screen: "Đồng ý" (the steps start) or "Để sau" (asked at the next stop)."""
        return self.decisions.enrollment_answer(agree)

    def presence_answer(self) -> None:
        """The driver tapped the HUD's "Bạn còn ở đó không?" (M44)."""
        self.decisions.presence_answer()

    def false_alarm(self, event_id: str) -> str:
        """The driver pressed "false alarm": 'ok', 'unknown', 'expired' or 'duplicate'."""
        result = self.hud.mark_false_alarm(event_id)
        if result == "ok":
            self.record_feedback(event_id)
        return result

    def record_feedback(self, event_id: str) -> None:
        """A false alarm already marked on the HUD state (the device's HUD server does that itself)."""
        self._record("feedback", build_feedback(event_id))

    def camera(self, lost: bool) -> None:
        """Camera lost / back: the HUD shows it and the dashboard learns the driver is (not) monitored."""
        self.hud.set_camera_lost(lost)
        if lost:
            self._lost_since = time.monotonic()
        elif self._lost_since is not None:
            self._camera_lost_s += time.monotonic() - self._lost_since
            self._lost_since = None
        event_id = self._system_event("camera_lost" if lost else "camera_restored")
        if lost:
            self.hud.start_incident("camera_lost", event_id)
        else:
            self.hud.end_incident("camera_lost")
        self._heartbeat()

    # ------------------------------------------------------------------ end of trip
    def end_trip(self) -> dict[str, Any]:
        """Block 11's trip summary, also recorded for the backend."""
        lost = self._camera_lost_s + (time.monotonic() - self._lost_since if self._lost_since is not None else 0.0)
        summary = self.decisions.trip_log.summary(
            self.trip_id,
            self.started_at,
            datetime.now(UTC),
            false_alarms=self.hud.false_alarms,
            camera_lost_s=lost,
            vehicle_signal_lost_s=self._signal_lost_s,
        ).to_dict()
        self._record("summary", summary)
        self._ended = True
        self._heartbeat(force=True)  # "ended": a finished trip, not a device that went quiet
        return summary
