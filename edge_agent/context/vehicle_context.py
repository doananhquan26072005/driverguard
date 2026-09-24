"""Block 10 - Vehicle context.

Turns raw vehicle signals (speed, turn signal, drive time, time of day) into the
flags the risk engine uses: moving, high speed, night, long drive, and whether
looking sideways is expected right now (turn signal on, plus a short grace period).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from edge_agent.context.can_sim import VehicleSignals


@dataclass(frozen=True)
class ContextConfig:
    min_speed_kmh: float = 5.0
    high_speed_kmh: float = 80.0
    long_drive_s: float = 7200.0
    night_hours: tuple[tuple[float, float], ...] = ((0.0, 5.0),)
    turn_signal_grace_s: float = 2.0

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> ContextConfig:
        d = dict(d or {})
        if "night_hours" in d:
            d["night_hours"] = tuple((float(a), float(b)) for a, b in d["night_hours"])
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d})


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

    def update(self, s: VehicleSignals) -> VehicleContext:
        cfg = self.config
        if s.turn_signal is not None:
            self._last_signal_t = s.t
        turning = self._last_signal_t is not None and s.t - self._last_signal_t <= cfg.turn_signal_grace_s
        return VehicleContext(
            t=s.t,
            speed_kmh=s.speed_kmh,
            moving=s.speed_kmh >= cfg.min_speed_kmh,
            high_speed=s.speed_kmh >= cfg.high_speed_kmh,
            night=in_hours(s.clock_hour, cfg.night_hours),
            long_drive=s.drive_time_s >= cfg.long_drive_s,
            turning=turning,
            drive_time_s=s.drive_time_s,
            clock_hour=s.clock_hour,
        )
