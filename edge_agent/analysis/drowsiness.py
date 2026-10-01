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
  keep the looser close_ratio. With `microsleep_deep_blink` > 0, an EAR frame is deep only
  when MediaPipe's eyeBlink blendshape (block 3, pretrained, no per-driver baseline) agrees
  it is at least that shut: EAR alone also collapses for glare on glasses, a head tilted
  down and eyes that are narrow before the driver's own baseline is learnt.
- PERCLOS judges every frame on its own (EAR < `perclos_close_ratio` x the open-eye
  baseline, or CNN p_closed >= `eye_cnn_closed`), not with the close / reopen hysteresis:
  after a blink, the hysteresis keeps narrowed eyes (squinting in sunlight, 0.65-0.75 x
  baseline) "closed" until they open wide again, which reads as PERCLOS near 100 %.
  Hysteresis is for episodes (blinks, microsleep); PERCLOS is a time fraction.
- A yawn needs the mouth wide open for `yawn_min_s` (talking / laughing are shorter).
- A nod is a head dip relative to the driver's usual pitch that is back within `nod_max_s`
  (longer = sustained head down), drops within `nod_max_drop_s`, comes back up fast (see "Nod vs bow" below) AND has the eyes closed
  for part of it (a glance at the speedometer keeps the eyes open).
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
  With `microsleep_mask_talk_spares_deep`, talking (not yawning) no longer restarts a closure
  on its deep frames (EAR firmly shut and the eyeBlink blendshape >= `microsleep_deep_blink`;
  without blendshapes the mask works as before): people
  squint while they talk, they do not keep the eyes firmly shut; small lip movements of a
  sleepy driver made the talking mask hide real microsleeps (NITYMED).
  With `perclos_use_mask`, PERCLOS skips the masked frames too (eye state treated as
  unknown there): squinting while talking / yawning is not eye closure from fatigue.
  Yawns are counted by their own rule.
- Driver enrollment (block 6 stage, `set_profile`): the open-eye baseline starts at the
  driver's enrolled EAR and only drifts within `eye_enrolled_max_drop` below /
  `eye_enrolled_max_rise` above it: eyes narrowing over tens of minutes of drowsiness no
  longer drag the baseline down and hide PERCLOS / deep closures. Yawn thresholds become the
  enrolled closed-mouth MAR + `yawn_enrolled_open_above` / `_close_above` (lips that rest
  apart are not a yawn, a small mouth still reaches it). The head-pose reference starts at
  the enrolled road pose and only learns from eyes-open frames. Without enrollment
  (skipped, evaluation clips) everything is self-learnt as before.
- Slow blinks (Caffier et al. 2003: eyelid reopening 162 -> 273 ms when drowsy; Schleicher et
  al. 2008: blink duration and delayed reopening are the best blink signs). Each blink is timed
  on the eye aperture, scaled between the closed and open EAR (enrolled values, or
  `blink_closed_ref_ratio` x baseline / baseline when not enrolled), crossing times interpolated
  between frames: its duration (aperture below `blink_open_level` and back) and its reopening
  time (deepest point -> `blink_open_level`). Two signals over the PERCLOS window:
  blink_time_frac (time spent in blinks / eye-known time) and reopen_ratio (median reopening
  time / the driver's own median over the first `slow_blink_baseline_blinks` blinks of the
  trip). Both ramp into slow_blink_score 0..1 (a term of drowsy_score). At 15-30 FPS a blink
  has only a few frames: medians of several blinks only, thresholds to be tuned on data.
- Nod vs bow: a drowsy nod drops slowly (neck muscles letting go) and comes back up with a jerk
  (waking up); a deliberate bow (dashboard, phone, picking something up) moves both ways at a
  controlled speed. A dip counts as a nod only when its rise is at least `nod_rise_speed_ratio`
  x faster than its drop and at least `nod_min_rise_deg_s`, with the eyes closed for part of
  it; other dips are "bow" events (not drowsiness). Pitch is relative to the driver's usual pose
  (the enrolled road pose after enrollment).
- Brow raise (Vural et al. 2007: drowsy drivers raise the outer brows, FACS AU2, to keep the
  eyes open): browOuterUp at least `brow_raise_above` over the driver's resting brow (enrolled,
  else the rolling median) while the eyes droop but are not closed (EAR below
  `brow_narrow_ratio` x baseline), for `brow_min_s`, not while yawning / talking (a yawn raises
  the brows too) -> a "brow_raise" event, counted over `brow_window_s`.
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
    eye_enrolled_max_drop: float = 0.10  # enrolled baseline drifts at most this fraction down
    eye_enrolled_max_rise: float = 0.25  # ... and this fraction up
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
    microsleep_deep_blink: float = 0.5  # EAR deep frames also need eyeBlink >= this when known (0 = off)
    # Closed-eye time does not count toward microsleep while yawning (see module doc)
    microsleep_mask_hold_s: float = 1.5
    microsleep_mask_max_open_s: float = 8.0
    microsleep_mask_talk_window_s: float = 2.0
    microsleep_mask_talk_swing: float = 0.08
    microsleep_mask_talk_min_swings: int = 3  # 0 = no talking mask
    microsleep_mask_talk_spares_deep: bool = True  # talking does not restart a deep closure (see module doc)
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
    yawn_enrolled_open_above: float = 0.40  # enrolled: mar_open = closed-mouth MAR + this
    yawn_enrolled_close_above: float = 0.29  # enrolled: mar_close = closed-mouth MAR + this
    # Slow blinks (see module doc)
    blink_closed_ref_ratio: float = 0.35  # not enrolled: closed-eye EAR ~ this x open-eye baseline
    blink_open_level: float = 0.8  # aperture (0 closed .. 1 open) where a blink starts / ends
    slow_blink_reopen_max_s: float = 1.0  # a reopening not finished in this long is not measured
    slow_blink_min_blinks: int = 5  # measured blinks in the window before reopen_ratio counts
    slow_blink_baseline_blinks: int = 20  # first blinks of the trip = the driver's own reopening time
    slow_blink_time_frac_low: float = 0.10  # blink_time_frac term ramps 0 -> 1 between low and high
    slow_blink_time_frac_high: float = 0.16
    slow_blink_reopen_ratio_low: float = 1.3  # reopen_ratio term ramps 0 -> 1 between low and high
    slow_blink_reopen_ratio_high: float = 1.7
    # Nod
    nod_pitch_down_deg: float = 15.0
    nod_return_deg: float = 7.0
    nod_min_s: float = 0.2
    nod_max_s: float = 2.0  # past nod_pitch_down_deg -> back (as v1): longer = sustained head down
    nod_max_drop_s: float = 0.0  # leaving the usual pose -> the bottom (0 = no limit)
    nod_max_rise_s: float = 0.0  # leaving the bottom -> back (0 = no limit)
    nod_rise_speed_ratio: float = 0.0  # rise at least this x faster than the drop (0 = off, see yaml)
    nod_min_rise_deg_s: float = 0.0  # 0 = off
    nod_require_eyes_closed: bool = True
    nod_eyes_closed_min_frac: float = 0.3
    nod_window_s: float = 300.0
    # Brow raise to keep the eyes open (see module doc)
    brow_raise_above: float = 0.2  # browOuterUp above the resting brow
    brow_narrow_ratio: float = 0.85  # ... while EAR < this x open-eye baseline (eyes drooping)
    brow_min_s: float = 0.5
    brow_window_s: float = 300.0
    brow_baseline_window_s: float = 120.0  # not enrolled: resting brow = rolling median
    brow_baseline_min_data_s: float = 10.0
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
    blink_time_frac: float = 0.0  # time spent in blinks / eye-known time, PERCLOS window
    reopen_s: float | None = None  # median eyelid reopening time of the window's blinks
    reopen_ratio: float | None = None  # reopen_s / the driver's own early-trip median
    slow_blink_score: float = 0.0  # 0..1, a drowsy_score term (needs PERCLOS coverage)
    brow_raise_count_5min: int = 0


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
        # Driver enrollment (set_profile): None = self-learnt
        self._ear_enrolled: float | None = None
        self._pose_enrolled: tuple[float, float] | None = None  # (yaw, pitch)
        self._mar_open, self._mar_close = cfg.yawn_mar_open, cfg.yawn_mar_close
        self._ear_closed_enrolled: float | None = None
        self._brow_enrolled: float | None = None
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
        self._yawn_mask_until = float("-inf")  # the yawn part of the mask (talking is the rest)
        self._talk_ext: float | None = None  # MAR extreme of the current mouth movement
        self._talk_rising = True
        self._talk_swings: deque[float] = deque()
        # nod
        self._dip_start: float | None = None
        self._dip_known = 0.0
        self._dip_closed = 0.0
        self._last_pose_t: float | None = None
        self._nods: deque[float] = deque()
        self._level_t: float | None = None  # last time the pitch was back near the usual pose
        self._dip_track: list[tuple[float, float]] = []  # (t, pitch offset) of the current dip
        # slow blinks
        self._aperture: deque[tuple[float, float]] = deque()  # (t, aperture) of recent EAR frames
        self._pending: tuple[float, float] | None = None  # (start, deepest t) of a blink still reopening
        self._blink_log: deque[tuple[float, float, float]] = deque()  # (end, duration, reopen)
        self._reopen_base: list[float] = []
        # brow raise
        self._brow = RollingWindow(cfg.brow_baseline_window_s)
        self._brow_since: float | None = None
        self._brow_fired = False
        self._brow_last_t: float | None = None
        self._brow_raises: deque[float] = deque()

    # ------------------------------------------------------------------ helpers
    def set_profile(
        self,
        ear_open: float,
        mar_closed: float,
        road_yaw: float,
        road_pitch: float,
        ear_closed: float | None = None,
        brow_neutral: float | None = None,
    ) -> None:
        """Use the driver's enrolled reference values from now on (see module doc)."""
        cfg = self.config
        self._ear_enrolled = ear_open
        self._ear_closed_enrolled = ear_closed
        self._brow_enrolled = brow_neutral
        # blink timing changes scale (aperture between the enrolled EARs): start its references over
        self._aperture.clear()
        self._pending = None
        self._blink_log.clear()
        self._reopen_base = []
        self._pose_enrolled = (road_yaw, road_pitch)
        self._mar_open = mar_closed + cfg.yawn_enrolled_open_above
        self._mar_close = mar_closed + cfg.yawn_enrolled_close_above

    def ear_baseline(self, t: float) -> float:
        cfg = self.config
        enrolled = self._ear_enrolled
        if self._ear.span < cfg.eye_baseline_min_data_s:
            value = cfg.eye_baseline_init if enrolled is None else enrolled
        else:
            value = self._ear.percentile(cfg.eye_baseline_percentile, t)
        if enrolled is not None:
            value = min(
                max(value, enrolled * (1.0 - cfg.eye_enrolled_max_drop)), enrolled * (1.0 + cfg.eye_enrolled_max_rise)
            )
        return min(max(value, cfg.eye_baseline_min), cfg.eye_baseline_max)

    def _enrolled_pose(self) -> tuple[float, float] | None:
        """The enrolled (yaw, pitch) while there is not enough eyes-open pose data yet, else None."""
        if self._pose_enrolled is not None and self._pitch.span < self.config.pose_baseline_min_data_s:
            return self._pose_enrolled
        return None

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
        for events in (self._blinks, self._yawns, self._nods, self._brow_raises):
            while events and events[-1] >= t0:
                events.pop()
        while self._blink_log and self._blink_log[-1][0] >= t0:
            self._blink_log.pop()
        self._aperture.clear()
        self._pending = None
        self._brow_since = None
        for window in (self._ear, self._yaw, self._pitch, self._brow):
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
            starting = self._pitch.span < cfg.pose_baseline_min_data_s and self._pose_enrolled is None
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
            self._last_pose_t = t
        elif self._enrolled_pose() is not None:
            pitch_ref = self._pose_enrolled[1]
        elif self._pitch.span > 0:
            pitch_ref = self._pitch.percentile(50, t)  # pitch only: the yaw cache keeps its own timing

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
        aperture = None
        if eye_known and not use_cnn and f.ear is not None:
            aperture = self._aperture_of(f.ear, baseline)
        self._update_closure(t, eye_closed, head_down, pitch_off is None, events)
        self._update_blink_timing(t, aperture, "blink" in events)
        masked = self._update_mask(t, mar)
        talk_only = masked and t > self._yawn_mask_until
        deep_frame = bool(eye_closed) and (
            f.p_closed >= cfg.microsleep_deep_cnn if use_cnn else self._ear_deep(f, baseline)
        )
        spared = (  # only with the blendshape's word for it: EAR alone let talking fake microsleeps (YawDD)
            talk_only
            and cfg.microsleep_mask_talk_spares_deep
            and deep_frame
            and f.eye_blink is not None
            and f.eye_blink >= cfg.microsleep_deep_blink
        )
        if masked and self._closed_since is not None and not self._head_drop and not spared:
            # Yawning / talking: restart the counted part of the closure. Not once the head
            # has dropped (a head drop is not a yawn), or falling asleep right after a yawn
            # would never reach the microsleep rules.
            self._count_since = t
            self._deep_frames = self._eye_frames = 0
        if eye_closed and self._count_since is not None:
            self._eye_frames += 1
            self._deep_frames += deep_frame
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
        blink_frac, reopen_s, reopen_ratio = self._slow_blinks(t, coverage)
        slow_blink = 0.0
        if coverage >= cfg.perclos_min_coverage_s:
            slow_blink = max(
                _ramp(blink_frac, cfg.slow_blink_time_frac_low, cfg.slow_blink_time_frac_high),
                0.0
                if reopen_ratio is None
                else _ramp(reopen_ratio, cfg.slow_blink_reopen_ratio_low, cfg.slow_blink_reopen_ratio_high),
            )
        yawning = self._update_yawn(t, mar, events)
        self._update_nod(t, dt, pitch_off, ear_low, events)
        self._update_brow(t, f, face_ok and eye_closed is False and not use_cnn, masked, baseline, events)

        self._expire(self._yawns, t, cfg.yawn_window_s)
        self._expire(self._nods, t, cfg.nod_window_s)
        self._expire(self._brow_raises, t, cfg.brow_window_s)
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
            blink_time_frac=blink_frac,
            reopen_s=reopen_s,
            reopen_ratio=reopen_ratio,
            slow_blink_score=slow_blink,
            brow_raise_count_5min=len(self._brow_raises),
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

    def _ear_deep(self, f: FrameFeatures, baseline: float) -> bool:
        """EAR firmly shut, confirmed by the eyeBlink blendshape when that vote is on and known."""
        cfg = self.config
        if f.ear is None or f.ear > baseline * cfg.microsleep_deep_ear_ratio:
            return False
        return cfg.microsleep_deep_blink <= 0 or f.eye_blink is None or f.eye_blink >= cfg.microsleep_deep_blink

    def _update_mask(self, t: float, mar: float | None) -> bool:
        """True while closed-eye time must not count toward microsleep (yawning or talking)."""
        cfg = self.config
        if mar is not None:
            if self._mask_open_since is None:
                if mar > self._mar_open:
                    self._mask_open_since = t
            elif mar < self._mar_close:
                self._mask_open_since = None
            talking = self._talking(t, mar)  # always called: keeps the MAR window filled
            yawning = self._mask_open_since is not None and t - self._mask_open_since <= cfg.microsleep_mask_max_open_s
            if yawning or talking:
                self._mask_until = t + cfg.microsleep_mask_hold_s
            if yawning:
                self._yawn_mask_until = t + cfg.microsleep_mask_hold_s
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
            if mar > self._mar_open:
                self._mouth_open_since = t
        elif mar < self._mar_close:
            self._mouth_open_since = None
            self._yawn_fired = False
        if self._mouth_open_since is not None and not self._yawn_fired and t - self._mouth_open_since >= cfg.yawn_min_s:
            self._yawn_fired = True
            self._yawns.append(t)
            events.append("yawn")
        return self._yawn_fired

    def _aperture_of(self, ear: float, baseline: float) -> float:
        """EAR scaled to 0 (the driver's closed eyes) .. 1 (open-eye baseline)."""
        if self._ear_closed_enrolled is not None and self._ear_enrolled is not None:
            closed = self._ear_closed_enrolled
        else:
            closed = self.config.blink_closed_ref_ratio * baseline
        return (ear - closed) / max(baseline - closed, 1e-6)

    def _update_blink_timing(self, t: float, aperture: float | None, blink_ended: bool) -> None:
        """Time each blink's duration and reopening on the aperture (see module doc)."""
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
            end = _cross_time(prev, (t, aperture), level)
            self._blink_log.append((end, end - start, end - deepest))
            if len(self._reopen_base) < cfg.slow_blink_baseline_blinks:
                self._reopen_base.append(end - deepest)
            self._pending = None
        elif t - deepest > cfg.slow_blink_reopen_max_s or self._closed_since is not None:
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
                return _cross_time(samples[i - 1], samples[i], level), samples[k][0]
        return None  # the closing edge is not in the recent frames: not measured

    def _slow_blinks(self, t: float, known_s: float) -> tuple[float, float | None, float | None]:
        """(blink_time_frac, median reopening time, reopen_ratio) over the PERCLOS window."""
        cfg = self.config
        while self._blink_log and t - self._blink_log[0][0] > cfg.perclos_window_s:
            self._blink_log.popleft()
        frac = sum(d for _, d, _ in self._blink_log) / known_s if known_s > 1e-9 else 0.0
        if len(self._blink_log) < cfg.slow_blink_min_blinks:
            return min(frac, 1.0), None, None
        reopen = float(np.median([r for _, _, r in self._blink_log]))
        ratio = None
        if len(self._reopen_base) >= cfg.slow_blink_min_blinks:
            ratio = reopen / max(float(np.median(self._reopen_base)), 1e-3)
        return min(frac, 1.0), reopen, ratio

    def _update_brow(
        self, t: float, f: FrameFeatures, eyes_open: bool, masked: bool, baseline: float, events: list[str]
    ) -> None:
        """Brows raised over the resting brow while the eyes droop: fighting sleep (see module doc)."""
        cfg = self.config
        if f.brow_up is None or not eyes_open or f.ear is None:
            if self._brow_last_t is not None and t - self._brow_last_t > cfg.max_gap_s:
                self._brow_since, self._brow_fired = None, False
            return
        self._brow_last_t = t
        if not masked:
            self._brow.add(t, f.brow_up)
        neutral = self._brow_enrolled
        if neutral is None:
            if self._brow.span < cfg.brow_baseline_min_data_s:
                return
            neutral = self._brow.percentile(50, t)
        raising = (
            not masked and f.brow_up - neutral >= cfg.brow_raise_above and f.ear < cfg.brow_narrow_ratio * baseline
        )
        if not raising:
            self._brow_since, self._brow_fired = None, False
            return
        if self._brow_since is None:
            self._brow_since = t
        if not self._brow_fired and t - self._brow_since >= cfg.brow_min_s:
            self._brow_fired = True
            self._brow_raises.append(t)
            events.append("brow_raise")

    def _update_nod(
        self, t: float, dt: float, pitch_off: float | None, ear_low: bool | None, events: list[str]
    ) -> None:
        cfg = self.config
        if pitch_off is None:
            if self._dip_start is not None and self._last_pose_t is not None and t - self._last_pose_t > cfg.max_gap_s:
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


def _ramp(x: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 1.0 if x >= hi else 0.0
    return min(max((x - lo) / (hi - lo), 0.0), 1.0)


def _cross_time(a: tuple[float, float], b: tuple[float, float], level: float) -> float:
    """Time where the line from sample a to sample b crosses `level` (linear interpolation)."""
    (ta, va), (tb, vb) = a, b
    if vb == va:
        return tb
    return ta + (level - va) / (vb - va) * (tb - ta)


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
        elif ev == "brow_raise":
            lines.append(f"[DROWSY] brows raised to keep the eyes open ({state.brow_raise_count_5min} in 5 min)")
    return lines
