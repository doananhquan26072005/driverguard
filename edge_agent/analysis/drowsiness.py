"""Block 7 - Drowsiness branch.

Per frame, from FrameFeatures (EAR, MAR, head pose), computes:
- eye_closed: per-frame eye state (None when it cannot be judged). From EAR, or from the
  eye-state CNN (block 5, `p_closed`) on frames where EAR is not reliable.
- closed_duration: seconds of the current eye-closure episode.
- perclos_60s: fraction of time the eyes were closed over the last `perclos_window_s`.
- blink_rate: blinks per minute (closures shorter than `blink_max_s`).
- yawn_count_10min, nod_count_5min: events in their windows.
and emits events ("blink", "microsleep", "yawn", "nod", "perclos_high") on the frame
they happen.

Anti false-positive rules:
- Eye closure is relative to the driver's own open-eye EAR (a high percentile of recent
  EAR), so narrow eyes are not "always closed". Hysteresis between close / reopen.
- Eye state is not judged when the head is turned far or tilted down (EAR collapses
  in those poses): no PERCLOS accumulation from looking at the dashboard.
- A yawn needs the mouth wide open for `yawn_min_s` (talking / laughing are shorter).
- A nod is a head dip relative to the driver's usual pitch that comes back within
  `nod_max_s` AND has the eyes closed for part of it (a glance at the speedometer
  keeps the eyes open).
- PERCLOS only raises "perclos_high" after `perclos_min_coverage_s` of eye data.
- Short face dropouts (< max_gap_s) do not break episodes; longer ones end them
  without counting a blink.

Pure logic on timestamps: no image, no clock, testable with fake sequences.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any

import numpy as np

from edge_agent.config import flatten
from edge_agent.perception.features import FrameFeatures


@dataclass(frozen=True)
class DrowsinessConfig:
    max_gap_s: float = 0.5
    # Eye state
    eye_baseline_init: float = 0.28
    eye_baseline_percentile: float = 90.0
    eye_baseline_window_s: float = 120.0
    eye_baseline_min_data_s: float = 10.0
    eye_baseline_min: float = 0.18
    eye_baseline_max: float = 0.42
    eye_close_ratio: float = 0.65
    eye_open_ratio: float = 0.75
    eye_max_yaw_deg: float = 35.0
    eye_max_pitch_down_deg: float = 25.0
    # Eye-state CNN (block 5) probabilities, with hysteresis
    eye_cnn_closed: float = 0.6
    eye_cnn_open: float = 0.4
    # Closure episodes
    blink_max_s: float = 0.5
    blink_window_s: float = 60.0
    microsleep_min_s: float = 1.0
    # PERCLOS
    perclos_window_s: float = 60.0
    perclos_min_coverage_s: float = 30.0
    perclos_drowsy: float = 0.15
    perclos_rearm: float = 0.12
    # Yawn
    yawn_mar_open: float = 0.6
    yawn_mar_close: float = 0.45
    yawn_min_s: float = 1.5
    yawn_window_s: float = 600.0
    # Nod
    nod_pitch_down_deg: float = 15.0
    nod_return_deg: float = 7.0
    nod_min_s: float = 0.2
    nod_max_s: float = 2.0
    nod_require_eyes_closed: bool = True
    nod_eyes_closed_min_frac: float = 0.3
    nod_window_s: float = 300.0
    # Head pose reference (rolling median of yaw / pitch)
    pose_baseline_window_s: float = 60.0

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> DrowsinessConfig:
        flat = flatten(d)
        return cls(**{k: flat[k] for k in cls.__dataclass_fields__ if k in flat})


@dataclass(frozen=True)
class DrowsinessState:
    timestamp: float
    eye_closed: bool | None
    closed_duration: float
    microsleep: bool  # current closure is at least microsleep_min_s long
    perclos_60s: float
    perclos_coverage_s: float  # seconds of eye data inside the PERCLOS window
    blink_rate: float  # blinks per minute
    yawning: bool
    yawn_count_10min: int
    nod_count_5min: int
    ear_open_baseline: float
    ear_closed_threshold: float
    events: tuple[str, ...] = ()
    eye_source: str | None = None  # "ear" or "cnn": what decided eye_closed on this frame


class RollingWindow:
    """(t, value) samples of the last `window_s` seconds; percentile cached for `recompute_s`."""

    def __init__(self, window_s: float, recompute_s: float = 1.0) -> None:
        self.window_s = window_s
        self.recompute_s = recompute_s
        self._buf: deque[tuple[float, float]] = deque()
        self._cache: dict[float, tuple[float, float]] = {}  # q -> (computed_at, value)

    def add(self, t: float, value: float) -> None:
        self._buf.append((t, value))
        while self._buf and t - self._buf[0][0] > self.window_s:
            self._buf.popleft()

    @property
    def span(self) -> float:
        return self._buf[-1][0] - self._buf[0][0] if len(self._buf) > 1 else 0.0

    def percentile(self, q: float, t: float) -> float | None:
        if not self._buf:
            return None
        cached = self._cache.get(q)
        if cached is None or t - cached[0] >= self.recompute_s:
            cached = (t, float(np.percentile([v for _, v in self._buf], q)))
            self._cache[q] = cached
        return cached[1]


class DrowsinessAnalyzer:
    def __init__(self, config: DrowsinessConfig | None = None) -> None:
        self.config = config or DrowsinessConfig()
        cfg = self.config
        self._ear = RollingWindow(cfg.eye_baseline_window_s)
        self._yaw = RollingWindow(cfg.pose_baseline_window_s)
        self._pitch = RollingWindow(cfg.pose_baseline_window_s)
        self._start_t: float | None = None
        self._last_t: float | None = None
        # eye
        self._eye_closed = False
        self._last_eye_t: float | None = None
        self._closed_since: float | None = None
        self._microsleep_fired = False
        self._blinks: deque[float] = deque()
        self._perclos: deque[tuple[float, float, bool]] = deque()  # (t, dt, closed)
        self._perclos_closed = 0.0
        self._perclos_known = 0.0
        self._perclos_armed = True
        # yawn
        self._mouth_open_since: float | None = None
        self._last_mar_t: float | None = None
        self._yawn_fired = False
        self._yawns: deque[float] = deque()
        # nod
        self._dip_start: float | None = None
        self._dip_known = 0.0
        self._dip_closed = 0.0
        self._last_pose_t: float | None = None
        self._nods: deque[float] = deque()

    # ------------------------------------------------------------------ helpers
    def ear_baseline(self, t: float) -> float:
        cfg = self.config
        if self._ear.span < cfg.eye_baseline_min_data_s:
            return cfg.eye_baseline_init
        value = self._ear.percentile(cfg.eye_baseline_percentile, t)
        return min(max(value, cfg.eye_baseline_min), cfg.eye_baseline_max)

    @staticmethod
    def _expire(events: deque[float], t: float, window: float) -> None:
        while events and t - events[0] > window:
            events.popleft()

    # ------------------------------------------------------------------ main update
    def update(self, f: FrameFeatures) -> DrowsinessState:
        cfg = self.config
        t = f.timestamp
        if self._start_t is None:
            self._start_t = t
        dt = 0.0 if self._last_t is None else min(max(0.0, t - self._last_t), cfg.max_gap_s)
        self._last_t = t
        events: list[str] = []

        # Head pose relative to the driver's usual pose (rolling median).
        yaw_off = pitch_off = None
        if f.face_found and f.yaw is not None and f.pitch is not None:
            self._yaw.add(t, f.yaw)
            self._pitch.add(t, f.pitch)
            yaw_off = f.yaw - self._yaw.percentile(50, t)
            pitch_off = f.pitch - self._pitch.percentile(50, t)
            self._last_pose_t = t

        # Eye state with a per-driver threshold.
        pose_ok = (
            yaw_off is not None and abs(yaw_off) <= cfg.eye_max_yaw_deg and pitch_off <= cfg.eye_max_pitch_down_deg
        )
        # Block 5 (eye-state CNN) decides when it ran: EAR was judged unreliable on this frame.
        use_cnn = f.face_found and f.p_closed is not None
        eye_known = f.face_found and pose_ok and (use_cnn or f.ear is not None)
        if eye_known and f.ear is not None and (not use_cnn or f.p_closed <= cfg.eye_cnn_open):
            self._ear.add(t, f.ear)  # an unreliable EAR must not become the driver's "open eye" value
        baseline = self.ear_baseline(t)
        close_thr = baseline * cfg.eye_close_ratio
        open_thr = baseline * cfg.eye_open_ratio
        if use_cnn:
            ear_low = f.p_closed >= cfg.eye_cnn_closed  # raw, ignores pose (used by nod)
        else:
            ear_low = None if f.ear is None else f.ear < close_thr

        eye_closed: bool | None = None
        if eye_known:
            if use_cnn:
                closing, opening = f.p_closed >= cfg.eye_cnn_closed, f.p_closed <= cfg.eye_cnn_open
            else:
                closing, opening = f.ear < close_thr, f.ear > open_thr
            if self._eye_closed and opening:
                self._eye_closed = False
            elif not self._eye_closed and closing:
                self._eye_closed = True
            eye_closed = self._eye_closed

        self._update_closure(t, eye_closed, events)
        closed_duration = t - self._closed_since if self._closed_since is not None else 0.0
        if closed_duration >= cfg.microsleep_min_s and not self._microsleep_fired:
            self._microsleep_fired = True
            events.append("microsleep")

        perclos, coverage = self._update_perclos(t, dt, eye_closed, events)
        blink_rate = self._blink_rate(t)
        yawning = self._update_yawn(t, f.mar, events)
        self._update_nod(t, dt, pitch_off, ear_low, events)

        self._expire(self._yawns, t, cfg.yawn_window_s)
        self._expire(self._nods, t, cfg.nod_window_s)
        return DrowsinessState(
            timestamp=t,
            eye_closed=eye_closed,
            eye_source=None if eye_closed is None else ("cnn" if use_cnn else "ear"),
            closed_duration=closed_duration,
            microsleep=closed_duration >= cfg.microsleep_min_s,
            perclos_60s=perclos,
            perclos_coverage_s=coverage,
            blink_rate=blink_rate,
            yawning=yawning,
            yawn_count_10min=len(self._yawns),
            nod_count_5min=len(self._nods),
            ear_open_baseline=baseline,
            ear_closed_threshold=close_thr,
            events=tuple(events),
        )

    # ------------------------------------------------------------------ sub-steps
    def _end_closure(self) -> None:
        self._closed_since = None
        self._microsleep_fired = False

    def _update_closure(self, t: float, eye_closed: bool | None, events: list[str]) -> None:
        cfg = self.config
        if eye_closed is None:
            # Unknown: keep a running episode through short dropouts only.
            if self._closed_since is not None and self._last_eye_t is not None and t - self._last_eye_t > cfg.max_gap_s:
                self._end_closure()
            return
        self._last_eye_t = t
        if eye_closed:
            if self._closed_since is None:
                self._closed_since = t
        elif self._closed_since is not None:
            if t - self._closed_since <= cfg.blink_max_s:
                self._blinks.append(t)
                events.append("blink")
            self._end_closure()

    def _update_perclos(self, t: float, dt: float, eye_closed: bool | None, events: list[str]) -> tuple[float, float]:
        cfg = self.config
        if eye_closed is not None and dt > 0:
            self._perclos.append((t, dt, eye_closed))
            self._perclos_known += dt
            self._perclos_closed += dt if eye_closed else 0.0
        while self._perclos and t - self._perclos[0][0] > cfg.perclos_window_s:
            _, old_dt, old_closed = self._perclos.popleft()
            self._perclos_known -= old_dt
            self._perclos_closed -= old_dt if old_closed else 0.0
        known = max(self._perclos_known, 0.0)
        perclos = self._perclos_closed / known if known > 1e-9 else 0.0
        if known >= cfg.perclos_min_coverage_s:
            if self._perclos_armed and perclos >= cfg.perclos_drowsy:
                self._perclos_armed = False
                events.append("perclos_high")
            elif not self._perclos_armed and perclos < cfg.perclos_rearm:
                self._perclos_armed = True
        return perclos, known

    def _blink_rate(self, t: float) -> float:
        cfg = self.config
        self._expire(self._blinks, t, cfg.blink_window_s)
        observed = min(t - self._start_t, cfg.blink_window_s)
        return len(self._blinks) / max(observed, 10.0) * 60.0

    def _update_yawn(self, t: float, mar: float | None, events: list[str]) -> bool:
        cfg = self.config
        if mar is None:
            if (
                self._mouth_open_since is not None
                and self._last_mar_t is not None
                and t - self._last_mar_t > cfg.max_gap_s
            ):
                self._mouth_open_since = None
                self._yawn_fired = False
            return self._yawn_fired
        self._last_mar_t = t
        if self._mouth_open_since is None:
            if mar > cfg.yawn_mar_open:
                self._mouth_open_since = t
        elif mar < cfg.yawn_mar_close:
            self._mouth_open_since = None
            self._yawn_fired = False
        if self._mouth_open_since is not None and not self._yawn_fired and t - self._mouth_open_since >= cfg.yawn_min_s:
            self._yawn_fired = True
            self._yawns.append(t)
            events.append("yawn")
        return self._yawn_fired

    def _update_nod(
        self, t: float, dt: float, pitch_off: float | None, ear_low: bool | None, events: list[str]
    ) -> None:
        cfg = self.config
        if pitch_off is None:
            if self._dip_start is not None and self._last_pose_t is not None and t - self._last_pose_t > cfg.max_gap_s:
                self._dip_start = None  # face lost too long: drop the dip rather than guess
            return
        if self._dip_start is None:
            if pitch_off > cfg.nod_pitch_down_deg:
                self._dip_start, self._dip_known, self._dip_closed = t, 0.0, 0.0
            return
        if ear_low is not None:
            self._dip_known += dt
            self._dip_closed += dt if ear_low else 0.0
        if pitch_off < cfg.nod_return_deg:
            duration = t - self._dip_start
            closed_frac = self._dip_closed / self._dip_known if self._dip_known > 0 else 0.0
            eyes_ok = not cfg.nod_require_eyes_closed or closed_frac >= cfg.nod_eyes_closed_min_frac
            if cfg.nod_min_s <= duration <= cfg.nod_max_s and eyes_ok:
                self._nods.append(t)
                events.append("nod")
            self._dip_start = None


def describe_events(state: DrowsinessState) -> list[str]:
    """Human-readable terminal lines for the drowsiness events of this frame (blinks excluded)."""
    lines = []
    for ev in state.events:
        if ev == "microsleep":
            lines.append(f"[DROWSY] microsleep: eyes closed {state.closed_duration:.1f} s")
        elif ev == "perclos_high":
            lines.append(f"[DROWSY] PERCLOS {state.perclos_60s:.2f} over the last {state.perclos_coverage_s:.0f} s")
        elif ev == "yawn":
            lines.append(f"[DROWSY] yawn ({state.yawn_count_10min} in 10 min)")
        elif ev == "nod":
            lines.append(f"[DROWSY] head nod ({state.nod_count_5min} in 5 min)")
    return lines
