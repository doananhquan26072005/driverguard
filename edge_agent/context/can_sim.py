"""Block 10 (source) - Simulated CAN bus.

Plays vehicle signals from a YAML scenario, as a real CAN reader would deliver them:

    name: highway_night
    start_clock: "02:30"        # simulated local time at t = 0 (optional: real clock)
    initial_drive_time_s: 6600  # driving time before the scenario starts
    loop: false
    timeline:                   # t in seconds from start
      - {t: 0,   speed_kmh: 0}
      - {t: 10,  speed_kmh: 90}
      - {t: 60,  speed_kmh: 90, turn_signal: left}
      - {t: 64,  speed_kmh: 90, turn_signal: off}

Speed is interpolated linearly between keyframes; turn_signal holds until changed.
`sample(t)` must be called with non-decreasing t (drive time is integrated).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Keyframe:
    t: float
    speed_kmh: float
    turn_signal: str | None = None  # "left" / "right" / "off"; None = unchanged


@dataclass(frozen=True)
class Scenario:
    name: str
    keyframes: tuple[Keyframe, ...]
    start_clock_s: float | None = None  # seconds since local midnight at t = 0
    initial_drive_time_s: float = 0.0
    loop: bool = False

    @property
    def duration(self) -> float:
        return self.keyframes[-1].t


@dataclass(frozen=True)
class VehicleSignals:
    t: float  # scenario time, seconds
    speed_kmh: float
    turn_signal: str | None  # "left" / "right" or None
    drive_time_s: float  # total time spent moving, including initial_drive_time_s
    clock_hour: float  # local time of day, 0..24


def parse_clock(value: str) -> float:
    """'HH:MM' or 'HH:MM:SS' -> seconds since midnight."""
    parts = [int(p) for p in str(value).split(":")]
    h, m, s = (parts + [0, 0])[:3]
    return float(h * 3600 + m * 60 + s)


def scenario_from_dict(d: dict) -> Scenario:
    frames = []
    for kf in d.get("timeline") or []:
        signal = kf.get("turn_signal")
        frames.append(Keyframe(float(kf["t"]), float(kf["speed_kmh"]), None if signal is None else str(signal)))
    if not frames:
        raise ValueError("scenario needs at least one timeline keyframe")
    frames.sort(key=lambda k: k.t)
    clock = d.get("start_clock")
    return Scenario(
        name=str(d.get("name", "scenario")),
        keyframes=tuple(frames),
        start_clock_s=None if clock is None else parse_clock(clock),
        initial_drive_time_s=float(d.get("initial_drive_time_s", 0.0)),
        loop=bool(d.get("loop", False)),
    )


def load_scenario(path: str | Path) -> Scenario:
    with open(path, encoding="utf-8") as f:
        return scenario_from_dict(yaml.safe_load(f) or {})


class CanSimulator:
    def __init__(self, scenario: Scenario, moving_kmh: float = 5.0) -> None:
        self.scenario = scenario
        self.moving_kmh = moving_kmh
        if scenario.start_clock_s is not None:
            self._clock0 = scenario.start_clock_s
        else:
            now = time.localtime()
            self._clock0 = float(now.tm_hour * 3600 + now.tm_min * 60 + now.tm_sec)
        self._drive_time = scenario.initial_drive_time_s
        self._last_t: float | None = None
        self._last_speed = 0.0

    def _scenario_time(self, t: float) -> float:
        d = self.scenario.duration
        if self.scenario.loop and d > 0:
            return t % d
        return t

    def speed_at(self, t: float) -> float:
        frames = self.scenario.keyframes
        st = self._scenario_time(t)
        if st <= frames[0].t:
            return frames[0].speed_kmh
        for a, b in zip(frames, frames[1:], strict=False):
            if a.t <= st <= b.t:
                if b.t == a.t:
                    return b.speed_kmh
                return a.speed_kmh + (b.speed_kmh - a.speed_kmh) * (st - a.t) / (b.t - a.t)
        return frames[-1].speed_kmh

    def turn_signal_at(self, t: float) -> str | None:
        st = self._scenario_time(t)
        state: str | None = None
        for kf in self.scenario.keyframes:
            if kf.t > st:
                break
            if kf.turn_signal is not None:
                state = None if kf.turn_signal == "off" else kf.turn_signal
        return state

    def sample(self, t: float) -> VehicleSignals:
        speed = self.speed_at(t)
        if self._last_t is not None and t > self._last_t and self._last_speed >= self.moving_kmh:
            self._drive_time += t - self._last_t
        self._last_t, self._last_speed = t, speed
        return VehicleSignals(
            t=t,
            speed_kmh=speed,
            turn_signal=self.turn_signal_at(t),
            drive_time_s=self._drive_time,
            clock_hour=((self._clock0 + t) % 86400) / 3600.0,
        )
