"""Block 7 helpers shared by the drowsiness sub-modules: rolling windows and small time-series utilities."""

from __future__ import annotations

from collections import deque

import numpy as np


class RollingWindow:
    """(t, value) samples of the last `window_s` seconds; percentile cached for `recompute_s`."""

    def __init__(self, window_s: float, recompute_s: float) -> None:
        self.window_s = window_s
        self.recompute_s = recompute_s
        self._buf: deque[tuple[float, float]] = deque()
        self._cache: dict[float, tuple[float, float]] = {}  # q -> (computed_at, value)

    def add(self, t: float, value: float) -> None:
        """Add a sample and drop those older than `window_s`."""
        self._buf.append((t, value))
        while self._buf and t - self._buf[0][0] > self.window_s:
            self._buf.popleft()

    def drop_since(self, t0: float) -> None:
        """Forget the samples taken at or after t0."""
        while self._buf and self._buf[-1][0] >= t0:
            self._buf.pop()
        self._cache.clear()

    @property
    def span(self) -> float:
        """Seconds between the oldest and the newest sample kept."""
        return self._buf[-1][0] - self._buf[0][0] if len(self._buf) > 1 else 0.0

    def percentile(self, q: float, t: float) -> float | None:
        """The q-th percentile of the kept values (recomputed every `recompute_s`); None when empty."""
        if not self._buf:
            return None
        cached = self._cache.get(q)
        if cached is None or t - cached[0] >= self.recompute_s:
            cached = (t, float(np.percentile([v for _, v in self._buf], q)))
            self._cache[q] = cached
        return cached[1]


SHARE_DIGITS = 9  # a share is rounded here, so that sums of float waits give 18 / 36 = 0.5, not 0.4999999


def share_of(on_s: float, total_s: float) -> float:
    """on_s / total_s as a share that compares cleanly with a threshold (see SHARE_DIGITS); 0 of nothing."""
    return round(on_s / total_s, SHARE_DIGITS) if total_s > 0 else 0.0


class TimeShare:
    """Share of the time a yes / no reading was "yes", on frames at any spacing (M93). `step` is called
    on every frame with the wait since the frame before; a frame that was read stands for half the wait
    before it and half the wait after it (the newest one, whose "after" is not known yet: the wait
    before it). So the first frame after a slow stretch does not carry that whole stretch, and a burst
    of frames counts for no more than the time it spans. At an even frame rate every frame weighs the
    same: exactly the share of frames read, which is what was counted before."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        """Start again with no frame read."""
        self._on_s = 0.0  # frames whose weight is final
        self._total_s = 0.0
        self._newest: tuple[bool, float] | None = None  # (reading, wait before it): weight not final yet

    def step(self, dt: float, on: bool | None) -> None:
        """dt: seconds since the frame before (gaps already capped by the caller). on: None = not read."""
        if self._newest is not None:
            was_on, before = self._newest
            weight = (before + dt) / 2.0
            self._total_s += weight
            self._on_s += weight if was_on else 0.0
        self._newest = None if on is None else (bool(on), dt)

    @property
    def share(self) -> float:
        """Share of the read time whose reading was "yes", in [0, 1]."""
        on, total = self._on_s, self._total_s
        if self._newest is not None:
            total += self._newest[1]
            on += self._newest[1] if self._newest[0] else 0.0
        if total > 0:
            return share_of(on, total)
        return 1.0 if self._newest is not None and self._newest[0] else 0.0  # one frame: the reading itself

    def at_least(self, frac: float) -> bool:
        """False before any frame was read."""
        return (self._total_s > 0 or self._newest is not None) and self.share >= frac


def expire(events: deque[float], t: float, window: float) -> None:
    """Drop event times older than `window` seconds before t."""
    while events and t - events[0] > window:
        events.popleft()


def drop_since(events: deque[float], t0: float) -> None:
    """Drop event times at or after t0."""
    while events and events[-1] >= t0:
        events.pop()


def ramp(x: float, lo: float, hi: float) -> float:
    """Linear ramp from 0 at `lo` to 1 at `hi`, clamped; a step at `hi` when hi <= lo."""
    if hi <= lo:
        return 1.0 if x >= hi else 0.0
    return min(max((x - lo) / (hi - lo), 0.0), 1.0)


def cross_time(a: tuple[float, float], b: tuple[float, float], level: float) -> float:
    """Time where the line from sample a to sample b crosses `level` (linear interpolation)."""
    (ta, va), (tb, vb) = a, b
    if vb == va:
        return tb
    return ta + (level - va) / (vb - va) * (tb - ta)
