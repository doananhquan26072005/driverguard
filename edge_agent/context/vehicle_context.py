"""Block 10 - Vehicle context.

Turns raw vehicle signals (speed, turn signal, drive time, time of day) into the
flags the risk engine uses: moving, high speed, night, long drive, and to which side
looking sideways is expected right now (turn signal on, plus a short grace period:
`turn_side`, used by block 8 to widen the yaw limit on that side only). A signal left on is not a
turn: once it has been on to one side for `turn_signal_max_s` of driving, `turn_side` ends (after
the grace period) until the signal goes off or changes side. Before, a blinker forgotten on the
motorway widened that side for as long as it stayed on. Time standing still is not counted: waiting
at a light to turn can take longer than any turn.

This is the only place that decides whether the vehicle is moving: the distraction
branch (block 8) and the risk engine (block 9) both use `VehicleContext.moving`.
No speed signal (speed_kmh None, e.g. CAN not connected) counts as moving when
`assume_moving_when_speed_unknown` is set, and never as high speed.

Standing still (speed below `stationary_kmh`, not just below `min_speed_kmh`: crawling in a
jam is not a stop) is what the drowsiness side uses: a short stop (red light) caps the
drowsiness level, and standing still for `rest_after_s` is a rest (parked), when the
driver may close the eyes on purpose. No speed signal is never standing still.

`rolling` is everything that is not standing still: moving, and the crawl between `stationary_kmh`
and `min_speed_kmh` (a jam). The distraction rules stay off in a crawl, but the driver must still be
in view there, so "monitoring unavailable" (block 9) follows `rolling`, not `moving` (M72).

Long drive is about the driver at the wheel now, so it is judged on `drive_run_s`: the driving time
since the last rest or driver change (`ContextTracker.new_driver`), not on the source's
`drive_time_s`, which only ever grows. Before M73 it was the latter: once two hours had been driven
the long-drive factor stayed on through every rest and for every later driver. The HUD's
"Lái liên tục" shows this same counter.

A stop of `short_stop_forget_s` or longer that is not yet a rest (a red light) is reported as
`long_stop`; the pipeline drops what the drowsiness side gathered during such a stop once the
vehicle drives off (see edge_agent/decision/pipeline.py).
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
    turn_signal_max_s: float = 30.0  # driving with the signal on to one side this long: no turn (0 = no limit)
    stationary_kmh: float = 1.0
    rest_after_s: float = 120.0
    short_stop_forget_s: float = 10.0  # a stop this long: what it gathered is dropped on driving off
    vehicle_signal_stale_s: float = 1.0  # external speed source silent this long = standing still
    vehicle_signal_wait_s: float = 30.0  # a driver in view this long and never a reading: speed unknown (0 = off)
    vehicle_poll_s: float = 0.25  # the agent asks for the vehicle signals this often
    vehicle_send_s: float = 0.2  # the web driving controls (#/drive) send them this often

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> ContextConfig:
        """Build the config from the `context` section of thresholds.yaml; an unknown key is an error."""
        d = dict(d or {})
        check_keys("context", {k: k for k in d}, cls.__dataclass_fields__)
        if "night_hours" in d:
            d["night_hours"] = tuple((float(a), float(b)) for a, b in d["night_hours"])
        return cls(**d)

    def is_moving(self, speed_kmh: float | None) -> bool:
        """True at `min_speed_kmh` or above; an unknown speed follows `assume_moving_when_speed_unknown`."""
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
    turn_side: str | None = None  # "left" / "right" while turning (the last signalled side)
    drive_run_s: float = 0.0  # driving time since the last rest / driver change: what long_drive is judged on
    long_stop: bool = False  # stood still for short_stop_forget_s (see module doc); stays True in a rest

    @property
    def rolling(self) -> bool:
        """Not standing still: moving, or crawling below min_speed_kmh (see module doc)."""
        return self.moving or (self.speed_kmh is not None and not self.stationary)


def in_hours(hour: float, windows: tuple[tuple[float, float], ...]) -> bool:
    """True when `hour` falls in one of the (start, end) windows; a window may wrap midnight."""
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
        self._last_side: str | None = None
        self._signal_side: str | None = None  # the side the signal is on now
        self._signal_run = 0.0  # ... and for how long while moving
        self._last_t: float | None = None
        self._stationary_since: float | None = None
        self._drive_time: float | None = None  # the source's drive_time_s at the last update
        self._drive_run = 0.0

    def new_driver(self) -> None:
        """Another driver took the wheel: their continuous driving starts at 0."""
        self._drive_run = 0.0

    def update(self, s: VehicleSignals) -> VehicleContext:
        """Block 10, one frame: turn the raw vehicle signals into the context the risk engine reads
        (moving, high speed, night, turning, stationary, resting, long drive)."""
        cfg = self.config
        dt = 0.0 if self._last_t is None else max(0.0, s.t - self._last_t)
        self._last_t = s.t
        if s.turn_signal is None:
            self._signal_side = None
        else:
            if s.turn_signal != self._signal_side:
                self._signal_side, self._signal_run = s.turn_signal, 0.0
            elif cfg.is_moving(s.speed_kmh):
                self._signal_run += dt
            if cfg.turn_signal_max_s <= 0 or self._signal_run <= cfg.turn_signal_max_s:
                self._last_signal_t = s.t
                self._last_side = s.turn_signal
        turning = self._last_signal_t is not None and s.t - self._last_signal_t <= cfg.turn_signal_grace_s
        stationary = s.speed_kmh is not None and s.speed_kmh < cfg.stationary_kmh
        if not stationary:
            self._stationary_since = None
        elif self._stationary_since is None:
            self._stationary_since = s.t
        stationary_s = s.t - self._stationary_since if self._stationary_since is not None else 0.0
        resting = stationary and stationary_s >= cfg.rest_after_s
        # The first reading carries the driving done before the agent started (a scenario's initial_drive_time_s).
        self._drive_run += s.drive_time_s - self._drive_time if self._drive_time is not None else s.drive_time_s
        self._drive_time = s.drive_time_s
        if resting:
            self._drive_run = 0.0
        return VehicleContext(
            t=s.t,
            speed_kmh=s.speed_kmh,
            moving=cfg.is_moving(s.speed_kmh),
            high_speed=s.speed_kmh is not None and s.speed_kmh >= cfg.high_speed_kmh,
            night=in_hours(s.clock_hour, cfg.night_hours),
            long_drive=self._drive_run >= cfg.long_drive_s,
            turning=turning,
            drive_time_s=s.drive_time_s,
            clock_hour=s.clock_hour,
            stationary=stationary,
            stationary_s=stationary_s,
            resting=resting,
            turn_side=self._last_side if turning else None,
            drive_run_s=self._drive_run,
            long_stop=stationary and stationary_s >= cfg.short_stop_forget_s,
        )
