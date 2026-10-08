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
        return self._buf[-1][0] - self._buf[0][0] if len(self._buf) > 1 else 0.0

    def percentile(self, q: float, t: float) -> float | None:
        if not self._buf:
            return None
        cached = self._cache.get(q)
        if cached is None or t - cached[0] >= self.recompute_s:
            cached = (t, float(np.percentile([v for _, v in self._buf], q)))
            self._cache[q] = cached
        return cached[1]


def expire(events: deque[float], t: float, window: float) -> None:
    """Drop event times older than `window` seconds before t."""
    while events and t - events[0] > window:
        events.popleft()


def drop_since(events: deque[float], t0: float) -> None:
    """Drop event times at or after t0."""
    while events and events[-1] >= t0:
        events.pop()


def ramp(x: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 1.0 if x >= hi else 0.0
    return min(max((x - lo) / (hi - lo), 0.0), 1.0)


def cross_time(a: tuple[float, float], b: tuple[float, float], level: float) -> float:
    """Time where the line from sample a to sample b crosses `level` (linear interpolation)."""
    (ta, va), (tb, vb) = a, b
    if vb == va:
        return tb
    return ta + (level - va) / (vb - va) * (tb - ta)
