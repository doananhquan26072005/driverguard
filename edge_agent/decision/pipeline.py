"""Blocks 7-12 wired together, without images.

One call per frame: FrameFeatures + phone flag + vehicle signals -> everything the HUD
and (later) the metadata publisher need. Used by edge_agent/main.py and by the M4
scenario tests, so the whole decision chain is testable with fake sequences.

A rest (block 10: parked for context.rest_after_s) is kept out of the drowsiness evidence:
its frames are not binned by trip memory, and once the vehicle moves again, what the
drowsiness branch and trip memory gathered since it stopped is dropped. Without this,
eyes closed to rest would raise a drowsiness alert on the first seconds of the next drive.

Driver enrollment (block 6 stage) runs here too, since it needs block 10's "standing still".
Once it is done its profile goes to blocks 7 and 8 (block 3 gets it from the caller, which
owns the face detector). While it asks the driver to close the eyes, and for
enrollment.reopen_grace_s after (the driver opens them on the beep), drowsiness alerts are
off, those frames are not binned by trip memory, and what they fed block 7 is dropped, as
after a rest.

Driver change ("Đổi tài xế" on the HUD, `change_driver`): everything learnt about the previous
driver is dropped (eye / mouth / pose baselines, PERCLOS, blinks, trend, road pose, enrollment)
and the new driver enrolls. The vehicle context and the whole-trip summary (block 11) go on.

Presence check (block 12 stage, M44): while monitoring is unavailable because the driver is out of
view, the HUD asks "Bạn còn ở đó không?"; `presence_answer` is the driver's tap.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from edge_agent.analysis.distraction import DistractionAnalyzer, DistractionConfig, DistractionState
from edge_agent.analysis.drowsiness import DrowsinessAnalyzer, DrowsinessConfig, DrowsinessState
from edge_agent.context.can_sim import VehicleSignals
from edge_agent.context.vehicle_context import ContextConfig, ContextTracker, VehicleContext
from edge_agent.decision.alert_manager import AlertConfig, AlertManager, AlertOutput
from edge_agent.decision.presence import PresenceCheck, PresenceConfig, PresenceState
from edge_agent.decision.risk_engine import RiskAssessment, RiskConfig, RiskEngine
from edge_agent.decision.trip_memory import TripMemory, TripMemoryConfig, TripState
from edge_agent.decision.trip_summary import TripCollector, TripSummaryConfig
from edge_agent.perception.enrollment import DriverEnrollment, DriverProfile, EnrollmentConfig, EnrollmentState
from edge_agent.perception.features import FrameFeatures
from edge_agent.perception.quality import QualityConfig, QualityMonitor, QualityState


@dataclass(frozen=True)
class DecisionResult:
    drowsiness: DrowsinessState
    distraction: DistractionState
    context: VehicleContext
    trip: TripState
    risk: RiskAssessment
    alert: AlertOutput
    enrollment: EnrollmentState
    # False while drowsiness is not judged: a rest (parked), or enrollment's eyes-closed step and its
    # reopen grace. Blocks 11 (trip memory, trip summary) skip these frames' drowsiness signs.
    observed: bool = True
    quality: QualityState = QualityState()  # block 6 stage: is the frame usable (FR-6)
    presence: PresenceState = PresenceState()  # block 12 stage: "Bạn còn ở đó không?" (M44)


class DecisionPipeline:
    def __init__(self, thresholds: dict[str, Any] | None = None) -> None:
        th = self._th = thresholds or {}
        self._new_driver()
        self.context = ContextTracker(ContextConfig.from_dict(th.get("context")))
        self.quality = QualityMonitor(QualityConfig.from_dict(th.get("quality")))  # the camera's, not the driver's
        self.risk = RiskEngine(RiskConfig.from_dict(th.get("risk")))
        self.trip_log = TripCollector(  # block 11 stage: the end-of-trip summary
            TripSummaryConfig.from_dict(th.get("trip_summary")),
            tired_score=self.risk.config.drowsy_l1,
            long_drive_s=self.context.config.long_drive_s,
            score_l2=self.risk.config.drowsy_l2,
        )
        self._rest_from: float | None = None  # frame time the vehicle stopped, once the stop is a rest

    def _new_driver(self) -> None:
        """Fresh per-driver state: blocks 7, 8, 11 (trip memory), 12 and enrollment."""
        th = self._th
        self.drowsiness = DrowsinessAnalyzer(DrowsinessConfig.from_dict(th.get("drowsiness")))
        self.distraction = DistractionAnalyzer(DistractionConfig.from_dict(th.get("distraction")))
        dc, xc = self.drowsiness.config, self.distraction.config
        self.enrollment = DriverEnrollment(
            EnrollmentConfig.from_dict(th.get("enrollment")),
            ear_min=dc.eye_baseline_min,
            ear_max=dc.eye_baseline_max,
            road_max_deg=xc.baseline_calibrate_max_deg,
        )
        self.trip = TripMemory(TripMemoryConfig.from_dict(th.get("trip_memory")))
        self.alerts = AlertManager(AlertConfig.from_dict(th.get("alert")))
        self.presence = PresenceCheck(PresenceConfig.from_dict(th.get("presence")))
        self._presence_ack = False  # the driver tapped the HUD's question since the last frame
        self._closing_from: float | None = None  # start of enrollment's close_eyes step
        self._closing_until: float | None = None  # ... its end + reopen_grace_s
        self._trip_state: TripState | None = None

    def enrollment_answer(self, agree: bool) -> bool:
        """The driver's answer on the HUD's enrollment consent screen ("Đồng ý" / "Để sau").
        False when the HUD was not asking."""
        return self.enrollment.consent(agree)

    def presence_answer(self) -> None:
        """The driver tapped "Tôi vẫn ở đây" on the HUD; taken by the next frame."""
        self._presence_ack = True

    def change_driver(self) -> None:
        """Another driver took the wheel (see module doc). The caller clears block 3's anchor."""
        self._new_driver()
        self._rest_from = None
        self.trip_log.driver_changes += 1

    def _track_rest(self, ctx: VehicleContext, t: float) -> None:
        if ctx.resting:
            if self._rest_from is None:
                self._rest_from = t - ctx.stationary_s
        elif self._rest_from is not None and not ctx.stationary:  # driving off after a rest
            self.drowsiness.forget_since(self._rest_from)
            self.trip.forget_since(self._rest_from)
            self.alerts.forget_repeats()  # 12: the driver rested, repeated-L1 escalation starts again
            self._rest_from = None

    def _track_enrollment(self, e: EnrollmentState, t: float) -> None:
        if e.status == "close_eyes":
            if self._closing_from is None:
                self._closing_from = t
            self._closing_until = None
        elif self._closing_from is not None:  # the eyes-closed step is over (done, redone or aborted)
            if self._closing_until is None:
                self._closing_until = t + self.enrollment.config.reopen_grace_s
            if t >= self._closing_until:
                self.drowsiness.forget_since(self._closing_from)
                self._closing_from = self._closing_until = None
        if "enrolled" in e.events and e.profile is not None:
            self._apply_profile(e.profile)

    def _apply_profile(self, p: DriverProfile) -> None:
        """The enrolled driver's own baselines, for blocks 7 and 8."""
        self.drowsiness.set_profile(
            p.ear_open,
            p.mar_closed,
            p.road_yaw,
            p.road_pitch,
            ear_closed=p.ear_closed,
            brow_neutral=p.brow_neutral,
            blink_closed=p.blink_closed,
        )
        self.distraction.set_road_pose(p.road_yaw, p.road_pitch, p.road_iris_y)

    def reconfigure(self, thresholds: dict[str, Any]) -> None:
        """New thresholds between two frames (M47, engineers' tuned values reloaded from the backend).
        The caller only does this while the vehicle is parked: blocks 7, 8, 12 and trip memory start
        again on the new numbers, which while parked holds nothing an alert depends on (what a stop
        gathered is dropped when driving resumes anyway). The driver stays enrolled, the vehicle
        context and the whole-trip summary go on."""
        enrollment = self.enrollment
        self._th = thresholds
        self._new_driver()
        self.enrollment = enrollment  # consent given, steps done, attempts: all kept
        if enrollment.profile is not None:
            self._apply_profile(enrollment.profile)
        self.risk = RiskEngine(RiskConfig.from_dict(thresholds.get("risk")))
        self.trip_log.tired_score = self.risk.config.drowsy_l1
        self.trip_log.score_l2 = self.risk.config.drowsy_l2

    def step(
        self,
        features: FrameFeatures,
        phone_near_face: bool | None,
        signals: VehicleSignals,
        phone_kind: str | None = None,
    ) -> DecisionResult:
        ctx = self.context.update(signals)
        self._track_rest(ctx, features.timestamp)
        enrollment = self.enrollment.update(features, ctx.stationary)
        self._track_enrollment(enrollment, features.timestamp)
        closing_eyes = self._closing_from is not None
        quality = self.quality.update(features)
        drowsy = self.drowsiness.update(features)
        distraction = self.distraction.update(
            features, phone_near_face, ctx.moving, ctx.turn_side, drowsy.gaze_down, phone_kind, drowsy.deep_closed
        )
        risk = self.risk.assess(drowsy, distraction, ctx, self._trip_state, drowsy_muted=closing_eyes, quality=quality)
        if risk.unavailable:  # 8: nothing was judged, the glance window starts again
            self.distraction.clear_glances()
        alert = self.alerts.update(risk)
        out_of_view = risk.unavailable and risk.unavailable_reason == "no_face"
        presence = self.presence.update(features.timestamp, out_of_view, self._presence_ack)  # 12
        self._presence_ack = False
        if alert.new_alert is not None:
            self.trip.record_alert(alert.new_alert.level)
        observed = not (ctx.resting or closing_eyes)
        self._trip_state = self.trip.update(features.timestamp, risk.drowsy_score, drowsy.events, observed=observed)
        result = DecisionResult(
            drowsy, distraction, ctx, self._trip_state, risk, alert, enrollment, observed, quality, presence
        )
        self.trip_log.update(result)
        return result
