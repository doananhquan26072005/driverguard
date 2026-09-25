"""Block 10 - Vehicle context.

Turns raw vehicle signals (speed, turn signal, drive time, time of day) into the
flags the risk engine uses: moving, high speed, night, long drive, and whether
looking sideways is expected right now (turn signal on, plus a short grace period).

This is the only place that decides whether the vehicle is moving: the distraction
branch (block 8) and the risk engine (block 9) both use `VehicleContext.moving`.
No speed signal (speed_kmh None, e.g. CAN not connected) counts as moving when
`assume_moving_when_speed_unknown` is set, and never as high speed.

Standing still (speed below `stationary_kmh`, not just below `min_speed_kmh`: crawling in a
jam is not a stop) is what the drowsiness side uses: a short stop (red light) caps the
drowsiness level, and standing still for `rest_after_s` is a rest (parked), when the
driver may close the eyes on purpose. No speed signal is never standing still.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from edge_agent.config import check_keys
from edge_agent.context.can_sim import VehicleSignals


@dataclass(frozen=True)
class ContextConfig:
    min_speed_kmh: float = 5.0
    assume_moving_when_speed_unknown: bool = True
    high_speed_kmh: float = 80.0
    long_drive_s: float = 7200.0
    night_hours: tuple[tuple[float, float], ...] = ((0.0, 5.0),)
    turn_signal_grace_s: float = 2.0
    stationary_kmh: float = 1.0
    rest_after_s: float = 120.0

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> ContextConfig:
        d = dict(d or {})
        check_keys("context", {k: k for k in d}, cls.__dataclass_fields__)
        if "night_hours" in d:
            d["night_hours"] = tuple((float(a), float(b)) for a, b in d["night_hours"])
        return cls(**d)

    def is_moving(self, speed_kmh: float | None) -> bool:
        if speed_kmh is None:
            return self.assume_moving_when_speed_unknown
        return speed_kmh >= self.min_speed_kmh


@dataclass(frozen=True)
class VehicleContext:
    t: float
    speed_kmh: float | None  # None = no CAN data
    moving: bool
    high_speed: bool
    night: bool
    long_drive: bool
    turning: bool  # turn signal on, or switched off less than turn_signal_grace_s ago
    drive_time_s: float
    clock_hour: float
    stationary: bool = False  # speed below stationary_kmh (a stop, not a crawl)
    stationary_s: float = 0.0  # seconds the vehicle has stood still, 0 otherwise
    resting: bool = False  # stood still for rest_after_s: a rest (parked), not a red light


def in_hours(hour: float, windows: tuple[tuple[float, float], ...]) -> bool:
    for start, end in windows:
        if start <= end:
            if start <= hour < end:
                return True
        elif hour >= start or hour < end:  # window wraps midnight, e.g. (22, 5)
            return True
    return False


class ContextTracker:
    def __init__(self, config: ContextConfig | None = None) -> None:
        self.config = config or ContextConfig()
        self._last_signal_t: float | None = None
        self._stationary_since: float | None = None

    def update(self, s: VehicleSignals) -> VehicleContext:
        cfg = self.config
        if s.turn_signal is not None:
            self._last_signal_t = s.t
        turning = self._last_signal_t is not None and s.t - self._last_signal_t <= cfg.turn_signal_grace_s
        stationary = s.speed_kmh is not None and s.speed_kmh < cfg.stationary_kmh
        if not stationary:
            self._stationary_since = None
        elif self._stationary_since is None:
            self._stationary_since = s.t
        stationary_s = s.t - self._stationary_since if self._stationary_since is not None else 0.0
        return VehicleContext(
            t=s.t,
            speed_kmh=s.speed_kmh,
            moving=cfg.is_moving(s.speed_kmh),
            high_speed=s.speed_kmh is not None and s.speed_kmh >= cfg.high_speed_kmh,
            night=in_hours(s.clock_hour, cfg.night_hours),
            long_drive=s.drive_time_s >= cfg.long_drive_s,
            turning=turning,
            drive_time_s=s.drive_time_s,
            clock_hour=s.clock_hour,
            stationary=stationary,
            stationary_s=stationary_s,
            resting=stationary and stationary_s >= cfg.rest_after_s,
        )
