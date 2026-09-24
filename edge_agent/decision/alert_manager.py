"""Block 12 - Alert manager.

Turns the per-frame risk level into stable alerts:
- Raise hysteresis: a higher level must hold for rise_confirm_s[level] before it becomes
  active (L3 can be 0 s = immediate). One noisy frame cannot raise an alert.
- Fall hysteresis: the level must stay lower for fall_hold_s before the active level
  drops, so an alert does not flicker on / off.
- Cooldown: once an alert of a level is emitted, the same level is not emitted again
  within cooldown_s[level]. A higher level is always emitted (escalation).

`active_level` is what the HUD shows; `new_alert` is set only on the frame an alert
is emitted (chime / sound / seat vibration, metadata event).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from edge_agent.decision.risk_engine import RiskAssessment

LEVEL_ACTIONS = {
    0: "normal",
    1: "icon + chime",
    2: "sound + seat vibration",
    3: "strong alarm, suggest a break",
}


def _levels(d: dict[Any, Any] | None, default: dict[int, float]) -> dict[int, float]:
    out = dict(default)
    out.update({int(k): float(v) for k, v in (d or {}).items()})
    return out


@dataclass(frozen=True)
class AlertConfig:
    rise_confirm_s: dict[int, float] = field(default_factory=lambda: {1: 1.0, 2: 0.5, 3: 0.0})
    fall_hold_s: float = 3.0
    cooldown_s: dict[int, float] = field(default_factory=lambda: {1: 120.0, 2: 30.0, 3: 10.0})

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> AlertConfig:
        d = d or {}
        default = cls()
        return cls(
            rise_confirm_s=_levels(d.get("rise_confirm_s"), default.rise_confirm_s),
            fall_hold_s=float(d.get("fall_hold_s", default.fall_hold_s)),
            cooldown_s=_levels(d.get("cooldown_s"), default.cooldown_s),
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
        self._last_emit: dict[int, float] = {}

    def _raise(self, r: RiskAssessment, level: int) -> AlertOutput:
        t = r.t
        self.active_level = level
        self._active_reasons = r.reasons
        self._candidate = None
        self._lower_since = None
        last = self._last_emit.get(level)
        if last is not None and t - last < self.config.cooldown_s.get(level, 0.0):
            return AlertOutput(t, level, self._active_reasons, None, suppressed=True)
        self._last_emit[level] = t
        alert = Alert(t, level, r.reasons, r.drowsy_score, r.distraction_score)
        return AlertOutput(t, level, self._active_reasons, alert)

    def update(self, r: RiskAssessment) -> AlertOutput:
        t, target = r.t, r.level

        if target > self.active_level:
            self._lower_since = None
            # A higher target restarts the confirmation; a lower-but-still-raised target keeps it.
            if self._candidate is None or target > self._candidate:
                self._candidate, self._candidate_since = target, t
            elif target < self._candidate:
                self._candidate = target
            if t - self._candidate_since >= self.config.rise_confirm_s.get(self._candidate, 0.0):
                return self._raise(r, self._candidate)
        elif target < self.active_level:
            self._candidate = None
            if self._lower_since is None:
                self._lower_since = t
            if t - self._lower_since >= self.config.fall_hold_s:
                self.active_level = target
                self._active_reasons = r.reasons
                self._lower_since = None
        else:
            self._candidate = None
            self._lower_since = None
            if target > 0:
                self._active_reasons = r.reasons

        return AlertOutput(t, self.active_level, self._active_reasons)
