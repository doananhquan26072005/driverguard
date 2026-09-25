"""Block 11 - Trip memory.

Remembers what happened during the trip so the risk engine can see beyond the
current frame:
- drowsy_score averaged per `bin_s` (one point per minute) and trend_15min = slope of
  a linear regression over the last `trend_window_bins` points (score points / minute).
- time of recent microsleep events (the risk engine's microsleep term).
- alert counts per level.

A rest (the vehicle parked, block 10) is not part of the fatigue timeline: its frames are
not binned (`observed=False`), and `forget_since` drops the bins and microsleeps from the
start of the stop once driving resumes. Timeline samples already sent stay on the backend.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any

import numpy as np

from edge_agent.config import config_from_dict


@dataclass(frozen=True)
class TripMemoryConfig:
    bin_s: float = 60.0
    trend_window_bins: int = 15

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> TripMemoryConfig:
        return config_from_dict(cls, d, "trip_memory")


@dataclass(frozen=True)
class TripState:
    t: float
    elapsed_s: float
    minute_scores: tuple[float, ...]  # completed bins, oldest first (at most trend_window_bins)
    trend_15min: float | None  # drowsy_score points per minute, None until 2 bins exist
    last_microsleep_t: float | None
    alerts_by_level: tuple[int, int, int, int]
    bins_completed: int = 0  # grows by one each time a minute closes (fatigue timeline samples)


def linear_slope(values: list[float] | tuple[float, ...]) -> float | None:
    """Least-squares slope per step; None for fewer than 2 values."""
    if len(values) < 2:
        return None
    x = np.arange(len(values), dtype=float)
    slope, _ = np.polyfit(x, np.asarray(values, dtype=float), 1)
    return float(slope)


class TripMemory:
    def __init__(self, config: TripMemoryConfig | None = None) -> None:
        self.config = config or TripMemoryConfig()
        self._start_t: float | None = None
        self._bin_index = 0
        self._bin_sum = 0.0
        self._bin_count = 0
        self._scores: deque[tuple[int, float]] = deque(maxlen=self.config.trend_window_bins)  # (bin, mean)
        self._microsleeps: list[float] = []
        self._alerts = [0, 0, 0, 0]
        self._bins_completed = 0

    def record_alert(self, level: int) -> None:
        self._alerts[level] += 1

    def forget_since(self, t0: float) -> None:
        """Drop the bins (the one t0 falls in included) and microsleeps from t0 on: a rest."""
        if self._start_t is None:
            return
        first = int((t0 - self._start_t) // self.config.bin_s)
        self._scores = deque(((i, s) for i, s in self._scores if i < first), maxlen=self.config.trend_window_bins)
        if self._bin_index >= first:
            self._bin_sum, self._bin_count = 0.0, 0
        while self._microsleeps and self._microsleeps[-1] >= t0:
            self._microsleeps.pop()

    def update(self, t: float, drowsy_score: float, events: tuple[str, ...] = (), observed: bool = True) -> TripState:
        """observed=False: the frame is not binned and its events are ignored (a rest)."""
        if self._start_t is None:
            self._start_t = t
        index = int((t - self._start_t) // self.config.bin_s)
        if index != self._bin_index:
            if self._bin_count:
                self._scores.append((self._bin_index, self._bin_sum / self._bin_count))
                self._bins_completed += 1
            # Bins with no frames at all (camera stalled, a rest) are skipped, not filled with zeros.
            self._bin_index, self._bin_sum, self._bin_count = index, 0.0, 0
        if observed:
            self._bin_sum += drowsy_score
            self._bin_count += 1
            if "microsleep" in events:
                self._microsleeps.append(t)
        scores = tuple(s for _, s in self._scores)
        return TripState(
            t=t,
            elapsed_s=t - self._start_t,
            minute_scores=scores,
            trend_15min=linear_slope(scores),
            last_microsleep_t=self._microsleeps[-1] if self._microsleeps else None,
            alerts_by_level=tuple(self._alerts),  # type: ignore[arg-type]
            bins_completed=self._bins_completed,
        )
