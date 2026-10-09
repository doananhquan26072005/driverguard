"""Block 12 - Alert manager.

Turns the per-frame risk level into stable alerts:
- Raise hysteresis: a higher level must hold for rise_confirm_s[level] before it becomes
  active (L3 can be 0 s = immediate). One noisy frame cannot raise an alert.
- Fall hysteresis: the level must stay lower for fall_hold_s before the active level
  drops, so an alert does not flicker on / off.
- New reason at the same level: while a level is active, a reason that was not in its
  alerts yet (e.g. L2 off_road, then L2 phone) is emitted as a new alert once it has
  held for rise_confirm_s[level], so the dashboard gets an event for every cause.
  When the active level drops, a reason of the lower level that was alerted at that level within
  its cooldown does not raise a new alert.
- Cooldown: per (level, reason). An alert is held back only when every one of its
  reasons was already emitted at that level within cooldown_s[level]. The cooldown of a lower
  level never holds a higher one back (escalation), but the higher level's own does: L2 off_road
  again within cooldown_s[2] of the last L2 off_road is held, also when it comes up from L1.
  L3 has no cooldown by default: after fall_hold_s of open
  eyes, a new closure is a new microsleep and gets its own siren and event.
- Reminder (M74, `remind`): the cooldown holds an alert back, it does not swallow it. A reason
  that is still a hit at the active level once cooldown_s[level] has passed since its last alert
  there is alerted again, after holding rise_confirm_s[level] like a new reason. That covers an
  episode that began inside the cooldown, a level that simply stays up (L1 for half an hour is a
  chime every cooldown, not one chime), and a reason that began under a higher level and is still
  there when that level drops. One alert covers every reason of the frame, so reasons that became
  due at different times do not each make a sound. A level with cooldown 0 is never reminded.
  A reason in `remind_skip_reasons` (M92: drowsy_score) is not reminded: it is one alert per
  episode, exactly as with remind off. That includes the case of a reason that is first seen when
  a higher level drops onto it: no alert of its own.
- Escalation over time (M32): an L1 alert whose reason was already alerted at L1 often enough
  (l1_repeat_count alerts within l1_repeat_window_s, this one included, reminders too) goes out
  as L2 with the extra reason "repeated_l1": the driver was told several times and did not rest.
  The active level is L2 for that alert, then falls back to L1 after fall_hold_s without a new
  alert. The count of that reason then starts again (M74): the next L2 needs l1_repeat_count more
  alerts, not one. A single L1 is unchanged, and a rest or a driver change starts the count again.
- Repeated L3 (M44): the l3_repeat_count-th L3 alert within l3_repeat_window_s carries the extra
  reason "repeated_l3" (the level cannot go higher): the driver keeps falling asleep, which the
  fleet view shows while it happens. The "unresponsive" alert of a closure that goes on is the
  same microsleep, not another one, and is not counted; neither is a reminder.

- Gap between frames: a level (or a new reason) is confirmed by holding, and holding is measured on
  timestamps. Two frames more than max_gap_s apart do not show it held in between (the loop stood
  still): the confirmation starts again at the frame after the gap. An active level is not touched.

`active_level` is what the HUD shows; `new_alert` is set only on the frame an alert
is emitted (chime / sound / seat vibration, metadata event).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from edge_agent.config import check_keys
from edge_agent.decision.risk_engine import RiskAssessment

LEVEL_ACTIONS = {
    0: "normal",
    1: "icon + chime",
    2: "sound + seat vibration",
    3: "strong alarm, suggest a break",
}
REPEATED_L1 = "repeated_l1"  # added to the reasons of an L1 alert escalated to L2 (M32)
REPEATED_L3 = "repeated_l3"  # added to the reasons of an L3 alert that keeps coming back (M44)
UNRESPONSIVE = "unresponsive"  # risk engine: the same closure going on, not a new L3


def _levels(d: dict[Any, Any] | None, default: dict[int, float]) -> dict[int, float]:
    out = dict(default)
    out.update({int(k): float(v) for k, v in (d or {}).items()})
    return out


@dataclass(frozen=True)
class AlertConfig:
    rise_confirm_s: dict[int, float] = field(default_factory=lambda: {1: 1.0, 2: 0.5, 3: 0.0})
    fall_hold_s: float = 3.0
    cooldown_s: dict[int, float] = field(default_factory=lambda: {1: 120.0, 2: 30.0, 3: 0.0})
    l1_repeat_count: int = 3  # this many L1 alerts of one reason within the window -> L2; 0 = off
    l1_repeat_window_s: float = 600.0
    l1_repeat_level: int = 2  # the level that alert goes out at
    l3_repeat_count: int = 3  # this many L3 alerts within the window: the reason repeated_l3; 0 = off
    l3_repeat_window_s: float = 600.0
    max_gap_s: float = 0.5  # frames further apart than this restart a running confirmation
    remind: bool = True  # a reason still there once its cooldown has passed is alerted again (M74)
    remind_skip_reasons: tuple[str, ...] = ("drowsy_score",)  # reasons that are not reminded (M92)

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> AlertConfig:
        d = d or {}
        check_keys("alert", {k: k for k in d}, cls.__dataclass_fields__)
        default = cls()
        return cls(
            rise_confirm_s=_levels(d.get("rise_confirm_s"), default.rise_confirm_s),
            fall_hold_s=float(d.get("fall_hold_s", default.fall_hold_s)),
            cooldown_s=_levels(d.get("cooldown_s"), default.cooldown_s),
            l1_repeat_count=int(d.get("l1_repeat_count", default.l1_repeat_count)),
            l1_repeat_window_s=float(d.get("l1_repeat_window_s", default.l1_repeat_window_s)),
            l1_repeat_level=int(d.get("l1_repeat_level", default.l1_repeat_level)),
            l3_repeat_count=int(d.get("l3_repeat_count", default.l3_repeat_count)),
            l3_repeat_window_s=float(d.get("l3_repeat_window_s", default.l3_repeat_window_s)),
            max_gap_s=float(d.get("max_gap_s", default.max_gap_s)),
            remind=bool(d.get("remind", default.remind)),
            remind_skip_reasons=tuple(str(x) for x in d.get("remind_skip_reasons", default.remind_skip_reasons)),
        )


@dataclass(frozen=True)
class Alert:
    t: float
    level: int
    reasons: tuple[str, ...]
    drowsy_score: float
    distraction_score: float

    @property
    def action(self) -> str:
        return LEVEL_ACTIONS[self.level]


@dataclass(frozen=True)
class AlertOutput:
    t: float
    active_level: int
    active_reasons: tuple[str, ...]
    new_alert: Alert | None = None
    suppressed: bool = False  # a level was raised but its alert was held back by cooldown


class AlertManager:
    def __init__(self, config: AlertConfig | None = None) -> None:
        self.config = config or AlertConfig()
        self.active_level = 0
        self._active_reasons: tuple[str, ...] = ()
        self._candidate: int | None = None
        self._candidate_since = 0.0
        self._lower_since: float | None = None
        self._last_emit: dict[tuple[int, str], float] = {}  # (level, reason) -> last emit time
        self._alerted: set[str] = set()  # reasons already covered by an alert at the active level
        self._new_reason_since: float | None = None
        self._reason_seen: dict[str, float] = {}  # reason -> last time it was a hit at the active level
        self._l1_emits: dict[str, list[float]] = {}  # reason -> times of its recent L1 alerts (M32)
        self._l3_emits: list[float] = []  # times of the recent L3 alerts (M44)
        self._last_t: float | None = None

    def forget_repeats(self) -> None:
        """The driver rested: earlier L1 alerts no longer count towards the escalation."""
        self._l1_emits.clear()
        self._l3_emits.clear()

    def _repeated(self, t: float, reasons: tuple[str, ...]) -> bool:
        """Count this L1 alert; True when one of its reasons reached l1_repeat_count in the window.
        A reason that reached it starts its count again."""
        cfg = self.config
        if cfg.l1_repeat_count <= 0:
            return False
        repeated = False
        for k in reasons:
            times = [x for x in self._l1_emits.get(k, []) if t - x < cfg.l1_repeat_window_s] + [t]
            if len(times) >= cfg.l1_repeat_count:
                repeated, times = True, []
            self._l1_emits[k] = times
        return repeated

    def _repeated_l3(self, t: float) -> bool:
        """Count this L3 alert; True when it is the l3_repeat_count-th within the window."""
        cfg = self.config
        if cfg.l3_repeat_count <= 0:
            return False
        self._l3_emits = [x for x in self._l3_emits if t - x < cfg.l3_repeat_window_s] + [t]
        return len(self._l3_emits) >= cfg.l3_repeat_count

    def _due(self, t: float, level: int, reason: str) -> bool:
        """The cooldown of this reason at this level has passed (or it was never alerted there)."""
        cooldown = self.config.cooldown_s.get(level, 0.0)
        if not self.config.remind or cooldown <= 0 or reason in self.config.remind_skip_reasons:
            return False
        return t - self._last_emit.get((level, reason), -float("inf")) >= cooldown

    def _emit(self, r: RiskAssessment, level: int, reasons: tuple[str, ...], reminder: bool = False) -> AlertOutput:
        t = r.t
        self._alerted |= set(reasons)
        keys = reasons or ("",)
        cooldown = self.config.cooldown_s.get(level, 0.0)
        if all(t - self._last_emit.get((level, k), -float("inf")) < cooldown for k in keys):
            return AlertOutput(t, level, self._active_reasons, None, suppressed=True)
        for k in keys:
            self._last_emit[(level, k)] = t
        if level == 1 and self._repeated(t, reasons):
            level, reasons = (
                self.config.l1_repeat_level,
                (*reasons, REPEATED_L1),
            )  # original reasons first: they set the event kind
            self.active_level, self._active_reasons = level, reasons
            self._alerted.add(REPEATED_L1)
            for k in keys:  # the same cause turning into a real L2 right after is not a second sound
                self._last_emit[(level, k)] = t
        if level == 3 and not reminder and UNRESPONSIVE not in reasons and self._repeated_l3(t):
            reasons = (*reasons, REPEATED_L3)  # the level stays L3; the backend shows it at once
        alert = Alert(t, level, reasons, r.drowsy_score, r.distraction_score)
        return AlertOutput(t, level, self._active_reasons, alert)

    def _raise(self, r: RiskAssessment, level: int) -> AlertOutput:
        self.active_level = level
        self._active_reasons = r.reasons
        self._candidate = None
        self._lower_since = None
        self._alerted = set()
        self._new_reason_since = None
        self._reason_seen = dict.fromkeys(r.reasons, r.t)
        return self._emit(r, level, r.reasons)

    def _check_new_reasons(self, r: RiskAssessment) -> AlertOutput | None:
        """Same level as active: emit when a reason not yet alerted, or one whose cooldown has
        passed (a reminder), has held long enough."""
        for x in r.reasons:
            self._reason_seen[x] = r.t
        # A reason counts as new again only after it was gone for fall_hold_s, like the level
        # itself: a reason flickering off for a frame or two must not re-alert.
        self._alerted = {
            x for x in self._alerted if r.t - self._reason_seen.get(x, float("-inf")) < self.config.fall_hold_s
        }
        level = self.active_level
        fresh = tuple(x for x in r.reasons if x not in self._alerted)
        new = fresh + tuple(x for x in r.reasons if x in self._alerted and self._due(r.t, level, x))
        if not new:
            self._new_reason_since = None
            return None
        if self._new_reason_since is None:
            self._new_reason_since = r.t
        if r.t - self._new_reason_since < self.config.rise_confirm_s.get(level, 0.0):
            return None
        self._new_reason_since = None
        # New reasons first: the publisher derives the event kind from the first reason.
        return self._emit(r, level, new + tuple(x for x in r.reasons if x not in new), reminder=not fresh)

    def update(self, r: RiskAssessment) -> AlertOutput:
        t, target = r.t, r.level
        if self._last_t is not None and t - self._last_t > self.config.max_gap_s:
            self._candidate = None  # not seen held across the gap: confirmed from this frame on
            self._new_reason_since = None
        self._last_t = t

        if target > self.active_level:
            self._lower_since = None
            self._new_reason_since = None
            # A higher target restarts the confirmation; a lower-but-still-raised target keeps it.
            if self._candidate is None or target > self._candidate:
                self._candidate, self._candidate_since = target, t
            elif target < self._candidate:
                self._candidate = target
            if t - self._candidate_since >= self.config.rise_confirm_s.get(self._candidate, 0.0):
                return self._raise(r, self._candidate)
        elif target < self.active_level:
            self._candidate = None
            self._new_reason_since = None
            if self._lower_since is None:
                self._lower_since = t
            if t - self._lower_since >= self.config.fall_hold_s:
                self.active_level = target
                self._active_reasons = r.reasons
                self._alerted = set(r.reasons)  # dropping a level is not a new alert (a reminder can follow)
                self._reason_seen = dict.fromkeys(r.reasons, t)
                self._lower_since = None
        else:
            self._candidate = None
            self._lower_since = None
            if target > 0:
                self._active_reasons = r.reasons
                out = self._check_new_reasons(r)
                if out is not None:
                    return out

        return AlertOutput(t, self.active_level, self._active_reasons)
