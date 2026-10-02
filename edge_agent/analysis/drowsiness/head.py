"""Block 7, head: the driver's usual head pose and head nods.

- Eye state is not judged when the head is turned far or tilted down (EAR collapses
  in those poses): no PERCLOS accumulation from looking at the dashboard. The offsets
  for that test come from here.
- The usual head pose (rolling median of yaw / pitch) only learns from frames with the
  eyes open, like the EAR baseline, so frequent nods do not drag it down. The first
  `pose_baseline_min_data_s` of pose data are all taken, to get started. After driver
  enrollment it starts at the enrolled road pose and only learns from eyes-open frames.
- A nod is a head dip relative to the driver's usual pitch that is back within `nod_max_s`
  (longer = sustained head down), drops within `nod_max_drop_s`, comes back up fast (see "Nod
  vs bow" below) AND has the eyes closed for part of it (a glance at the speedometer keeps
  the eyes open).
- Nod vs bow: a drowsy nod drops slowly (neck muscles letting go) and comes back up with a jerk
  (waking up); a deliberate bow (dashboard, phone, picking something up) moves both ways at a
  controlled speed. A dip counts as a nod only when its rise is at least `nod_rise_speed_ratio`
  x faster than its drop and at least `nod_min_rise_deg_s`, with the eyes closed for part of
  it; other dips are "bow" events (not drowsiness). Pitch is relative to the driver's usual pose
  (the enrolled road pose after enrollment).
"""

from __future__ import annotations

from collections import deque

from edge_agent.analysis.drowsiness.common import RollingWindow, drop_since, expire
from edge_agent.analysis.drowsiness.config import DrowsinessConfig
from edge_agent.perception.features import FrameFeatures


class HeadPose:
    """Yaw / pitch relative to the driver's usual pose (eyes-open rolling median, or enrolled)."""

    def __init__(self, config: DrowsinessConfig) -> None:
        self.config = config
        self._yaw = RollingWindow(config.pose_baseline_window_s)
        self._pitch = RollingWindow(config.pose_baseline_window_s)
        self._enrolled: tuple[float, float] | None = None  # (yaw, pitch)
        self.last_t: float | None = None  # last frame with a usable pose

    def set_enrolled(self, road_yaw: float, road_pitch: float) -> None:
        self._enrolled = (road_yaw, road_pitch)

    def _enrolled_pose(self) -> tuple[float, float] | None:
        """The enrolled (yaw, pitch) while there is not enough eyes-open pose data yet, else None."""
        if self._enrolled is not None and self._pitch.span < self.config.pose_baseline_min_data_s:
            return self._enrolled
        return None

    def update(
        self, t: float, f: FrameFeatures, face_ok: bool, ear_low: bool | None
    ) -> tuple[float | None, float | None, float | None]:
        """(yaw offset, pitch offset, usual pitch); offsets None without a usable pose."""
        cfg = self.config
        yaw_off = pitch_off = None
        pitch_ref = None
        if face_ok and f.yaw is not None and f.pitch is not None:
            starting = self._pitch.span < cfg.pose_baseline_min_data_s and self._enrolled is None
            if ear_low is False or starting:
                self._yaw.add(t, f.yaw)
                self._pitch.add(t, f.pitch)
            enrolled = self._enrolled_pose()
            if enrolled is not None:
                yaw_ref, pitch_ref = enrolled
            else:
                yaw_ref, pitch_ref = self._yaw.percentile(50, t), self._pitch.percentile(50, t)
            if yaw_ref is not None and pitch_ref is not None:
                yaw_off, pitch_off = f.yaw - yaw_ref, f.pitch - pitch_ref
            self.last_t = t
        elif self._enrolled_pose() is not None:
            pitch_ref = self._enrolled[1]
        elif self._pitch.span > 0:
            pitch_ref = self._pitch.percentile(50, t)  # pitch only: the yaw cache keeps its own timing
        return yaw_off, pitch_off, pitch_ref

    def drop_since(self, t0: float) -> None:
        self._yaw.drop_since(t0)
        self._pitch.drop_since(t0)


class NodDetector:
    """Head dips: "nod" (drowsy: slow drop, jerk up, eyes closed) or "bow" (a deliberate look down)."""

    def __init__(self, config: DrowsinessConfig) -> None:
        self.config = config
        self._dip_start: float | None = None
        self._dip_known = 0.0
        self._dip_closed = 0.0
        self._nods: deque[float] = deque()
        self._level_t: float | None = None  # last time the pitch was back near the usual pose
        self._dip_track: list[tuple[float, float]] = []  # (t, pitch offset) of the current dip

    def update(
        self,
        t: float,
        dt: float,
        pitch_off: float | None,
        ear_low: bool | None,
        last_pose_t: float | None,
        events: list[str],
    ) -> None:
        cfg = self.config
        if pitch_off is None:
            if self._dip_start is not None and last_pose_t is not None and t - last_pose_t > cfg.max_gap_s:
                self._dip_start = None  # face lost too long: drop the dip rather than guess
            return
        if self._dip_start is None:
            if pitch_off < cfg.nod_return_deg:
                self._level_t = t
            elif pitch_off > cfg.nod_pitch_down_deg:
                self._dip_start, self._dip_known, self._dip_closed = t, 0.0, 0.0
                self._dip_track = [(t, pitch_off)]
            return
        self._dip_track.append((t, pitch_off))
        if ear_low is not None:
            self._dip_known += dt
            self._dip_closed += dt if ear_low else 0.0
        if pitch_off < cfg.nod_return_deg:
            # Drop: leaving the usual pose -> first reaching the bottom; rise: last at the bottom ->
            # back. "Bottom" = within 15 % of the dip depth, so holding the head down does not count.
            left = self._level_t if self._level_t is not None else self._dip_start
            peak = max(p for _, p in self._dip_track)
            bottom = peak - 0.15 * (peak - cfg.nod_return_deg)
            at_bottom = [tt for tt, p in self._dip_track if p >= bottom]
            drop_s = max(at_bottom[0] - left, 1e-3)
            rise_s = max(t - at_bottom[-1], 1e-3)
            depth = peak - cfg.nod_return_deg
            down_speed, up_speed = depth / drop_s, depth / rise_s
            closed_frac = self._dip_closed / self._dip_known if self._dip_known > 0 else 0.0
            eyes_ok = not cfg.nod_require_eyes_closed or closed_frac >= cfg.nod_eyes_closed_min_frac
            jerk_up = up_speed >= cfg.nod_min_rise_deg_s and (
                cfg.nod_rise_speed_ratio <= 0 or up_speed >= cfg.nod_rise_speed_ratio * down_speed
            )
            timing = (
                cfg.nod_min_s <= t - self._dip_start <= cfg.nod_max_s
                and (cfg.nod_max_drop_s <= 0 or drop_s <= cfg.nod_max_drop_s)
                and (cfg.nod_max_rise_s <= 0 or rise_s <= cfg.nod_max_rise_s)
            )
            if timing and jerk_up and eyes_ok:
                self._nods.append(t)
                events.append("nod")
            else:
                events.append("bow")  # a deliberate look down, not drowsiness
            self._dip_start = None
            self._dip_track = []
            self._level_t = t

    def count(self, t: float) -> int:
        expire(self._nods, t, self.config.nod_window_s)
        return len(self._nods)

    def forget_since(self, t0: float) -> None:
        drop_since(self._nods, t0)
        if self._dip_start is not None and self._dip_start >= t0:
            self._dip_start = None
