"""Block 7, brows: raised to keep drooping eyes open.

Vural et al. 2007: drowsy drivers raise the outer brows (FACS AU2) to keep the eyes open.
browOuterUp at least `brow_raise_above` over the driver's resting brow (enrolled, else the
rolling median) while the eyes droop but are not closed (EAR below `brow_narrow_ratio` x
baseline), for `brow_min_s`, not while yawning / talking (a yawn raises the brows too) -> a
"brow_raise" event, counted over `brow_window_s`.
"""

from __future__ import annotations

from collections import deque

from edge_agent.analysis.drowsiness.common import RollingWindow, drop_since, expire
from edge_agent.analysis.drowsiness.config import DrowsinessConfig
from edge_agent.perception.features import FrameFeatures


class BrowRaise:
    def __init__(self, config: DrowsinessConfig) -> None:
        self.config = config
        self._window = RollingWindow(config.brow_baseline_window_s, config.baseline_recompute_s)
        self._enrolled: float | None = None
        self._since: float | None = None
        self._fired = False
        self._last_t: float | None = None
        self._raises: deque[float] = deque()

    def set_enrolled(self, brow_neutral: float | None) -> None:
        self._enrolled = brow_neutral

    def update(
        self, t: float, f: FrameFeatures, eyes_open: bool, masked: bool, baseline: float, events: list[str]
    ) -> None:
        cfg = self.config
        if f.brow_up is None or not eyes_open or f.ear is None:
            if self._last_t is not None and t - self._last_t > cfg.max_gap_s:
                self._since, self._fired = None, False
            return
        self._last_t = t
        if not masked:
            self._window.add(t, f.brow_up)
        neutral = self._enrolled
        if neutral is None:
            if self._window.span < cfg.brow_baseline_min_data_s:
                return
            neutral = self._window.percentile(50, t)
        raising = (
            not masked and f.brow_up - neutral >= cfg.brow_raise_above and f.ear < cfg.brow_narrow_ratio * baseline
        )
        if not raising:
            self._since, self._fired = None, False
            return
        if self._since is None:
            self._since = t
        if not self._fired and t - self._since >= cfg.brow_min_s:
            self._fired = True
            self._raises.append(t)
            events.append("brow_raise")

    def gap(self) -> None:
        """No frame for too long: the raise under way starts again."""
        self._since, self._fired = None, False

    def count(self, t: float) -> int:
        expire(self._raises, t, self.config.brow_window_s)
        return len(self._raises)

    def forget_since(self, t0: float) -> None:
        drop_since(self._raises, t0)
        self._since = None
        self._window.drop_since(t0)
