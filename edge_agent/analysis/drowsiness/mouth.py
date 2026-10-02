"""Block 7, mouth: yawns, and the yawn / talking mask on closed-eye time.

- A yawn needs the mouth wide open for `yawn_min_s` (talking / laughing are shorter).
- Yawn mask: the eyes squeeze shut while yawning. While the mouth is wide open (MAR
  above `yawn_mar_open`, until it drops below `yawn_mar_close`) and for
  `microsleep_mask_hold_s` after, closed-eye time is not counted in closed_duration, so
  a yawn does not reach the microsleep rules. The mask stops after the mouth has been
  open `microsleep_mask_max_open_s` (a slack jaw in sleep is not a yawn). Talking masks
  the same way: the eyes narrow and close for short spells while the mouth keeps moving
  (at least `microsleep_mask_talk_min_swings` MAR reversals of `microsleep_mask_talk_swing`
  within `microsleep_mask_talk_window_s`). A still mouth has none, and a single jump (a
  yawn ending, the jaw dropping in sleep) makes at most two.
  With `microsleep_mask_talk_spares_deep`, talking (not yawning) no longer restarts a closure
  on its deep frames (EAR firmly shut and the eyeBlink blendshape >= `microsleep_deep_blink`;
  without blendshapes the mask works as before): people
  squint while they talk, they do not keep the eyes firmly shut; small lip movements of a
  sleepy driver made the talking mask hide real microsleeps (NITYMED).
  With `perclos_use_mask`, PERCLOS skips the masked frames too (eye state treated as
  unknown there): squinting while talking / yawning is not eye closure from fatigue.
  Yawns are counted by their own rule.
- Driver enrollment: the yawn thresholds (mar_open / mar_close, given on every update)
  become the enrolled closed-mouth MAR + `yawn_enrolled_open_above` / `_close_above` (lips
  that rest apart are not a yawn, a small mouth still reaches it).
"""

from __future__ import annotations

from collections import deque

from edge_agent.analysis.drowsiness.common import drop_since, expire
from edge_agent.analysis.drowsiness.config import DrowsinessConfig


class MouthMask:
    """True while closed-eye time must not count toward microsleep (yawning or talking)."""

    def __init__(self, config: DrowsinessConfig) -> None:
        self.config = config
        self._open_since: float | None = None
        self._until = float("-inf")
        self._yawn_until = float("-inf")  # the yawn part of the mask (talking is the rest)
        self._talk_ext: float | None = None  # MAR extreme of the current mouth movement
        self._talk_rising = True
        self._talk_swings: deque[float] = deque()

    def update(self, t: float, mar: float | None, mar_open: float, mar_close: float) -> bool:
        cfg = self.config
        if mar is not None:
            if self._open_since is None:
                if mar > mar_open:
                    self._open_since = t
            elif mar < mar_close:
                self._open_since = None
            talking = self._talking(t, mar)  # always called: keeps the MAR window filled
            yawning = self._open_since is not None and t - self._open_since <= cfg.microsleep_mask_max_open_s
            if yawning or talking:
                self._until = t + cfg.microsleep_mask_hold_s
            if yawning:
                self._yawn_until = t + cfg.microsleep_mask_hold_s
        return t <= self._until

    def talk_only(self, t: float) -> bool:
        """The mask holds for talking, not for a yawn (call when masked)."""
        return t > self._yawn_until

    def _talking(self, t: float, mar: float) -> bool:
        """Mouth keeps opening and closing: enough MAR reversals (zigzag) in the talk window."""
        cfg = self.config
        if self._talk_ext is None:
            self._talk_ext = mar
        elif self._talk_rising:
            if mar > self._talk_ext:
                self._talk_ext = mar
            elif self._talk_ext - mar >= cfg.microsleep_mask_talk_swing:
                self._talk_rising, self._talk_ext = False, mar
                self._talk_swings.append(t)
        elif mar < self._talk_ext:
            self._talk_ext = mar
        elif mar - self._talk_ext >= cfg.microsleep_mask_talk_swing:
            self._talk_rising, self._talk_ext = True, mar
            self._talk_swings.append(t)
        expire(self._talk_swings, t, cfg.microsleep_mask_talk_window_s)
        return cfg.microsleep_mask_talk_min_swings > 0 and len(self._talk_swings) >= cfg.microsleep_mask_talk_min_swings


class YawnCounter:
    """Mouth wide open for `yawn_min_s` -> a "yawn" event, counted over `yawn_window_s`."""

    def __init__(self, config: DrowsinessConfig) -> None:
        self.config = config
        self._open_since: float | None = None
        self._last_mar_t: float | None = None
        self._fired = False
        self._yawns: deque[float] = deque()

    def update(self, t: float, mar: float | None, mar_open: float, mar_close: float, events: list[str]) -> bool:
        """True while the current yawn has been counted (the mouth is still open)."""
        cfg = self.config
        if mar is None:
            if self._open_since is not None and self._last_mar_t is not None and t - self._last_mar_t > cfg.max_gap_s:
                self._open_since = None
                self._fired = False
            return self._fired
        self._last_mar_t = t
        if self._open_since is None:
            if mar > mar_open:
                self._open_since = t
        elif mar < mar_close:
            self._open_since = None
            self._fired = False
        if self._open_since is not None and not self._fired and t - self._open_since >= cfg.yawn_min_s:
            self._fired = True
            self._yawns.append(t)
            events.append("yawn")
        return self._fired

    def count(self, t: float) -> int:
        expire(self._yawns, t, self.config.yawn_window_s)
        return len(self._yawns)

    def forget_since(self, t0: float) -> None:
        drop_since(self._yawns, t0)
