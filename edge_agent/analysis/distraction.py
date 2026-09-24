"""Block 8 - Distraction branch.

Per frame, from head pose + phone flag + vehicle speed, computes:
- off_road_duration: seconds the head has been continuously turned away from the road.
- phone_ratio_2s: fraction of recent samples (window `phone_window_s`) with a phone
  in the driver zone.

Anti false-positive rules:
- The branch is disabled below `min_speed_kmh` (parked / red light: looking around
  or using the phone is fine). All state is reset.
- Head angles are compared to an adaptive "looking at the road" baseline, so a camera
  that is not mounted straight in front of the driver does not look like distraction.
  The baseline only learns from on-road samples, so looking away never shifts it.
- Returning to the road must last `on_road_confirm_s` before the off-road timer resets,
  so a quick glance back does not hide a long distraction; a single noisy frame
  cannot reset it either.
- Face lost: keep the previous state (turning far away often loses the face, while an
  occlusion when looking forward should not start the timer).

Pure logic on timestamps: no image, no clock, testable with fake sequences.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from typing import Any

from edge_agent.perception.features import FrameFeatures


@dataclass(frozen=True)
class DistractionConfig:
    min_speed_kmh: float = 5.0
    assume_moving_when_speed_unknown: bool = True
    yaw_off_road_deg: float = 30.0
    pitch_down_off_road_deg: float = 20.0
    pitch_up_off_road_deg: float = 25.0
    on_road_confirm_s: float = 0.3
    phone_window_s: float = 2.0
    baseline_adapt: bool = True
    baseline_tau_s: float = 30.0
    baseline_max_deg: float = 20.0
    baseline_yaw_deg: float = 0.0
    baseline_pitch_deg: float = 0.0

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> DistractionConfig:
        d = d or {}
        baseline = d.get("baseline") or {}
        flat = {k: v for k, v in d.items() if k != "baseline"}
        flat.update({f"baseline_{k}": v for k, v in baseline.items()})
        return cls(**{k: flat[k] for k in cls.__dataclass_fields__ if k in flat})


@dataclass(frozen=True)
class DistractionState:
    timestamp: float
    active: bool  # False when the vehicle is stopped
    off_road: bool
    off_road_duration: float
    phone_ratio_2s: float
    yaw_offset: float | None  # head angles relative to the baseline
    pitch_offset: float | None
    baseline_yaw: float
    baseline_pitch: float


class DistractionAnalyzer:
    def __init__(self, config: DistractionConfig | None = None) -> None:
        self.config = config or DistractionConfig()
        self.baseline_yaw = self.config.baseline_yaw_deg
        self.baseline_pitch = self.config.baseline_pitch_deg
        self.reset()

    def reset(self) -> None:
        """Clear timers and windows (baseline is kept: it describes the camera mount)."""
        self._off_road = False
        self._off_road_since: float | None = None
        self._on_road_since: float | None = None
        self._phone: deque[tuple[float, bool]] = deque()
        self._last_t: float | None = None

    def is_moving(self, speed_kmh: float | None) -> bool:
        if speed_kmh is None:
            return self.config.assume_moving_when_speed_unknown
        return speed_kmh >= self.config.min_speed_kmh

    def _head_off_road(self, yaw_off: float, pitch_off: float) -> bool:
        cfg = self.config
        return (
            abs(yaw_off) > cfg.yaw_off_road_deg
            or pitch_off > cfg.pitch_down_off_road_deg
            or pitch_off < -cfg.pitch_up_off_road_deg
        )

    def _adapt_baseline(self, yaw: float, pitch: float, dt: float) -> None:
        cfg = self.config
        if not cfg.baseline_adapt or dt <= 0 or cfg.baseline_tau_s <= 0:
            return
        alpha = 1.0 - math.exp(-dt / cfg.baseline_tau_s)
        lim = cfg.baseline_max_deg
        self.baseline_yaw = min(max(self.baseline_yaw + alpha * (yaw - self.baseline_yaw), -lim), lim)
        self.baseline_pitch = min(max(self.baseline_pitch + alpha * (pitch - self.baseline_pitch), -lim), lim)

    def _phone_ratio(self, t: float, phone_near_face: bool | None) -> float:
        if phone_near_face is not None:  # None = no fresh detector result: not counted
            self._phone.append((t, phone_near_face))
        while self._phone and t - self._phone[0][0] > self.config.phone_window_s:
            self._phone.popleft()
        if not self._phone:
            return 0.0
        return sum(1 for _, p in self._phone if p) / len(self._phone)

    def update(
        self,
        features: FrameFeatures,
        phone_near_face: bool | None,
        speed_kmh: float | None,
    ) -> DistractionState:
        t = features.timestamp
        dt = 0.0 if self._last_t is None else max(0.0, t - self._last_t)
        self._last_t = t

        if not self.is_moving(speed_kmh):
            self.reset()
            self._last_t = t
            return DistractionState(t, False, False, 0.0, 0.0, None, None, self.baseline_yaw, self.baseline_pitch)

        yaw_off = pitch_off = None
        has_pose = features.face_found and features.yaw is not None and features.pitch is not None
        if has_pose:
            yaw_off = features.yaw - self.baseline_yaw
            pitch_off = features.pitch - self.baseline_pitch
            head_off = self._head_off_road(yaw_off, pitch_off)
            if not head_off:
                self._adapt_baseline(features.yaw, features.pitch, dt)
        else:
            head_off = self._off_road  # face lost: hold previous state

        if head_off:
            self._on_road_since = None
            if not self._off_road:
                self._off_road = True
                self._off_road_since = t
        elif self._off_road:
            if self._on_road_since is None:
                self._on_road_since = t
            if t - self._on_road_since >= self.config.on_road_confirm_s:
                self._off_road = False
                self._off_road_since = None
                self._on_road_since = None

        duration = t - self._off_road_since if self._off_road and self._off_road_since is not None else 0.0
        return DistractionState(
            timestamp=t,
            active=True,
            off_road=self._off_road,
            off_road_duration=duration,
            phone_ratio_2s=self._phone_ratio(t, phone_near_face),
            yaw_offset=yaw_off,
            pitch_offset=pitch_off,
            baseline_yaw=self.baseline_yaw,
            baseline_pitch=self.baseline_pitch,
        )
