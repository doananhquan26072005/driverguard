"""One trip around blocks 6-14, shared by the device (edge_agent.main) and the browser (edge_agent.web.bridge).

Per frame, from the features of blocks 3-6: block 10 samples the vehicle (a link to the vehicle that
goes quiet while driving is a lost signal: the driver and the backend are told, and its time goes in
the summary), the DecisionPipeline
runs blocks 6 (enrollment) to 12, block 3's driver anchor is set once the driver is enrolled, the
HUD state (block 13) is updated, and the metadata records of block 14 are built. Between frames:
"Đổi tài xế", camera lost / back, "false alarm", and the end of the trip (block 11's summary).

HUD buttons between frames also include the enrollment consent answer (`enrollment_answer`).

Loop health (M28): a frame that fails anywhere in blocks 2-14 goes to `frame_failed` (the callers catch
it and go on). Failing for `hud.processing_error_s` = "processing error" on the HUD (not monitored) and
`agent_error` to the backend; the next good frame clears it (`agent_recovered`). A smoothed FPS below
`hud.low_fps_below` for `hud.low_fps_s` = `low_fps` (alerts may be late) until it is back up
(`fps_restored`). Only the error's class name is logged, never data.

Records go to `emit(kind, data)` with kind "event", "sample", "feedback" or "summary": the device
hands them to MetadataPublisher, the browser queues them for its own POST. The callers keep only
their own I/O: camera, HTTP servers and preview window on the device, Pyodide on the web.

Pure logic on the timestamps it is given (plus a monotonic clock for camera-lost time): no
image, testable with fake sequences.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from edge_agent.context.can_sim import CanSimulator, ExternalVehicle, VehicleSignals, hud_vehicle
from edge_agent.context.vehicle_context import ContextConfig
from edge_agent.decision.pipeline import DecisionPipeline, DecisionResult
from edge_agent.hud.server import HudConfig, HudState
from edge_agent.io.publisher import (
    build_enrolled_event,
    build_event,
    build_feedback,
    build_sample,
    build_system_event,
)
from edge_agent.perception.features import FrameFeatures
from edge_agent.perception.landmarks import DriverSelector

Emit = Callable[[str, dict[str, Any]], None]


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
    ) -> None:
        self.trip_id = trip_id
        self.vehicle = vehicle
        self.vehicle_source = vehicle_source  # shown on the HUD: "sim" or the scenario name
        self.selector = selector
        self._emit = emit
        self.stationary_kmh = ContextConfig.from_dict(thresholds.get("context")).stationary_kmh
        self.decisions = DecisionPipeline(thresholds)
        self.hud = HudState(HudConfig.from_dict(thresholds.get("hud")))
        self.started_at = datetime.now(UTC)
        self.fps = 0.0
        self.last_speed: float | None = None
        self._t0: float | None = None
        self._last_clock: float | None = None
        self._unavailable = False
        self._bins_sent = 0
        self._minute_max_level = 0
        self._lost_since: float | None = None  # monotonic time the camera was lost
        self._camera_lost_s = 0.0
        self._hud_cfg = HudConfig.from_dict(thresholds.get("hud"))
        self._failing_since: float | None = None  # frame time of the first failing frame in a row
        self._processing_error = False
        self.last_error: str | None = None  # class name of the last frame error (for the device log)
        self._low_fps_since: float | None = None
        self._low_fps = False
        self._signal_lost = False  # the vehicle link went quiet while driving (speed unknown)
        self._signal_lost_s = 0.0
        self._last_t: float | None = None
        self.hud.set_vehicle(self._vehicle_state(None))

    @property
    def started(self) -> bool:
        """At least one frame was processed (there is a trip to summarise)."""
        return self._t0 is not None

    def _record(self, kind: str, data: dict[str, Any]) -> None:
        if self._emit is not None:
            self._emit(kind, data)

    def _system_event(self, reason: str, metrics: dict[str, Any] | None = None) -> None:
        self._record("event", build_system_event(reason, self.trip_id, self.last_speed, metrics=metrics))

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

    # ------------------------------------------------------------------ per frame
    def step(self, features: FrameFeatures, phone_flag: bool | None, t: float, clock: float | None = None) -> FrameStep:
        """One frame at time t. clock: what the FPS is measured on (the device's wall clock), default t."""
        if self._t0 is None:
            self._t0 = t
        signals = self.vehicle.sample(t - self._t0)  # 10 (CAN)
        self.last_speed = signals.speed_kmh
        self._track_vehicle_signal(t)
        self._last_t = t
        r = self.decisions.step(features, phone_flag, signals)  # 6 enrollment, 7, 8, 10, 11, 9, 12
        changed = r.risk.unavailable != self._unavailable
        if changed:  # 9: face lost while moving / back (FR-6)
            self._unavailable = r.risk.unavailable
            self._system_event("monitoring_unavailable" if self._unavailable else "monitoring_restored")
        self.hud.set_vehicle(self._vehicle_state(signals))  # 0 km/h = parked
        if "enrolled" in r.enrollment.events and r.enrollment.profile is not None:
            self.selector.set_anchor(r.enrollment.profile.anchor)  # 3: who the driver is
            self._record("event", build_enrolled_event(r, self.trip_id))

        clock = t if clock is None else clock
        if self._last_clock is not None and clock > self._last_clock:
            dt = clock - self._last_clock
            self.fps = 1.0 / dt if self.fps == 0 else 0.9 * self.fps + 0.1 / dt
        self._last_clock = clock
        self._frame_ok()
        self._track_fps(clock)

        self.hud.update(r, self.fps)  # 13
        self._minute_max_level = max(self._minute_max_level, r.alert.active_level)
        event_id = None
        if r.alert.new_alert is not None:  # 13, 14
            event = build_event(r.alert.new_alert, r, self.trip_id)
            event_id = event["event_id"]
            self.hud.add_alert(event_id, r.alert.new_alert.level, r.alert.new_alert.reasons)
            self._record("event", event)
        if r.trip.bins_completed > self._bins_sent:  # a minute just closed: one fatigue timeline point
            self._bins_sent = r.trip.bins_completed
            if r.trip.minute_scores:
                sample = build_sample(
                    r.trip.minute_scores[-1], r.drowsiness.perclos_60s, self._minute_max_level, self.trip_id
                )
                self._record("sample", sample)
            self._minute_max_level = r.alert.active_level
        return FrameStep(r, signals, event_id, changed)

    # ------------------------------------------------------------------ loop health (M28)
    def frame_failed(self, t: float, error: str) -> None:
        """A frame failed in blocks 2-14 (the caller caught it and goes on). t: its frame time."""
        self.last_error = error
        if self._failing_since is None:
            self._failing_since = t
        if not self._processing_error and t - self._failing_since >= self._hud_cfg.processing_error_s:
            self._processing_error = True
            self.hud.set_processing_error(True)
            self._system_event("agent_error")

    def _frame_ok(self) -> None:
        self._failing_since = None
        self.last_error = None
        if self._processing_error:
            self._processing_error = False
            self.hud.set_processing_error(False)
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

    # ------------------------------------------------------------------ HUD buttons, camera status
    def change_driver(self) -> None:
        """ "Đổi tài xế": drop the previous driver's baselines and block 3's anchor; the new driver enrolls."""
        self.decisions.change_driver()
        self.selector.set_anchor(None)  # block 3: the largest face until the new driver enrolls
        self._system_event("driver_changed")

    def enrollment_answer(self, agree: bool) -> bool:
        """Enrollment consent screen: "Đồng ý" (the steps start) or "Để sau" (asked at the next stop)."""
        return self.decisions.enrollment_answer(agree)

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
        self._system_event("camera_lost" if lost else "camera_restored")

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
        return summary
