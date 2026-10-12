"""Block 9 - Rule-based risk engine.

Rule table (docs/workflow/workflow_full_4.jpg):
- closed_duration >= microsleep_l3_s                    -> L3 (microsleep)
- closed_duration >= unresponsive_closed_s              -> L3 (unresponsive): the siren has been on
  for seconds and the eyes are still closed; a new reason, so block 12 sends a second event (M44)
- drowsy_score = 40*perclos + 25*microsleep + 15*yawn + 20*nod (+ 0*slow_blink + 0*brow: both
  are still measured and kept in drowsy_terms, their weights are 0 since M53)
  (terms 0..1; multiplied by night / long-drive factors from context, then capped at 100)
  >= l1 -> L1, >= l2 -> L2
- off_road_duration >= off_road_s (off_road_high_speed_s at high speed) -> L2
- phone_ratio_2s >= phone_ratio                          -> L2
- trend_15min >= slope_per_min (enough history, score not trivial) -> trend.level (0 = note only
  since M53; 1 = early warning)
- blink_rate outside [normal_min, normal_max]            -> blink.level (0 = note only)
The final level is the highest level among the rules that fire.

Monitoring unavailable (PRD FR-6): no face for `unavailable_no_face_s` while the vehicle is not
standing still (camera covered, driver out of view, glare) -> `unavailable`, and no alert at all while it lasts: nothing
can be judged without a face, and guessing would be a false alarm. The HUD and the backend are
told the driver is not monitored instead. Exception: a closure that block 7 keeps counting through
a head drop (eyes seen closed, then the head fell out of view) is evidence, not a lost face, so
it stays monitored and the microsleep L3 alarm goes on. A face in view that cannot be read (block 6
quality stage: low_light, glare, blur, and bad_angle: partly out of the image or without a head
pose, M72) for `unavailable_low_quality_s` is unavailable as well, and `unavailable_reason` says
which of them it is (a lost face: camera_blocked, bad_angle or no_face). Before M72 bad_angle was
timed nowhere: a face cut by the edge of the image was not measured, not "unavailable" and raised no
alert, for as long as it stayed there. The head-drop exception holds for it too (a dropped head is
often partly out of the image). "Not standing still" is block 10's `rolling`: also the crawl below
context.min_speed_kmh, where the distraction rules are off but a driver out of view is still not
watched (before M72: `moving`, so nobody was told at 1-5 km/h).
Likewise a face lost right after a large
head turn (block 8 `turned_away`, at most distraction.turned_away.max_s): the driver is looking
behind, the off-road rule goes on instead of "unavailable".

Context: distraction rules only while moving; standing still (0 km/h) raises no alert at all (M30). The turn signal does not switch off-road off:
block 8 only widens the yaw limit towards the signalled side (looking the other way, or
further than the widened limit, still counts). Drowsiness rules while standing still (block 10) are capped at
`drowsy.stationary_max_level`: 0 since M30, so a microsleep at a red light gets no chime either
(with 1, as before M30, it gets one, and a driver closing the eyes to rest after parking gets no
strong alarm). Once the stop is a rest
(context.rest_after_s) they are off, and so they are while driver enrollment asks the driver
to close the eyes (`drowsy_muted`: drowsy_score and its terms read 0 too). During a rest the score
and its terms read 0 as well: eyes closed in a parked vehicle are not drowsiness at the wheel, and
the HUD used to show 65 points next to "level 0" there. Stateless: same inputs -> same output.

The blink-rate rule waits for `blink_min_observed_s` of eye data in block 7's blink window
(DrowsinessState.blink_observed_s), not for that long since the trip began: a driver whose eyes were
read for ten seconds of the last minute has no blink rate to judge.

A measurement of block 7 / 8 that is not finite (NaN, inf) reads as 0 here, so only its own term or
rule is lost (M77). Before, a NaN perclos_60s made drowsy_score NaN, every comparison with it was
False, and the level was 0 with yawns and nods at their maximum; the NaN score then went into trip
memory and to the backend, which is not valid JSON. Blocks 7 and 8 are not known to output one:
this is a guard, and the first time a field is replaced it is logged (the only thing kept between
frames).
"""

from __future__ import annotations

import dataclasses
import logging
import math
from dataclasses import dataclass
from typing import Any, TypeVar

from edge_agent.analysis.distraction import DistractionState
from edge_agent.analysis.drowsiness import DrowsinessState
from edge_agent.config import config_from_dict
from edge_agent.context.vehicle_context import VehicleContext
from edge_agent.decision.trip_memory import TripState
from edge_agent.perception.quality import NO_FACE_ISSUES, TIMED_ISSUES, QualityState

log = logging.getLogger("driverguard.risk")

UNRESPONSIVE = "unresponsive"  # L3 reason: eyes closed through the alarm (M44)
MAX_LEVEL = 3  # the scale L0-L3
MAX_SCORE = 100.0  # drowsy_score and distraction_score run 0-100

# The numbers the rules read from blocks 7 and 8: each must be finite (M77).
DROWSY_INPUTS = (
    "closed_duration",
    "perclos_60s",
    "blink_rate",
    "yawn_count_10min",
    "nod_count_5min",
    "brow_raise_count_5min",
    "slow_blink_score",
)
DISTRACTION_INPUTS = ("off_road_duration", "phone_ratio_2s", "no_face_duration")

_State = TypeVar("_State", DrowsinessState, DistractionState)


@dataclass(frozen=True)
class RiskConfig:
    microsleep_l3_s: float = 1.5
    microsleep_level: int = 3  # level of each rule; 0 = note only
    unresponsive_level: int = 3
    unresponsive_closed_s: float = 6.0  # eyes still closed this long: L3 reason unresponsive; 0 = off
    drowsy_weight_perclos: float = 40.0
    drowsy_weight_microsleep: float = 25.0
    drowsy_weight_yawn: float = 15.0
    drowsy_weight_nod: float = 20.0
    drowsy_weight_slow_blink: float = 0.0  # measured, not scored (M53)
    drowsy_weight_brow: float = 0.0
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
    drowsy_context_factor_cap: float = 1.2  # the two factors together multiply by no more than this
    drowsy_stationary_max_level: int = 0  # 0 = off while standing still (M30), 3 = no cap
    distraction_off_road_s: float = 2.0
    distraction_off_road_high_speed_s: float = 1.5
    distraction_phone_ratio: float = 0.6
    distraction_off_road_level: int = 2
    distraction_phone_level: int = 2
    unavailable_no_face_s: float = 3.0  # 0 = never unavailable
    unavailable_low_quality_s: float = 5.0  # face in view but unusable this long; 0 = off
    trend_level: int = 0  # 0 = note only (M53)
    trend_min_points: int = 5
    trend_slope_per_min: float = 2.0
    trend_min_score: float = 20.0
    blink_normal_min: float = 10.0
    blink_normal_max: float = 30.0
    blink_min_observed_s: float = 30.0
    blink_level: int = 0

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> RiskConfig:
        """Build the config from its section of thresholds.yaml; an unknown key is an error."""
        return config_from_dict(cls, d, "risk")


@dataclass(frozen=True)
class RuleHit:
    level: int
    reason: str  # microsleep, unresponsive, drowsy_score, off_road, phone, trend, blink_rate
    value: float  # the measurement that fired the rule


@dataclass(frozen=True)
class RiskAssessment:
    t: float
    level: int  # 0..3, highest level among hits
    hits: tuple[RuleHit, ...]  # every rule that fired, highest level first
    drowsy_score: float  # 0..100
    distraction_score: float  # 0..100
    drowsy_terms: tuple[float, ...]  # perclos, microsleep, yawn, nod, slow_blink, brow (0..1)
    unavailable: bool = False  # face lost / unreadable too long while rolling: not monitored, no alerts (FR-6)
    # Why: no_face, camera_blocked, bad_angle, low_light, glare or blur. None while monitored.
    unavailable_reason: str | None = None

    @property
    def reasons(self) -> tuple[str, ...]:
        """Reasons of the rules that hit at the assessed level; empty at level 0."""
        return tuple(h.reason for h in self.hits if h.level == self.level and self.level > 0)


def ramp(x: float, lo: float, hi: float) -> float:
    """Linear ramp from 0 at `lo` to 1 at `hi`, clamped; a step at `hi` when hi <= lo."""
    if hi <= lo:
        return 1.0 if x >= hi else 0.0
    return min(max((x - lo) / (hi - lo), 0.0), 1.0)


class RiskEngine:
    def __init__(self, config: RiskConfig | None = None) -> None:
        self.config = config or RiskConfig()
        self._logged: set[str] = set()  # non-finite inputs already reported

    def _finite(self, state: _State, names: tuple[str, ...]) -> tuple[_State, tuple[str, ...]]:
        """`state` with its non-finite `names` set to 0, and which they were (none on a normal frame)."""
        if math.isfinite(sum(getattr(state, n) for n in names)):  # one sum: a NaN / inf anywhere shows in it
            return state, ()
        bad = tuple(n for n in names if not math.isfinite(getattr(state, n)))
        for n in bad:
            if n not in self._logged:
                self._logged.add(n)
                log.warning("%s is %s: read as 0, its term / rule is off (logged once)", n, getattr(state, n))
        return dataclasses.replace(state, **dict.fromkeys(bad, 0)), bad

    def drowsy_score(
        self, d: DrowsinessState, ctx: VehicleContext, trip: TripState | None
    ) -> tuple[float, tuple[float, ...]]:
        """drowsy_score (0-100) and its terms before weighting: PERCLOS, microsleep, yawns, nods,
        slow blinks, brow raises. Night and a long drive scale the score, up to the factor cap."""
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
        factor = (cfg.drowsy_night_factor if ctx.night else 1.0) * (
            cfg.drowsy_long_drive_factor if ctx.long_drive else 1.0
        )
        score *= min(factor, cfg.drowsy_context_factor_cap)
        return min(score, MAX_SCORE), (perclos, microsleep, yawn, nod, d.slow_blink_score, brow)

    def drowsy_level_cap(self, ctx: VehicleContext) -> int:
        """Highest level the drowsiness rules may raise: none during a rest, capped at a stop."""
        if ctx.resting:
            return 0
        if ctx.stationary:
            return self.config.drowsy_stationary_max_level
        return MAX_LEVEL

    def off_road_threshold(self, ctx: VehicleContext) -> float:
        """Seconds off the road that count as a distraction; a shorter time at high speed."""
        cfg = self.config
        return cfg.distraction_off_road_high_speed_s if ctx.high_speed else cfg.distraction_off_road_s

    def assess(
        self,
        d: DrowsinessState,
        x: DistractionState,
        ctx: VehicleContext,
        trip: TripState | None = None,
        drowsy_muted: bool = False,
        quality: QualityState | None = None,
    ) -> RiskAssessment:
        """Block 9, one frame: both scores, the rules that hit and the level L0-L3 with its reasons.
        `drowsy_muted`: the eyes are closed on request, so the drowsiness branch is off."""
        cfg = self.config
        hits: list[RuleHit] = []
        d, bad = self._finite(d, DROWSY_INPUTS)
        x, _ = self._finite(x, DISTRACTION_INPUTS)

        # Drowsiness branch
        drowsy, terms = self.drowsy_score(d, ctx, trip)
        if drowsy_muted or ctx.resting:  # eyes closed on request, or parked for a rest: nothing to score
            drowsy, terms = 0.0, (0.0,) * len(terms)
        cap = 0 if drowsy_muted else self.drowsy_level_cap(ctx)
        if cap > 0:
            if d.closed_duration >= cfg.microsleep_l3_s:
                hits.append(RuleHit(cfg.microsleep_level, "microsleep", d.closed_duration))
            if cfg.unresponsive_closed_s > 0 and d.closed_duration >= cfg.unresponsive_closed_s:
                hits.append(
                    RuleHit(cfg.unresponsive_level, UNRESPONSIVE, d.closed_duration)
                )  # the alarm did not wake the driver
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
            if (
                d.blink_observed_s >= cfg.blink_min_observed_s  # eye data in block 7's blink window
                and "blink_rate" not in bad  # unknown is not "blinking too little"
                and not (cfg.blink_normal_min <= d.blink_rate <= cfg.blink_normal_max)
            ):
                hits.append(RuleHit(cfg.blink_level, "blink_rate", d.blink_rate))
            hits = [RuleHit(min(h.level, cap), h.reason, h.value) for h in hits]

        # Distraction branch: only while moving (block 8 already resets when stopped).
        off_road_thr = self.off_road_threshold(ctx)
        off_road = x.off_road_duration  # turn signal: already widened towards that side in block 8
        distraction = 0.0
        if x.active and ctx.moving:
            distraction = MAX_SCORE * min(
                max(off_road / off_road_thr, x.phone_ratio_2s / cfg.distraction_phone_ratio), 1.0
            )
            if off_road >= off_road_thr:
                hits.append(RuleHit(cfg.distraction_off_road_level, "off_road", off_road))
            if x.phone_ratio_2s >= cfg.distraction_phone_ratio:
                hits.append(RuleHit(cfg.distraction_phone_level, "phone", x.phone_ratio_2s))

        issue = quality.issue if quality is not None else None
        no_face = (
            cfg.unavailable_no_face_s > 0
            and x.no_face_duration >= cfg.unavailable_no_face_s
            and not d.head_drop  # a closure carried through a head drop is still watched
            and not x.turned_away  # face lost right after a large head turn: looking behind (block 8)
        )
        # A face in view that cannot be read (too dark, washed out, blurred): what blocks 7 / 8 say
        # about it is a guess, so nothing is carried through, not even a closure being counted.
        # Partly out of the image (bad_angle): the same, except a closure carried through a head drop.
        poor = (
            quality is not None
            and cfg.unavailable_low_quality_s > 0
            and issue in TIMED_ISSUES
            and quality.duration >= cfg.unavailable_low_quality_s
            and not (issue == "bad_angle" and d.head_drop)
        )
        unavailable = ctx.rolling and (no_face or poor)
        unavailable_reason = None
        if unavailable:
            hits, distraction = [], 0.0
            if no_face:
                unavailable_reason = issue if issue in NO_FACE_ISSUES else "no_face"
            else:
                unavailable_reason = issue

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
            unavailable_reason=unavailable_reason,
        )
