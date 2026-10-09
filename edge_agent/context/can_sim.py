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

`ExternalVehicle` (the default of edge_agent.main and #/live) has no timeline: speed and turn
signal come from outside the agent, today from tools/drive_sim.py (the driving simulator the
tester runs next to it), later from a real CAN reader. No fresh signal for
`context.vehicle_signal_stale_s` (simulator not running, link lost):
- never had a signal, or the last one said the vehicle stood still (below `stationary_kmh`):
  standing still at 0 km/h, parked until a speed says otherwise;
- either way, once a signal had come in, the link is lost (`link_lost`) and the driver is told (M26);
- the last signal said the vehicle was driving: `signal_lost`, the speed is unknown (None). Block 10 then treats the vehicle as moving (`assume_moving_when_speed_unknown`),
  so monitoring goes on and the stop never becomes a rest; the runtime tells the driver and the
  backend. Before this, a lost link while driving read as parked: distraction off, drowsiness
  capped at L1, then off after `rest_after_s` (docs/safety-fmea.md, row 2).
The time of day is the real clock.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
    speed_kmh: float | None  # None = no speed signal (the simulator always has one)
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


SIM = "sim"  # scenario name of the default vehicle source: ExternalVehicle fed by tools/drive_sim.py
DEFAULT_SIM_URL = "http://127.0.0.1:8766/can"


class ExternalVehicle:
    """Vehicle signals pushed from outside (see module doc). Thread-safe enough for one writer
    (the link) and one reader (the main loop): plain attribute swaps."""

    def __init__(
        self,
        stale_s: float = 1.0,
        moving_kmh: float = 5.0,
        clock: Any = time.monotonic,
        stationary_kmh: float = 1.0,
        wait_s: float = 0.0,
    ) -> None:
        """wait_s: context.vehicle_signal_wait_s (0 = never had a reading stays "parked" for good)."""
        self.stale_s = stale_s
        self.wait_s = wait_s
        self._watched_s = 0.0  # time the camera has watched a driver without any reading yet (M95)
        self._watch_t: float | None = None
        self.moving_kmh = moving_kmh
        self.stationary_kmh = stationary_kmh  # last reading below this when lost = parked, not lost
        self._clock = clock
        now = time.localtime()
        self._clock0 = float(now.tm_hour * 3600 + now.tm_min * 60 + now.tm_sec)
        self._speed = 0.0
        self._turn: str | None = None
        self._received: float | None = None  # clock() of the last update
        self._drive_time = 0.0
        self._last_t: float | None = None
        self._last_moving = False

    def update(self, speed_kmh: float, turn_signal: str | None) -> None:
        """A fresh reading (km/h, "left" / "right" / None)."""
        self._speed = max(0.0, float(speed_kmh))
        self._turn = turn_signal if turn_signal in ("left", "right") else None
        self._received = self._clock()

    @property
    def connected(self) -> bool:
        return self._received is not None and self._clock() - self._received <= self.stale_s

    def observe(self, t: float, watching: bool) -> None:
        """Called on every frame, before `sample`. watching: the camera sees a driver who is not being
        enrolled. Without any reading yet, that time is counted towards `wait_s` (M95); a frame after
        a hole counts `stale_s` at most."""
        if watching and self._received is None and self._watch_t is not None:
            self._watched_s += min(max(t - self._watch_t, 0.0), self.stale_s)
        self._watch_t = t

    @property
    def never_received(self) -> bool:
        """No reading ever came, and a driver has been in view for `wait_s`: not "parked" any more but
        speed unknown, monitored as moving, and the driver is told (M95). Before, a page with no speed
        source stood "parked" for the whole trip and raised no alert at all."""
        return self._received is None and self.wait_s > 0 and self._watched_s >= self.wait_s

    @property
    def link_lost(self) -> bool:
        """A signal had come in and the link went quiet (driving or parked), or none ever came
        (`never_received`): the driver is told."""
        return (self._received is not None and not self.connected) or self.never_received

    @property
    def signal_lost(self) -> bool:
        """Speed unknown: the link went quiet while the last reading said the vehicle was driving, or no
        reading ever came (`never_received`)."""
        lost_driving = self._received is not None and not self.connected and self._speed >= self.stationary_kmh
        return lost_driving or self.never_received

    def sample(self, t: float) -> VehicleSignals:
        live = self.connected
        speed: float | None = self._speed if live else (None if self.signal_lost else 0.0)
        moving = speed is None or speed >= self.moving_kmh  # lost while driving: still driving
        if self._last_t is not None and t > self._last_t and self._last_moving:
            self._drive_time += t - self._last_t
        self._last_t, self._last_moving = t, moving
        return VehicleSignals(
            t=t,
            speed_kmh=speed,
            turn_signal=self._turn if live else None,
            drive_time_s=self._drive_time,
            clock_hour=((self._clock0 + t) % 86400) / 3600.0,
        )


def hud_vehicle(
    source: str,
    connected: bool,
    signals: VehicleSignals | None,
    stationary_kmh: float,
    signal_lost: bool = False,
    never_received: bool = False,
) -> dict:
    """The HUD's vehicle card: where the speed comes from, and parked / driving by the speed alone
    (below `context.stationary_kmh` = stopped / parked). signal_lost: the link went quiet while driving,
    speed unknown (None), still counted as driving; with `driving` False the link went quiet while parked.
    never_received: the signal is "lost" because none ever came (M95); the HUD words it that way."""
    speed = signals.speed_kmh if signals is not None else 0.0
    return {
        "source": source,
        "connected": connected,
        "speed_kmh": None if speed is None else round(speed, 1),
        "turn_signal": None if signals is None else signals.turn_signal,
        "driving": speed is None or speed >= stationary_kmh,
        "signal_lost": signal_lost,
        "never_received": never_received,
    }


class SignalLink:
    """Device side: polls tools/drive_sim.py (GET url -> {"speed_kmh", "turn_signal"}) on a thread
    and feeds an ExternalVehicle. Only numbers go through it."""

    def __init__(self, vehicle: ExternalVehicle, url: str, period_s: float) -> None:
        """period_s: context.vehicle_poll_s."""
        import threading

        self.vehicle, self.url, self.period_s = vehicle, url, period_s
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="SignalLink", daemon=True)

    def start(self) -> SignalLink:
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=1.0)

    def poll_once(self) -> bool:
        import json
        import urllib.request

        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 127.0.0.1: no proxy lookup
            with opener.open(self.url, timeout=self.period_s * 2) as resp:
                d = json.loads(resp.read())
            self.vehicle.update(float(d.get("speed_kmh", 0.0)), d.get("turn_signal"))
            return True
        except (OSError, ValueError):
            return False  # simulator not running: the vehicle goes stale -> parked

    def _run(self) -> None:
        while not self._stop.is_set():
            self.poll_once()
            self._stop.wait(self.period_s)
