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
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from edge_agent.analysis.distraction import DistractionAnalyzer, DistractionConfig, DistractionState
from edge_agent.analysis.drowsiness import DrowsinessAnalyzer, DrowsinessConfig, DrowsinessState
from edge_agent.context.can_sim import VehicleSignals
from edge_agent.context.vehicle_context import ContextConfig, ContextTracker, VehicleContext
from edge_agent.decision.alert_manager import AlertConfig, AlertManager, AlertOutput
from edge_agent.decision.risk_engine import RiskAssessment, RiskConfig, RiskEngine
from edge_agent.decision.trip_memory import TripMemory, TripMemoryConfig, TripState
from edge_agent.decision.trip_summary import TripCollector, TripSummaryConfig
from edge_agent.perception.enrollment import DriverEnrollment, EnrollmentConfig, EnrollmentState
from edge_agent.perception.features import FrameFeatures


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


class DecisionPipeline:
    def __init__(self, thresholds: dict[str, Any] | None = None) -> None:
        th = self._th = thresholds or {}
        self._new_driver()
        self.context = ContextTracker(ContextConfig.from_dict(th.get("context")))
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
        self._closing_from: float | None = None  # start of enrollment's close_eyes step
        self._closing_until: float | None = None  # ... its end + reopen_grace_s
        self._trip_state: TripState | None = None

    def enrollment_answer(self, agree: bool) -> bool:
        """The driver's answer on the HUD's enrollment consent screen ("Đồng ý" / "Để sau").
        False when the HUD was not asking."""
        return self.enrollment.consent(agree)

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
            p = e.profile
            self.drowsiness.set_profile(
                p.ear_open, p.mar_closed, p.road_yaw, p.road_pitch, ear_closed=p.ear_closed, brow_neutral=p.brow_neutral
            )
            self.distraction.set_road_pose(p.road_yaw, p.road_pitch)

    def step(self, features: FrameFeatures, phone_near_face: bool | None, signals: VehicleSignals) -> DecisionResult:
        ctx = self.context.update(signals)
        self._track_rest(ctx, features.timestamp)
        enrollment = self.enrollment.update(features, ctx.stationary)
        self._track_enrollment(enrollment, features.timestamp)
        closing_eyes = self._closing_from is not None
        drowsy = self.drowsiness.update(features)
        distraction = self.distraction.update(features, phone_near_face, ctx.moving, ctx.turn_side, drowsy.gaze_down)
        risk = self.risk.assess(drowsy, distraction, ctx, self._trip_state, drowsy_muted=closing_eyes)
        alert = self.alerts.update(risk)
        if alert.new_alert is not None:
            self.trip.record_alert(alert.new_alert.level)
        observed = not (ctx.resting or closing_eyes)
        self._trip_state = self.trip.update(features.timestamp, risk.drowsy_score, drowsy.events, observed=observed)
        result = DecisionResult(drowsy, distraction, ctx, self._trip_state, risk, alert, enrollment, observed)
        self.trip_log.update(result)
        return result
