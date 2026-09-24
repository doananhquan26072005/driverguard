"""Blocks 7-12 wired together, without images.

One call per frame: FrameFeatures + phone flag + vehicle signals -> everything the HUD
and (later) the metadata publisher need. Used by edge_agent/main.py and by the M4
scenario tests, so the whole decision chain is testable with fake sequences.
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
from edge_agent.perception.features import FrameFeatures


@dataclass(frozen=True)
class DecisionResult:
    drowsiness: DrowsinessState
    distraction: DistractionState
    context: VehicleContext
    trip: TripState
    risk: RiskAssessment
    alert: AlertOutput


class DecisionPipeline:
    def __init__(self, thresholds: dict[str, Any] | None = None) -> None:
        th = thresholds or {}
        self.drowsiness = DrowsinessAnalyzer(DrowsinessConfig.from_dict(th.get("drowsiness")))
        self.distraction = DistractionAnalyzer(DistractionConfig.from_dict(th.get("distraction")))
        self.context = ContextTracker(ContextConfig.from_dict(th.get("context")))
        self.trip = TripMemory(TripMemoryConfig.from_dict(th.get("trip_memory")))
        self.risk = RiskEngine(RiskConfig.from_dict(th.get("risk")))
        self.alerts = AlertManager(AlertConfig.from_dict(th.get("alert")))
        self._trip_state: TripState | None = None

    def step(self, features: FrameFeatures, phone_near_face: bool | None, signals: VehicleSignals) -> DecisionResult:
        ctx = self.context.update(signals)
        drowsy = self.drowsiness.update(features)
        distraction = self.distraction.update(features, phone_near_face, ctx.speed_kmh)
        risk = self.risk.assess(drowsy, distraction, ctx, self._trip_state)
        alert = self.alerts.update(risk)
        if alert.new_alert is not None:
            self.trip.record_alert(alert.new_alert.level)
        self._trip_state = self.trip.update(features.timestamp, risk.drowsy_score, drowsy.events)
        return DecisionResult(drowsy, distraction, ctx, self._trip_state, risk, alert)
