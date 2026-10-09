"""Blocks 7-12 wired together, without images.

One call per frame: FrameFeatures + phone flag + vehicle signals -> everything the HUD
and (later) the metadata publisher need. Used by edge_agent/main.py and by the M4
scenario tests, so the whole decision chain is testable with fake sequences.

A rest (block 10: parked for context.rest_after_s) is kept out of the drowsiness evidence:
its frames are not binned by trip memory, and once the vehicle moves again, what the
drowsiness branch and trip memory gathered since it stopped is dropped. Without this,
eyes closed to rest would raise a drowsiness alert on the first seconds of the next drive.

A shorter stop of at least context.short_stop_forget_s (a red light, M73) is handled the same way
when the vehicle drives off: what blocks 7 and trip memory gathered since it stopped is dropped.
Standing still raises no alert (M30), and before M73 eyes closed at a red light only moved the alert
to the moment the vehicle rolled again, with the driver awake and looking at the road. Its frames
are still binned while it lasts (nobody knows yet how long it will be), and the repeated-L1
escalation of block 12 goes on: the driver has not rested. A stop shorter than that keeps everything.

Driver enrollment (block 6 stage) runs here too, since it needs block 10's "standing still".
Once it is done its profile goes to blocks 7 and 8 (block 3 gets it from the caller, which
owns the face detector). While it asks the driver to close the eyes, and for
enrollment.reopen_grace_s after (the driver opens them on the beep), drowsiness alerts are
off, drowsy_score reads 0, those frames are not binned by trip memory, and what they fed block 7
is dropped, as after a rest. When that step completed the enrollment, block 7 drops everything it
gathered so far instead: it was measured on the self-learnt baselines, and the enrolled driver
starts from zero on their own, and trip memory drops what it gathered since the vehicle stopped
(what it holds from driving before a late enrollment stays: a microsleep on the road still counts).

Driver change ("Đổi tài xế" on the HUD, `change_driver`): everything learnt about the previous
driver is dropped (eye / mouth / pose baselines, PERCLOS, blinks, trend, road pose, enrollment)
and the new driver enrolls, and their continuous driving (block 10 `drive_run_s`, what "long drive" is
judged on) starts at 0. The rest of the vehicle context and the whole-trip summary (block 11) go on.

Thresholds reloaded during the trip (`reconfigure`, M47): only the sections in RELOADABLE can change
under a running trip, and the caller applies them during a rest only (M79).

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

# Thresholds sections `reconfigure` puts into effect. A reloaded version that changes any other
# section cannot be applied during the trip (edge_agent.runtime.TripRuntime.apply_thresholds).
RELOADABLE = ("drowsiness", "distraction", "trip_memory", "alert", "presence", "risk")


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
            bin_s=TripMemoryConfig.from_dict(th.get("trip_memory")).bin_s,
        )
        self._stop_from: float | None = None  # frame time the vehicle stopped, once the stop is long enough to forget
        self._stop_rested = False  # ... and it became a rest

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
        self._closing_stop_from = 0.0  # when the vehicle stopped for that enrollment
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
        self._stop_from, self._stop_rested = None, False
        self.context.new_driver()
        self.trip_log.driver_changed()

    def _track_rest(self, ctx: VehicleContext, t: float) -> None:
        """Driving off after a rest or a long enough stop: drop what was gathered since the vehicle stopped."""
        if ctx.long_stop:
            if self._stop_from is None:
                self._stop_from = t - ctx.stationary_s
            self._stop_rested = self._stop_rested or ctx.resting
        elif self._stop_from is not None and not ctx.stationary:
            self.drowsiness.forget_since(self._stop_from)
            self.trip.forget_since(self._stop_from)
            if self._stop_rested:
                self.alerts.forget_repeats()  # 12: the driver rested, repeated-L1 escalation starts again
            self._stop_from, self._stop_rested = None, False

    def _track_enrollment(self, e: EnrollmentState, ctx: VehicleContext, t: float) -> None:
        if e.status == "close_eyes":
            if self._closing_from is None:
                self._closing_from = t
                self._closing_stop_from = t - ctx.stationary_s
            self._closing_until = None
        elif self._closing_from is not None:  # the eyes-closed step is over (done, redone or aborted)
            if self._closing_until is None:
                self._closing_until = t + self.enrollment.config.reopen_grace_s
            if t >= self._closing_until:
                if e.enrolled:  # the scores start from zero (see module doc)
                    self.drowsiness.forget_since(float("-inf"))
                    self.trip.forget_since(self._closing_stop_from)
                    self._trip_state = self.trip.update(t, 0.0, observed=False)  # block 9 reads it this frame
                else:  # the step is redone, or was aborted: only what it fed block 7 goes
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
        The caller only does this during a rest (block 10 `resting`, not a red light: M79): blocks 7, 8
        and 12 start again on the new numbers, and what they gathered since the vehicle stopped is
        dropped when driving resumes anyway. Trip memory goes on (microsleeps and the trend from before
        the rest still count) unless its own section changed. The driver stays enrolled, the vehicle
        context and the whole-trip summary go on. Only the RELOADABLE sections are read."""
        enrollment, trip, trip_state = self.enrollment, self.trip, self._trip_state
        keep_trip = thresholds.get("trip_memory") == self._th.get("trip_memory")
        self._th = thresholds
        self._new_driver()
        self.enrollment = enrollment  # consent given, steps done, attempts: all kept
        if keep_trip:
            self.trip, self._trip_state = trip, trip_state
        if enrollment.profile is not None:
            self._apply_profile(enrollment.profile)
        self.risk = RiskEngine(RiskConfig.from_dict(thresholds.get("risk")))
        self.trip_log.tired_score = self.risk.config.drowsy_l1
        self.trip_log.score_l2 = self.risk.config.drowsy_l2

    @property
    def max_gap_s(self) -> float:
        """Two frames further apart than this are a hole for blocks 7, 8 or 12: a running duration or
        confirmation starts again (M71). A loop whose every frame comes that late times nothing."""
        return min(self.drowsiness.config.max_gap_s, self.distraction.config.max_gap_s, self.alerts.config.max_gap_s)

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
        self._track_enrollment(enrollment, ctx, features.timestamp)
        closing_eyes = self._closing_from is not None
        quality = self.quality.update(features)
        drowsy = self.drowsiness.update(features, moving=ctx.moving)
        distraction = self.distraction.update(
            features,
            phone_near_face,
            ctx.moving,
            ctx.turn_side,
            drowsy.gaze_down,
            phone_kind,
            drowsy.deep_closed,
            rolling=ctx.rolling,
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
