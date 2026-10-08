"""Block 7, slow blinks: blink duration and eyelid reopening time.

Caffier et al. 2003: eyelid reopening 162 -> 273 ms when drowsy; Schleicher et al. 2008: blink
duration and delayed reopening are the best blink signs. Each blink is timed on the eye
aperture, scaled between the closed and open EAR (enrolled values, or
`blink_closed_ref_ratio` x baseline / baseline when not enrolled), crossing times interpolated
between frames: its duration (aperture below `blink_open_level` and back) and its reopening
time (deepest point -> `blink_open_level`). Two signals over the PERCLOS window:
blink_time_frac (time spent in blinks / eye-known time) and reopen_ratio (median reopening
time / the driver's own median over the first `slow_blink_baseline_blinks` blinks of the
trip). Both ramp into slow_blink_score 0..1 (a term of drowsy_score). At 15-30 FPS a blink
has only a few frames: medians of several blinks only, thresholds to be tuned on data.
"""

from __future__ import annotations

from collections import deque

import numpy as np

from edge_agent.analysis.drowsiness.common import cross_time, ramp
from edge_agent.analysis.drowsiness.config import DrowsinessConfig


class SlowBlinks:
    def __init__(self, config: DrowsinessConfig) -> None:
        self.config = config
        self._aperture: deque[tuple[float, float]] = deque()  # (t, aperture) of recent EAR frames
        self._pending: tuple[float, float] | None = None  # (start, deepest t) of a blink still reopening
        self._log: deque[tuple[float, float, float]] = deque()  # (end, duration, reopen)
        self._reopen_base: list[float] = []

    def reset(self) -> None:
        """Start the timing references over (the aperture scale changed: driver enrollment)."""
        self._aperture.clear()
        self._pending = None
        self._log.clear()
        self._reopen_base = []

    def aperture_of(self, ear: float, baseline: float, ear_open: float | None, ear_closed: float | None) -> float:
        """EAR scaled to 0 (the driver's closed eyes) .. 1 (open-eye baseline). ear_open / ear_closed:
        the enrolled values, None when not enrolled."""
        if ear_closed is not None and ear_open is not None:
            closed = ear_closed
        else:
            closed = self.config.blink_closed_ref_ratio * baseline
        return (ear - closed) / max(baseline - closed, 1e-6)

    def update(self, t: float, aperture: float | None, blink_ended: bool, closing: bool) -> None:
        """Time each blink's duration and reopening on the aperture. closing: a closure episode is running."""
        cfg = self.config
        level = cfg.blink_open_level
        if aperture is None:
            self._aperture.clear()  # a gap (CNN, pose, no face): crossings cannot be timed across it
            if self._pending is not None and t - self._pending[1] > cfg.slow_blink_reopen_max_s:
                self._pending = None
            return
        prev = self._aperture[-1] if self._aperture else None
        self._aperture.append((t, aperture))
        while self._aperture and t - self._aperture[0][0] > cfg.blink_max_s + cfg.slow_blink_reopen_max_s:
            self._aperture.popleft()
        if blink_ended:
            self._pending = self._blink_start()
        if self._pending is None or prev is None:
            return
        start, deepest = self._pending
        if aperture >= level and prev[1] < level:
            end = cross_time(prev, (t, aperture), level)
            self._log.append((end, end - start, end - deepest))
            if len(self._reopen_base) < cfg.slow_blink_baseline_blinks:
                self._reopen_base.append(end - deepest)
            self._pending = None
        elif t - deepest > cfg.slow_blink_reopen_max_s or closing:
            self._pending = None  # never reopened fully, or closed again: not measured

    def _blink_start(self) -> tuple[float, float] | None:
        """(start, deepest point) of the blink that just reopened, from the recent apertures."""
        samples = list(self._aperture)
        if len(samples) < 2:
            return None
        k = min(range(len(samples)), key=lambda i: (samples[i][1], -samples[i][0]))  # deepest, latest
        level = self.config.blink_open_level
        for i in range(k, 0, -1):
            if samples[i - 1][1] >= level > samples[i][1]:
                return cross_time(samples[i - 1], samples[i], level), samples[k][0]
        return None  # the closing edge is not in the recent frames: not measured

    def stats(self, t: float, known_s: float) -> tuple[float, float | None, float | None]:
        """(blink_time_frac, median reopening time, reopen_ratio) over the PERCLOS window."""
        cfg = self.config
        while self._log and t - self._log[0][0] > cfg.perclos_window_s:
            self._log.popleft()
        frac = sum(d for _, d, _ in self._log) / known_s if known_s > 1e-9 else 0.0
        if len(self._log) < cfg.slow_blink_min_blinks:
            return min(frac, 1.0), None, None
        reopen = float(np.median([r for _, _, r in self._log]))
        ratio = None
        if len(self._reopen_base) >= cfg.slow_blink_min_blinks:
            ratio = reopen / max(float(np.median(self._reopen_base)), 1e-3)
        return min(frac, 1.0), reopen, ratio

    def score(self, coverage_s: float, blink_frac: float, reopen_ratio: float | None) -> float:
        """slow_blink_score 0..1; 0 until the PERCLOS window has `perclos_min_coverage_s` of eye data."""
        cfg = self.config
        if coverage_s < cfg.perclos_min_coverage_s:
            return 0.0
        return max(
            ramp(blink_frac, cfg.slow_blink_time_frac_low, cfg.slow_blink_time_frac_high),
            0.0
            if reopen_ratio is None
            else ramp(reopen_ratio, cfg.slow_blink_reopen_ratio_low, cfg.slow_blink_reopen_ratio_high),
        )

    def gap(self) -> None:
        """No frame for too long: a crossing cannot be timed across it, a blink under way is not measured."""
        self._aperture.clear()
        self._pending = None

    def forget_since(self, t0: float) -> None:
        while self._log and self._log[-1][0] >= t0:
            self._log.pop()
        self._aperture.clear()
        self._pending = None
