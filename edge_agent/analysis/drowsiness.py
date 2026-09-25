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
- A face partly out of frame (FrameFeatures.face_reliable False, block 6) is handled like
  a lost face: its EAR / MAR / pose feed neither PERCLOS, the eye baseline, yawns nor nods.
  Its pitch is only used to see a head drop (a driver slumping forward often slides out
  of frame), so the head-drop carry below still starts.
- Deep closure: closed_duration (microsleep event + L3 rule) only counts a closure whose
  eye frames are mostly "firmly shut": EAR <= `microsleep_deep_ear_ratio` x the open-eye
  baseline (or CNN p_closed >= `microsleep_deep_cnn`) on at least `microsleep_deep_min_frac`
  of them. Narrowed eyes (looking down, squinting in sunlight, smiling) sit around 0.55-0.75
  x baseline and stay inside the close / reopen hysteresis for seconds; a real closure drops
  well below. Once the closure is deep, its whole length counts (no added delay). Blinks
  keep the looser close_ratio.
- PERCLOS judges every frame on its own (EAR < `perclos_close_ratio` x the open-eye
  baseline, or CNN p_closed >= `eye_cnn_closed`), not with the close / reopen hysteresis:
  after a blink, the hysteresis keeps narrowed eyes (squinting in sunlight, 0.65-0.75 x
  baseline) "closed" until they open wide again, which reads as PERCLOS near 100 %.
  Hysteresis is for episodes (blinks, microsleep); PERCLOS is a time fraction.
- A yawn needs the mouth wide open for `yawn_min_s` (talking / laughing are shorter).
- A nod is a head dip relative to the driver's usual pitch that comes back within
  `nod_max_s` AND has the eyes closed for part of it (a glance at the speedometer
  keeps the eyes open).
- The usual head pose (rolling median of yaw / pitch) only learns from frames with the
  eyes open, like the EAR baseline, so frequent nods do not drag it down. The first
  `pose_baseline_min_data_s` of pose data are all taken, to get started.
- PERCLOS only raises "perclos_high" after `perclos_min_coverage_s` of eye data.
- Short face dropouts (< max_gap_s) do not break episodes; longer ones end them
  without counting a blink.
- Head drop: when the eyes were seen closed for `head_drop_carry_min_closed_s` and the
  head then drops past `eye_max_pitch_down_deg` (eyes can no longer be judged), the
  closure keeps counting while the head stays down or the face is lost, so falling
  asleep with a head drop still reaches the microsleep L3 rule. A blink followed by a
  glance down is shorter than the minimum and is not carried.
- Yawn mask: the eyes squeeze shut while yawning. While the mouth is wide open (MAR
  above `yawn_mar_open`, until it drops below `yawn_mar_close`) and for
  `microsleep_mask_hold_s` after, closed-eye time is not counted in closed_duration, so
  a yawn does not reach the microsleep rules. The mask stops after the mouth has been
  open `microsleep_mask_max_open_s` (a slack jaw in sleep is not a yawn). Talking masks
  the same way: the eyes narrow and close for short spells while the mouth keeps moving
  (at least `microsleep_mask_talk_min_swings` MAR reversals of `microsleep_mask_talk_swing`
  within `microsleep_mask_talk_window_s`). A still mouth has none, and a single jump (a
  yawn ending, the jaw dropping in sleep) makes at most two.
  With `perclos_use_mask`, PERCLOS skips the masked frames too (eye state treated as
  unknown there): squinting while talking / yawning is not eye closure from fatigue.
  Yawns are counted by their own rule.
- After a rest (the vehicle parked, block 10), `forget_since` drops what was gathered
  since the vehicle stopped: eyes closed to rest and waking-up yawns say nothing about the
  next drive. Events from before the stop stay.

Pure logic on timestamps: no image, no clock, testable with fake sequences.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any

import numpy as np

from edge_agent.config import config_from_dict
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
    # Keep counting a closure through a head drop (eyes closed at least this long before it)
    head_drop_carry_min_closed_s: float = 0.5
    # Closure episodes
    blink_max_s: float = 0.5
    blink_window_s: float = 60.0
    blink_rate_min_span_s: float = 10.0  # blink rate divides by at least this (first seconds of a trip)
    microsleep_min_s: float = 1.0
    # Only a deep closure counts toward closed_duration (see module doc)
    microsleep_deep_ear_ratio: float = 0.5
    microsleep_deep_cnn: float = 0.8
    microsleep_deep_min_frac: float = 0.5
    # Closed-eye time does not count toward microsleep while yawning (see module doc)
    microsleep_mask_hold_s: float = 1.5
    microsleep_mask_max_open_s: float = 8.0
    microsleep_mask_talk_window_s: float = 2.0
    microsleep_mask_talk_swing: float = 0.08
    microsleep_mask_talk_min_swings: int = 3  # 0 = no talking mask
    # PERCLOS
    perclos_window_s: float = 60.0
    perclos_min_coverage_s: float = 30.0
    perclos_drowsy: float = 0.15
    perclos_rearm: float = 0.12
    perclos_use_mask: bool = True  # skip yawn / talking-masked frames (see module doc)
    perclos_close_ratio: float = 0.65  # per-frame closed test for PERCLOS (see module doc)
    # Yawn
    yawn_mar_open: float = 0.45
    yawn_mar_close: float = 0.34
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
    pose_baseline_min_data_s: float = 5.0

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> DrowsinessConfig:
        return config_from_dict(cls, d, "drowsiness")


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
    head_drop: bool = False  # closure carried through a head drop (eye state unknown)
    pitch_baseline: float | None = None  # the driver's usual pitch (eyes-open median)
    closure_masked: bool = False  # yawn mask: closed-eye time is not counted on this frame
    perclos_ready: bool = False  # perclos_coverage_s >= perclos_min_coverage_s: PERCLOS is meaningful


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
        self._closed_since: float | None = None  # start of the closure episode (blinks)
        self._count_since: float | None = None  # start of the counted part (closed_duration)
        self._microsleep_fired = False
        self._head_drop = False
        self._deep_frames = 0  # eye frames of the counted closure that are firmly shut
        self._eye_frames = 0
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
        # microsleep mask
        self._mask_open_since: float | None = None
        self._mask_until = float("-inf")
        self._talk_ext: float | None = None  # MAR extreme of the current mouth movement
        self._talk_rising = True
        self._talk_swings: deque[float] = deque()
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

    def forget_since(self, t0: float) -> None:
        """Drop what was gathered from t0 on (the vehicle stopped for a rest, block 10): the
        closure episode, PERCLOS samples, blinks, yawns, nods and baseline samples."""
        self._end_closure()
        while self._perclos and self._perclos[-1][0] >= t0:
            _, dt, closed = self._perclos.pop()
            self._perclos_known -= dt
            self._perclos_closed -= dt if closed else 0.0
        self._perclos_armed = True
        for events in (self._blinks, self._yawns, self._nods):
            while events and events[-1] >= t0:
                events.pop()
        for window in (self._ear, self._yaw, self._pitch):
            window.drop_since(t0)
        if self._dip_start is not None and self._dip_start >= t0:
            self._dip_start = None

    # ------------------------------------------------------------------ main update
    def update(self, f: FrameFeatures) -> DrowsinessState:
        cfg = self.config
        t = f.timestamp
        if self._start_t is None:
            self._start_t = t
        dt = 0.0 if self._last_t is None else min(max(0.0, t - self._last_t), cfg.max_gap_s)
        self._last_t = t
        events: list[str] = []
        face_ok = f.face_found and f.face_reliable  # partial face: landmarks are extrapolated
        mar = f.mar if face_ok else None

        # Raw eye reading, before pose is known. Block 5 (eye-state CNN) decides when it ran:
        # EAR was judged unreliable on this frame.
        use_cnn = face_ok and f.p_closed is not None
        baseline = self.ear_baseline(t)
        close_thr = baseline * cfg.eye_close_ratio
        open_thr = baseline * cfg.eye_open_ratio
        if use_cnn:
            ear_low = f.p_closed >= cfg.eye_cnn_closed  # raw, ignores pose (used by nod)
        else:
            ear_low = None if f.ear is None or not face_ok else f.ear < close_thr

        # Head pose relative to the driver's usual pose (rolling median of eyes-open frames).
        yaw_off = pitch_off = None
        pitch_ref = None
        if face_ok and f.yaw is not None and f.pitch is not None:
            if ear_low is False or self._pitch.span < cfg.pose_baseline_min_data_s:
                self._yaw.add(t, f.yaw)
                self._pitch.add(t, f.pitch)
            yaw_ref, pitch_ref = self._yaw.percentile(50, t), self._pitch.percentile(50, t)
            if yaw_ref is not None and pitch_ref is not None:
                yaw_off, pitch_off = f.yaw - yaw_ref, f.pitch - pitch_ref
            self._last_pose_t = t
        elif self._pitch.span > 0:
            pitch_ref = self._pitch.percentile(50, t)

        # Eye state with a per-driver threshold.
        pose_ok = (
            yaw_off is not None and abs(yaw_off) <= cfg.eye_max_yaw_deg and pitch_off <= cfg.eye_max_pitch_down_deg
        )
        eye_known = face_ok and pose_ok and (use_cnn or f.ear is not None)
        if eye_known and f.ear is not None and (not use_cnn or f.p_closed <= cfg.eye_cnn_open):
            self._ear.add(t, f.ear)  # an unreliable EAR must not become the driver's "open eye" value

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

        if pitch_off is None and f.face_found and f.pitch is not None and pitch_ref is not None:
            head_off = f.pitch - pitch_ref  # partial face: good enough to see a head drop
        else:
            head_off = pitch_off
        head_down = head_off is not None and head_off > cfg.eye_max_pitch_down_deg
        self._update_closure(t, eye_closed, head_down, pitch_off is None, events)
        masked = self._update_mask(t, mar)
        if masked and self._closed_since is not None and not self._head_drop:
            # Yawning / talking: restart the counted part of the closure. Not once the head
            # has dropped (a head drop is not a yawn), or falling asleep right after a yawn
            # would never reach the microsleep rules.
            self._count_since = t
            self._deep_frames = self._eye_frames = 0
        if eye_closed and self._count_since is not None:
            self._eye_frames += 1
            if use_cnn:
                self._deep_frames += f.p_closed >= cfg.microsleep_deep_cnn
            else:
                self._deep_frames += f.ear <= baseline * cfg.microsleep_deep_ear_ratio
        deep = self._eye_frames > 0 and self._deep_frames >= cfg.microsleep_deep_min_frac * self._eye_frames
        closed_duration = t - self._count_since if self._count_since is not None and deep else 0.0
        if closed_duration >= cfg.microsleep_min_s and not self._microsleep_fired:
            self._microsleep_fired = True
            events.append("microsleep")

        # Per frame, not the hysteresis state: narrowed eyes after a blink are not closed.
        perclos_eye: bool | None = None
        if eye_known and not (masked and cfg.perclos_use_mask):
            if use_cnn:
                perclos_eye = f.p_closed >= cfg.eye_cnn_closed
            else:
                perclos_eye = f.ear < baseline * cfg.perclos_close_ratio
        perclos, coverage = self._update_perclos(t, dt, perclos_eye, events)
        blink_rate = self._blink_rate(t)
        yawning = self._update_yawn(t, mar, events)
        self._update_nod(t, dt, pitch_off, ear_low, events)

        self._expire(self._yawns, t, cfg.yawn_window_s)
        self._expire(self._nods, t, cfg.nod_window_s)
        return DrowsinessState(
            timestamp=t,
            eye_closed=eye_closed,
            eye_source=None if eye_closed is None else ("cnn" if use_cnn else "ear"),
            head_drop=self._head_drop,
            pitch_baseline=pitch_ref,
            closure_masked=masked,
            closed_duration=closed_duration,
            microsleep=closed_duration >= cfg.microsleep_min_s,
            perclos_60s=perclos,
            perclos_coverage_s=coverage,
            perclos_ready=coverage >= cfg.perclos_min_coverage_s,
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
        self._count_since = None
        self._microsleep_fired = False
        self._head_drop = False
        self._deep_frames = self._eye_frames = 0

    def _update_closure(
        self, t: float, eye_closed: bool | None, head_down: bool, face_lost: bool, events: list[str]
    ) -> None:
        cfg = self.config
        if eye_closed is None:
            if self._closed_since is None or self._last_eye_t is None:
                return
            if self._head_drop:
                # Carried closure: goes on while the head stays down or the face is lost.
                if not (head_down or face_lost):
                    self._end_closure()
                return
            # From the start of the closure, not of its counted part: eyes shut during a
            # yawn / talking still qualify for the carry when the head drops.
            closed_before = self._last_eye_t - self._closed_since
            if (
                head_down
                and t - self._last_eye_t <= cfg.max_gap_s
                and closed_before >= cfg.head_drop_carry_min_closed_s
            ):
                self._head_drop = True  # eyes closed, then the head dropped: keep counting
                return
            # Unknown: keep a running episode through short dropouts only.
            if t - self._last_eye_t > cfg.max_gap_s:
                self._end_closure()
            return
        self._last_eye_t = t
        self._head_drop = False
        if eye_closed:
            if self._closed_since is None:
                self._closed_since = self._count_since = t
        elif self._closed_since is not None:
            if t - self._closed_since <= cfg.blink_max_s:
                self._blinks.append(t)
                events.append("blink")
            self._end_closure()

    def _update_mask(self, t: float, mar: float | None) -> bool:
        """True while closed-eye time must not count toward microsleep (yawning or talking)."""
        cfg = self.config
        if mar is not None:
            if self._mask_open_since is None:
                if mar > cfg.yawn_mar_open:
                    self._mask_open_since = t
            elif mar < cfg.yawn_mar_close:
                self._mask_open_since = None
            talking = self._talking(t, mar)  # always called: keeps the MAR window filled
            yawning = self._mask_open_since is not None and t - self._mask_open_since <= cfg.microsleep_mask_max_open_s
            if yawning or talking:
                self._mask_until = t + cfg.microsleep_mask_hold_s
        return t <= self._mask_until

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
        self._expire(self._talk_swings, t, cfg.microsleep_mask_talk_window_s)
        return cfg.microsleep_mask_talk_min_swings > 0 and len(self._talk_swings) >= cfg.microsleep_mask_talk_min_swings

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
        return len(self._blinks) / max(observed, cfg.blink_rate_min_span_s) * 60.0

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
