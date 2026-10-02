"""Block 9 - Rule-based risk engine.

Rule table (docs/workflow/workflow_full_4.jpg):
- closed_duration >= microsleep_l3_s                    -> L3 (microsleep)
- drowsy_score = 40*perclos + 25*microsleep + 15*yawn + 20*nod + 10*slow_blink + 10*brow
  (terms 0..1, capped at 100; slow_blink / brow are v2 and temporary)
  >= l1 -> L1, >= l2 -> L2; multiplied by night / long-drive factors from context
- off_road_duration >= off_road_s (off_road_high_speed_s at high speed) -> L2
- phone_ratio_2s >= phone_ratio                          -> L2
- trend_15min >= slope_per_min (enough history, score not trivial) -> trend.level (early warning)
- blink_rate outside [normal_min, normal_max]            -> blink.level (0 = note only)
The final level is the highest level among the rules that fire.

Monitoring unavailable (PRD FR-6): no face for `unavailable_no_face_s` while moving (camera
covered, driver out of view, glare) -> `unavailable`, and no alert at all while it lasts: nothing
can be judged without a face, and guessing would be a false alarm. The HUD and the backend are
told the driver is not monitored instead. Exception: a closure that block 7 keeps counting through
a head drop (eyes seen closed, then the head fell out of view) is evidence, not a lost face, so
it stays monitored and the microsleep L3 alarm goes on.

Context: distraction rules only while moving. The turn signal does not switch off-road off:
block 8 only widens the yaw limit towards the signalled side (looking the other way, or
further than the widened limit, still counts). Drowsiness rules while standing still (block 10) are capped at
`drowsy.stationary_max_level`: a microsleep at a red light still gets a chime, a driver
closing the eyes to rest after parking gets no strong alarm. Once the stop is a rest
(context.rest_after_s) they are off, and so they are while driver enrollment asks the driver
to close the eyes (`drowsy_muted`). Stateless: same inputs -> same output.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from edge_agent.analysis.distraction import DistractionState
from edge_agent.analysis.drowsiness import DrowsinessState
from edge_agent.config import config_from_dict
from edge_agent.context.vehicle_context import VehicleContext
from edge_agent.decision.trip_memory import TripState


@dataclass(frozen=True)
class RiskConfig:
    microsleep_l3_s: float = 1.5
    drowsy_weight_perclos: float = 40.0
    drowsy_weight_microsleep: float = 25.0
    drowsy_weight_yawn: float = 15.0
    drowsy_weight_nod: float = 20.0
    drowsy_weight_slow_blink: float = 10.0
    drowsy_weight_brow: float = 10.0
    drowsy_perclos_low: float = 0.05
    drowsy_perclos_high: float = 0.20
    drowsy_yawn_full: float = 3.0
    drowsy_nod_full: float = 2.0
    drowsy_brow_full: float = 3.0
    drowsy_microsleep_memory_s: float = 300.0
    drowsy_l1: float = 40.0
    drowsy_l2: float = 70.0
    drowsy_night_factor: float = 1.2
    drowsy_long_drive_factor: float = 1.2
    drowsy_stationary_max_level: int = 1  # 0 = off while standing still, 3 = no cap
    distraction_off_road_s: float = 2.0
    distraction_off_road_high_speed_s: float = 1.5
    distraction_phone_ratio: float = 0.6
    unavailable_no_face_s: float = 3.0  # 0 = never unavailable
    trend_level: int = 1
    trend_min_points: int = 5
    trend_slope_per_min: float = 2.0
    trend_min_score: float = 20.0
    blink_normal_min: float = 10.0
    blink_normal_max: float = 30.0
    blink_min_observed_s: float = 60.0
    blink_level: int = 0

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> RiskConfig:
        return config_from_dict(cls, d, "risk")


@dataclass(frozen=True)
class RuleHit:
    level: int
    reason: str  # microsleep, drowsy_score, off_road, phone, trend, blink_rate
    value: float  # the measurement that fired the rule


@dataclass(frozen=True)
class RiskAssessment:
    t: float
    level: int  # 0..3, highest level among hits
    hits: tuple[RuleHit, ...]  # every rule that fired, highest level first
    drowsy_score: float  # 0..100
    distraction_score: float  # 0..100
    drowsy_terms: tuple[float, ...]  # perclos, microsleep, yawn, nod, slow_blink, brow (0..1)
    unavailable: bool = False  # face lost too long while moving: not monitored, no alerts (FR-6)

    @property
    def reasons(self) -> tuple[str, ...]:
        return tuple(h.reason for h in self.hits if h.level == self.level and self.level > 0)


def ramp(x: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 1.0 if x >= hi else 0.0
    return min(max((x - lo) / (hi - lo), 0.0), 1.0)


class RiskEngine:
    def __init__(self, config: RiskConfig | None = None) -> None:
        self.config = config or RiskConfig()

    def drowsy_score(
        self, d: DrowsinessState, ctx: VehicleContext, trip: TripState | None
    ) -> tuple[float, tuple[float, ...]]:
        cfg = self.config
        perclos = 0.0
        if d.perclos_ready:  # enough eye data: drowsiness.perclos_min_coverage_s (single source)
            perclos = ramp(d.perclos_60s, cfg.drowsy_perclos_low, cfg.drowsy_perclos_high)
        recent = "microsleep" in d.events or (
            trip is not None
            and trip.last_microsleep_t is not None
            and d.timestamp - trip.last_microsleep_t <= cfg.drowsy_microsleep_memory_s
        )
        microsleep = 1.0 if recent or d.closed_duration >= cfg.microsleep_l3_s else 0.0
        yawn = min(d.yawn_count_10min / cfg.drowsy_yawn_full, 1.0) if cfg.drowsy_yawn_full > 0 else 0.0
        nod = min(d.nod_count_5min / cfg.drowsy_nod_full, 1.0) if cfg.drowsy_nod_full > 0 else 0.0
        brow = min(d.brow_raise_count_5min / cfg.drowsy_brow_full, 1.0) if cfg.drowsy_brow_full > 0 else 0.0
        score = (
            cfg.drowsy_weight_perclos * perclos
            + cfg.drowsy_weight_microsleep * microsleep
            + cfg.drowsy_weight_yawn * yawn
            + cfg.drowsy_weight_nod * nod
            + cfg.drowsy_weight_slow_blink * d.slow_blink_score
            + cfg.drowsy_weight_brow * brow
        )
        if ctx.night:
            score *= cfg.drowsy_night_factor
        if ctx.long_drive:
            score *= cfg.drowsy_long_drive_factor
        return min(score, 100.0), (perclos, microsleep, yawn, nod, d.slow_blink_score, brow)

    def drowsy_level_cap(self, ctx: VehicleContext) -> int:
        """Highest level the drowsiness rules may raise: none during a rest, capped at a stop."""
        if ctx.resting:
            return 0
        if ctx.stationary:
            return self.config.drowsy_stationary_max_level
        return 3

    def off_road_threshold(self, ctx: VehicleContext) -> float:
        cfg = self.config
        return cfg.distraction_off_road_high_speed_s if ctx.high_speed else cfg.distraction_off_road_s

    def assess(
        self,
        d: DrowsinessState,
        x: DistractionState,
        ctx: VehicleContext,
        trip: TripState | None = None,
        drowsy_muted: bool = False,
    ) -> RiskAssessment:
        cfg = self.config
        hits: list[RuleHit] = []

        # Drowsiness branch
        drowsy, terms = self.drowsy_score(d, ctx, trip)
        cap = 0 if drowsy_muted else self.drowsy_level_cap(ctx)
        if cap > 0:
            if d.closed_duration >= cfg.microsleep_l3_s:
                hits.append(RuleHit(3, "microsleep", d.closed_duration))
            if drowsy >= cfg.drowsy_l2:
                hits.append(RuleHit(2, "drowsy_score", drowsy))
            elif drowsy >= cfg.drowsy_l1:
                hits.append(RuleHit(1, "drowsy_score", drowsy))
            trend = trip.trend_15min if trip is not None else None
            if (
                trend is not None
                and len(trip.minute_scores) >= cfg.trend_min_points
                and trend >= cfg.trend_slope_per_min
                and trip.minute_scores[-1] >= cfg.trend_min_score
            ):
                hits.append(RuleHit(cfg.trend_level, "trend", trend))
            observed = trip.elapsed_s if trip is not None else 0.0
            if observed >= cfg.blink_min_observed_s and not (
                cfg.blink_normal_min <= d.blink_rate <= cfg.blink_normal_max
            ):
                hits.append(RuleHit(cfg.blink_level, "blink_rate", d.blink_rate))
            hits = [RuleHit(min(h.level, cap), h.reason, h.value) for h in hits]

        # Distraction branch: only while moving (block 8 already resets when stopped).
        off_road_thr = self.off_road_threshold(ctx)
        off_road = x.off_road_duration  # turn signal: already widened towards that side in block 8
        distraction = 0.0
        if x.active and ctx.moving:
            distraction = 100.0 * min(max(off_road / off_road_thr, x.phone_ratio_2s / cfg.distraction_phone_ratio), 1.0)
            if off_road >= off_road_thr:
                hits.append(RuleHit(2, "off_road", off_road))
            if x.phone_ratio_2s >= cfg.distraction_phone_ratio:
                hits.append(RuleHit(2, "phone", x.phone_ratio_2s))

        unavailable = (
            ctx.moving
            and cfg.unavailable_no_face_s > 0
            and x.no_face_duration >= cfg.unavailable_no_face_s
            and not d.head_drop  # a closure carried through a head drop is still watched
        )
        if unavailable:
            hits, distraction = [], 0.0

        hits.sort(key=lambda h: -h.level)
        level = max((h.level for h in hits), default=0)
        return RiskAssessment(
            t=d.timestamp,
            level=level,
            hits=tuple(hits),
            drowsy_score=drowsy,
            distraction_score=distraction,
            drowsy_terms=terms,
            unavailable=unavailable,
        )
