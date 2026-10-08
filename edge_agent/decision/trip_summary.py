"""Block 11 stage - Trip summary: what happened over the whole trip, built when it ends.

`TripCollector` adds up every frame's decision result (no image, a few numbers per frame), and
`summary()` turns them into a `TripSummary`: duration, driving / stopped time, rests, alerts by
level and reason, drowsiness signs (microsleeps, yawns, nods, brow raises), distraction time
(off road, phone by call / text, glances away, looking behind),
monitoring coverage (face seen, unavailable, camera lost), the drowsy_score of every minute,
the minute fatigue first showed, a trip assessment and suggestions.

Frames the pipeline does not judge for drowsiness (`DecisionResult.observed` False: a rest after
parking, enrollment's eyes-closed step) add no drowsiness signs, no closure length and no minute
score, as in trip memory: closing the eyes for enrollment or to rest is not "nhắm mắt ngủ gật khi
đang lái" (bug found in M21, fixed in M27). A microsleep at a red light (standing still, not a rest)
still counts.

The assessment describes the trip, it does not grade the driver (alerts can be false, the
driver may flag them): "good" / "attention" / "risk", with the reasons that set it, by rules
in thresholds.yaml (trip_summary). Suggestions are codes with numbers; the HUD and the
dashboard word them. The summary is metadata only, sent to the backend for the driver and the
higher roles (manager, engineer, admin).

Pure logic on frame timestamps: testable with fake sequences.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

import numpy as np

from edge_agent.config import config_from_dict

DROWSY_EVENTS = ("microsleep", "yawn", "nod", "brow_raise")


@dataclass(frozen=True)
class TripSummaryConfig:
    max_frame_gap_s: float = 1.0  # a longer gap between frames (stall) adds no time
    risk_on_l3: bool = True  # any L3 alert -> "risk"
    attention_alerts_per_hour: float = 2.0  # L2+ alerts per driving hour -> "attention"
    attention_min_alerts: int = 2  # ... and at least this many (1 alert in a 10-minute trip is not "frequent")
    attention_tired_minutes: int = 5  # tired minutes -> "attention"
    min_monitored_frac: float = 0.6  # less of the driving time with a face seen: low coverage
    rest_margin_min: float = 10.0  # suggest a rest this many minutes before fatigue first showed
    min_rest_suggestion_min: float = 15.0

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> TripSummaryConfig:
        return config_from_dict(cls, d, "trip_summary")


@dataclass
class MinutePoint:
    minute: int  # minutes since the trip started
    drowsy_score: float  # mean over the minute
    max_level: int
    moving: bool  # moving for most of the minute


@dataclass
class TripSummary:
    trip_id: str
    started_at: str  # ISO 8601
    ended_at: str
    duration_s: float
    driving_s: float
    stopped_s: float
    rests: int
    longest_drive_s: float
    avg_speed_kmh: float | None
    speed_source: str  # "simulated" (CAN scenario) or "can"
    alerts_by_level: dict[str, int]
    alerts_by_reason: dict[str, int]
    false_alarms: int
    microsleeps: int
    longest_closure_s: float
    yawns: int
    nods: int
    brow_raises: int
    off_road_s: float
    phone_s: float
    phone_call_s: float  # phone_s by how the phone was held (block 4 phone_kind); the rest is unknown
    phone_text_s: float
    glances: int  # times the driver looked away from the road while driving
    off_road_ratio_max: float  # highest share of the glance window (distraction.glance) spent off road
    turned_away_s: float  # face lost right after a large head turn (looking behind), not "unavailable"
    monitored_frac: float | None  # driving time with a face seen / driving time
    unavailable_s: float
    unavailable_by_cause: dict[str, float]  # seconds per reason (no_face, camera_blocked, low_light, ...)
    camera_lost_s: float
    vehicle_signal_lost_s: float  # vehicle link lost while driving (speed unknown, monitored as moving)
    enrolled: bool
    driver_changes: int
    drowsy_mean: float
    drowsy_p90: float
    drowsy_max: float
    first_tired_min: int | None  # driving minutes before the first tired minute
    score_l1: float  # drowsy_score thresholds of this trip (risk.drowsy.l1 / l2), for the charts
    score_l2: float
    rating: str  # good | attention | risk
    rating_reasons: list[str]
    suggestions: list[dict[str, Any]]  # {"code": ..., optional numbers}
    minutes: list[MinutePoint] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TripCollector:
    def __init__(
        self,
        config: TripSummaryConfig | None = None,
        tired_score: float = 40.0,
        long_drive_s: float = 7200.0,
        score_l2: float = 70.0,
    ) -> None:
        """tired_score: a minute at or above this drowsy_score is "tired" (risk.drowsy.l1);
        long_drive_s: a continuous drive this long gets a "regular breaks" suggestion (context.long_drive_s)."""
        self.config = config or TripSummaryConfig()
        self.tired_score, self.long_drive_s, self.score_l2 = tired_score, long_drive_s, score_l2
        self._t0: float | None = None
        self._last_t: float | None = None
        self.duration = self.driving = self.stopped = 0.0
        self.rests = 0
        self._was_resting = False
        self._drive_run = self.longest_drive = 0.0
        self._speed_sum = self._speed_time = 0.0
        self.alerts_by_level = {"1": 0, "2": 0, "3": 0}
        self.alerts_by_reason: dict[str, int] = {}
        self.counts = dict.fromkeys(DROWSY_EVENTS, 0)
        self.longest_closure = 0.0
        self.off_road = self.phone = 0.0
        self.phone_kind = {"call": 0.0, "text": 0.0}
        self.glances = 0
        self._was_off_road = False
        self.off_road_ratio_max = 0.0
        self.turned_away = 0.0
        self.monitored = self.unavailable = 0.0
        self.unavailable_by_cause: dict[str, float] = {}  # risk.unavailable_reason -> seconds
        self.enrolled = False
        self.driver_changes = 0  # "Đổi tài xế" presses (edge_agent.decision.pipeline.change_driver)
        # Continuous driving of the current driver (HUD, M65): block 10's drive_run_s, the counter the
        # long-drive rule reads, so the HUD and the rule cannot disagree (M73).
        self._driver_run = 0.0
        self._minutes: dict[int, list[float]] = {}  # minute -> [score sum, frames, max level, moving frames]

    def update(self, r: Any) -> None:
        """One frame's DecisionResult (edge_agent.decision.pipeline)."""
        cfg = self.config
        t = r.risk.t
        if self._t0 is None:
            self._t0 = t
        dt = 0.0 if self._last_t is None else min(max(0.0, t - self._last_t), cfg.max_frame_gap_s)
        self._last_t = t
        ctx = r.context
        self.duration += dt
        if ctx.moving:
            self.driving += dt
            self._drive_run += dt
            self.longest_drive = max(self.longest_drive, self._drive_run)
            if ctx.speed_kmh is not None:
                self._speed_sum += ctx.speed_kmh * dt
                self._speed_time += dt
            if not r.risk.unavailable and r.distraction.no_face_duration == 0:  # face seen
                self.monitored += dt
        else:
            self.stopped += dt
        if ctx.resting and not self._was_resting:
            self.rests += 1
            self._drive_run = 0.0
        self._was_resting = ctx.resting
        self._driver_run = ctx.drive_run_s
        if r.risk.unavailable:
            self.unavailable += dt
            cause = r.risk.unavailable_reason or "no_face"
            self.unavailable_by_cause[cause] = self.unavailable_by_cause.get(cause, 0.0) + dt
        hit_reasons = {h.reason for h in r.risk.hits}
        if "off_road" in hit_reasons:
            self.off_road += dt
        if "phone" in hit_reasons:
            self.phone += dt
            if r.distraction.phone_kind in self.phone_kind:
                self.phone_kind[r.distraction.phone_kind] += dt
        x = r.distraction
        self.glances += x.off_road and not self._was_off_road
        self._was_off_road = x.off_road
        self.off_road_ratio_max = max(self.off_road_ratio_max, x.off_road_ratio)
        if x.turned_away:
            self.turned_away += dt
        observed = getattr(r, "observed", True)  # drowsiness not judged: a rest, enrollment's eyes-closed step
        if observed:
            for ev in r.drowsiness.events:
                if ev in self.counts:
                    self.counts[ev] += 1
            self.longest_closure = max(self.longest_closure, r.drowsiness.closed_duration)
        alert = r.alert.new_alert
        if alert is not None and alert.level > 0:
            self.alerts_by_level[str(alert.level)] += 1
            for reason in alert.reasons:
                self.alerts_by_reason[reason] = self.alerts_by_reason.get(reason, 0) + 1
        self.enrolled = self.enrolled or r.enrollment.enrolled
        if not observed:  # no minute score from it either (its drowsy_score reads the eyes closed on purpose)
            return
        m = int((t - self._t0) // 60)
        acc = self._minutes.setdefault(m, [0.0, 0, 0, 0])
        acc[0] += r.risk.drowsy_score
        acc[1] += 1
        acc[2] = max(acc[2], r.alert.active_level)
        acc[3] += ctx.moving

    def minutes(self) -> list[MinutePoint]:
        return [
            MinutePoint(m, round(a[0] / a[1], 1), int(a[2]), a[3] * 2 >= a[1])
            for m, a in sorted(self._minutes.items())
            if a[1]
        ]

    # ------------------------------------------------------------------ live view for the HUD (M65)
    def driver_changed(self) -> None:
        """ "Đổi tài xế": the new driver's continuous driving starts at 0. The trip's own numbers
        (longest_drive_s, rests, minutes) go on: nothing of the summary is lost."""
        self.driver_changes += 1
        self._driver_run = 0.0

    def hud_view(self, window_min: int) -> dict[str, Any]:
        """What the HUD shows of the running trip, read-only: continuous driving of the current
        driver, driving time, and the drowsy_score of each of the last `window_min` minutes (oldest
        first, the running minute last and partial). A minute with no judged frame (a rest, the
        eyes-closed step of enrollment, a stall) is None: the HUD draws it as a gap, not as 0."""
        recent: list[dict[str, Any] | None] = []
        if self._t0 is not None and self._last_t is not None and window_min > 0:
            now = int((self._last_t - self._t0) // 60)
            for m in range(max(0, now - window_min + 1), now + 1):
                a = self._minutes.get(m)
                recent.append(
                    None
                    if not a or not a[1]
                    else {"minute": m, "drowsy_score": round(a[0] / a[1], 1), "max_level": int(a[2])}
                )
        return {
            "drive_run_s": round(self._driver_run, 1),
            "driving_s": round(self.driving, 1),
            "score_l1": self.tired_score,  # colour bands of the chart: risk.drowsy.l1 / l2 of this trip
            "score_l2": self.score_l2,
            "window_min": window_min,  # the chart's width in minutes (hud.trend_minutes), recent may be shorter
            "recent_minutes": recent,
        }

    def summary(
        self,
        trip_id: str,
        started_at: datetime,
        ended_at: datetime,
        false_alarms: int = 0,
        camera_lost_s: float = 0.0,
        speed_source: str = "simulated",
        vehicle_signal_lost_s: float = 0.0,
    ) -> TripSummary:
        cfg = self.config
        minutes = self.minutes()
        scores = np.array([p.drowsy_score for p in minutes]) if minutes else np.zeros(1)
        first_tired = None
        driving_min = 0
        for p in minutes:
            if p.drowsy_score >= self.tired_score:
                first_tired = driving_min
                break
            driving_min += p.moving
        monitored = self.monitored / self.driving if self.driving > 0 else None
        s = TripSummary(
            trip_id=trip_id,
            started_at=started_at.isoformat(),
            ended_at=ended_at.isoformat(),
            duration_s=round(self.duration, 1),
            driving_s=round(self.driving, 1),
            stopped_s=round(self.stopped, 1),
            rests=self.rests,
            longest_drive_s=round(self.longest_drive, 1),
            avg_speed_kmh=round(self._speed_sum / self._speed_time, 1) if self._speed_time > 0 else None,
            speed_source=speed_source,
            alerts_by_level=dict(self.alerts_by_level),
            alerts_by_reason=dict(self.alerts_by_reason),
            false_alarms=false_alarms,
            microsleeps=self.counts["microsleep"],
            longest_closure_s=round(self.longest_closure, 2),
            yawns=self.counts["yawn"],
            nods=self.counts["nod"],
            brow_raises=self.counts["brow_raise"],
            off_road_s=round(self.off_road, 1),
            phone_s=round(self.phone, 1),
            phone_call_s=round(self.phone_kind["call"], 1),
            phone_text_s=round(self.phone_kind["text"], 1),
            glances=self.glances,
            off_road_ratio_max=round(self.off_road_ratio_max, 3),
            turned_away_s=round(self.turned_away, 1),
            monitored_frac=None if monitored is None else round(monitored, 3),
            unavailable_s=round(self.unavailable, 1),
            unavailable_by_cause={k: round(v, 1) for k, v in sorted(self.unavailable_by_cause.items())},
            camera_lost_s=round(camera_lost_s, 1),
            vehicle_signal_lost_s=round(vehicle_signal_lost_s, 1),
            enrolled=self.enrolled,
            driver_changes=self.driver_changes,
            drowsy_mean=round(float(scores.mean()), 1),
            drowsy_p90=round(float(np.percentile(scores, 90)), 1),
            drowsy_max=round(float(scores.max()), 1),
            first_tired_min=first_tired,
            score_l1=self.tired_score,
            score_l2=self.score_l2,
            rating="good",
            rating_reasons=[],
            suggestions=[],
            minutes=minutes,
        )
        s.rating, s.rating_reasons = assess(s, cfg, self.tired_score)
        s.suggestions = suggest(s, cfg, self.long_drive_s)
        return s


def assess(s: TripSummary, cfg: TripSummaryConfig, tired_score: float) -> tuple[str, list[str]]:
    """Trip assessment: "risk" > "attention" > "good", with the reasons that set it."""
    reasons: list[str] = []
    risk = cfg.risk_on_l3 and (s.alerts_by_level.get("3", 0) > 0 or s.microsleeps > 0)
    if risk:
        reasons.append("microsleep")
    serious = s.alerts_by_level.get("2", 0) + s.alerts_by_level.get("3", 0)
    hours = s.driving_s / 3600.0
    if serious >= max(cfg.attention_min_alerts, 1) and hours > 0 and serious / hours >= cfg.attention_alerts_per_hour:
        reasons.append("frequent_alerts")
    tired_minutes = sum(1 for p in s.minutes if p.drowsy_score >= tired_score)
    if tired_minutes >= cfg.attention_tired_minutes:
        reasons.append("tired_minutes")
    if s.monitored_frac is not None and s.monitored_frac < cfg.min_monitored_frac:
        reasons.append("low_coverage")  # not a verdict on the driver: the numbers are incomplete
    rating = "risk" if risk else ("attention" if {"frequent_alerts", "tired_minutes"} & set(reasons) else "good")
    return rating, reasons


def suggest(s: TripSummary, cfg: TripSummaryConfig, long_drive_s: float) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if s.rating == "risk":
        out.append({"code": "rest_now"})
    if s.first_tired_min is not None:
        out.append(
            {
                "code": "rest_after",
                "minutes": int(max(s.first_tired_min - cfg.rest_margin_min, cfg.min_rest_suggestion_min)),
            }
        )
    if s.longest_drive_s >= long_drive_s:
        out.append({"code": "regular_breaks", "minutes": int(long_drive_s // 60)})
    if s.alerts_by_reason.get("phone", 0):
        out.append({"code": "phone_away"})
    if s.alerts_by_reason.get("off_road", 0):
        out.append({"code": "eyes_on_road"})
    if s.monitored_frac is not None and s.monitored_frac < cfg.min_monitored_frac:
        out.append({"code": "check_camera"})
    if not s.enrolled:
        out.append({"code": "enroll"})
    return out
