"""Block 7, eyes: open-eye baseline, closure episodes (blinks, microsleep) and PERCLOS.

Anti false-positive rules:
- Eye closure is relative to the driver's own open-eye EAR (a high percentile of recent
  EAR), so narrow eyes are not "always closed". Hysteresis between close / reopen.
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
- PERCLOS only raises "perclos_high" after `perclos_min_coverage_s` of eye data.
- Short face dropouts (< max_gap_s) do not break episodes; longer ones end them
  without counting a blink.
- Head drop: when the eyes were seen closed for `head_drop_carry_min_closed_s` and the
  head then drops past `eye_max_pitch_down_deg` (eyes can no longer be judged), the
  closure keeps counting while the head stays down or the face is lost, so falling
  asleep with a head drop still reaches the microsleep L3 rule. A blink followed by a
  glance down is shorter than the minimum and is not carried. Only a deep closure is
  carried (`microsleep_deep_min_frac` of the episode's eye frames firmly shut): lids lowered
  while slowly bowing to the phone / dashboard used to start the carry and raise L3.
- Looking down: the upper lids follow the gaze, so EAR drops to about half the open-eye value
  and MediaPipe's eyeBlink rises too (real microsleeps on FL3D: eyeBlink p50 0.63, so the
  blendshape vote cannot tell them apart). With the head bowed at least
  `microsleep_deep_bowed_pitch_deg` below the usual pose, a deep EAR frame needs EAR <=
  `microsleep_deep_bowed_ear_ratio` x baseline (FL3D microsleeps with the head bowed: EAR p90
  0.33-0.41 x, all 83 L3 alerts kept at 0.35). Lowered lids that are not that shut are
  "gaze_down": block 8 counts them as looking off the road (L2), not as sleep.
- Driver enrollment: the open-eye baseline starts at the driver's enrolled EAR and only
  drifts within `eye_enrolled_max_drop` below / `eye_enrolled_max_rise` above it: eyes
  narrowing over tens of minutes of drowsiness no longer drag the baseline down and hide
  PERCLOS / deep closures.
"""

from __future__ import annotations

from collections import deque

from edge_agent.analysis.drowsiness.common import RollingWindow, drop_since, expire
from edge_agent.analysis.drowsiness.config import DrowsinessConfig
from edge_agent.perception.features import FrameFeatures


class EyeBaseline:
    """The driver's open-eye EAR: a high percentile of recent EAR, held near the enrolled value."""

    def __init__(self, config: DrowsinessConfig) -> None:
        self.config = config
        self._window = RollingWindow(config.eye_baseline_window_s)
        self.enrolled: float | None = None  # open-eye EAR from driver enrollment
        self.enrolled_closed: float | None = None  # closed-eye EAR from driver enrollment

    def set_enrolled(self, ear_open: float, ear_closed: float | None) -> None:
        self.enrolled = ear_open
        self.enrolled_closed = ear_closed

    def add(self, t: float, ear: float) -> None:
        self._window.add(t, ear)

    def value(self, t: float) -> float:
        cfg = self.config
        enrolled = self.enrolled
        if self._window.span < cfg.eye_baseline_min_data_s:
            value = cfg.eye_baseline_init if enrolled is None else enrolled
        else:
            value = self._window.percentile(cfg.eye_baseline_percentile, t)
        if enrolled is not None:
            value = min(
                max(value, enrolled * (1.0 - cfg.eye_enrolled_max_drop)), enrolled * (1.0 + cfg.eye_enrolled_max_rise)
            )
        return min(max(value, cfg.eye_baseline_min), cfg.eye_baseline_max)

    def drop_since(self, t0: float) -> None:
        self._window.drop_since(t0)


def ear_deep(config: DrowsinessConfig, f: FrameFeatures, baseline: float, bowed: bool = False) -> bool:
    """EAR firmly shut, confirmed by the eyeBlink blendshape when that vote is on and known. Bowed
    head: the stricter `microsleep_deep_bowed_ear_ratio` (lids lowered to look down are not shut)."""
    ratio = config.microsleep_deep_bowed_ear_ratio if bowed else config.microsleep_deep_ear_ratio
    if f.ear is None or f.ear > baseline * ratio:
        return False
    return config.microsleep_deep_blink <= 0 or f.eye_blink is None or f.eye_blink >= config.microsleep_deep_blink


class EyeClosure:
    """Close / reopen hysteresis and closure episodes: blinks, deep closures, the head-drop carry."""

    def __init__(self, config: DrowsinessConfig) -> None:
        self.config = config
        self._eye_closed = False
        self._last_eye_t: float | None = None
        self.closed_since: float | None = None  # start of the closure episode (blinks)
        self._count_since: float | None = None  # start of the counted part (closed_duration)
        self._microsleep_fired = False
        self.head_drop = False  # closure carried through a head drop
        self._deep_frames = 0  # eye frames of the counted closure that are firmly shut
        self._eye_frames = 0
        self._episode_deep = 0  # same, over the whole episode (not reset by the yawn / talking mask)
        self._episode_eye = 0
        self._blinks: deque[float] = deque()

    def judge(self, closing: bool, opening: bool) -> bool:
        """Eye state with hysteresis: closes on `closing`, reopens only on `opening`."""
        if self._eye_closed and opening:
            self._eye_closed = False
        elif not self._eye_closed and closing:
            self._eye_closed = True
        return self._eye_closed

    def end(self) -> None:
        self.closed_since = None
        self._count_since = None
        self._microsleep_fired = False
        self.head_drop = False
        self._deep_frames = self._eye_frames = 0
        self._episode_deep = self._episode_eye = 0

    def _episode_is_deep(self) -> bool:
        return self._episode_eye > 0 and self._episode_deep >= self.config.microsleep_deep_min_frac * self._episode_eye

    def update(self, t: float, eye_closed: bool | None, head_down: bool, face_lost: bool, events: list[str]) -> None:
        cfg = self.config
        if eye_closed is None:
            if self.closed_since is None or self._last_eye_t is None:
                return
            if self.head_drop:
                # Carried closure: goes on while the head stays down or the face is lost.
                if not (head_down or face_lost):
                    self.end()
                return
            # From the start of the closure, not of its counted part: eyes shut during a
            # yawn / talking still qualify for the carry when the head drops.
            closed_before = self._last_eye_t - self.closed_since
            if (
                head_down
                and t - self._last_eye_t <= cfg.max_gap_s
                and closed_before >= cfg.head_drop_carry_min_closed_s
                and self._episode_is_deep()  # lids lowered to look down are not carried
            ):
                self.head_drop = True  # eyes shut, then the head dropped: keep counting
                return
            # Unknown: keep a running episode through short dropouts only.
            if t - self._last_eye_t > cfg.max_gap_s:
                self.end()
            return
        self._last_eye_t = t
        self.head_drop = False
        if eye_closed:
            if self.closed_since is None:
                self.closed_since = self._count_since = t
        elif self.closed_since is not None:
            if t - self.closed_since <= cfg.blink_max_s:
                self._blinks.append(t)
                events.append("blink")
            self.end()

    def mask(self, t: float) -> None:
        """Yawning / talking: restart the counted part of the closure. Not once the head
        has dropped (a head drop is not a yawn), or falling asleep right after a yawn
        would never reach the microsleep rules."""
        if self.closed_since is not None and not self.head_drop:
            self._count_since = t
            self._deep_frames = self._eye_frames = 0

    def closed_duration(self, t: float, eye_closed: bool | None, deep_frame: bool, events: list[str]) -> float:
        """Seconds of the counted, deep closure (0 when not deep); fires "microsleep" once."""
        cfg = self.config
        if eye_closed and self.closed_since is not None:
            self._episode_eye += 1
            self._episode_deep += deep_frame
        if eye_closed and self._count_since is not None:
            self._eye_frames += 1
            self._deep_frames += deep_frame
        deep = self._eye_frames > 0 and self._deep_frames >= cfg.microsleep_deep_min_frac * self._eye_frames
        duration = t - self._count_since if self._count_since is not None and deep else 0.0
        if duration >= cfg.microsleep_min_s and not self._microsleep_fired:
            self._microsleep_fired = True
            events.append("microsleep")
        return duration

    def blink_rate(self, t: float, start_t: float) -> float:
        """Blinks per minute over `blink_window_s` (or since start_t, at least `blink_rate_min_span_s`)."""
        cfg = self.config
        expire(self._blinks, t, cfg.blink_window_s)
        observed = min(t - start_t, cfg.blink_window_s)
        return len(self._blinks) / max(observed, cfg.blink_rate_min_span_s) * 60.0

    def forget_since(self, t0: float) -> None:
        self.end()
        drop_since(self._blinks, t0)


class Perclos:
    """Fraction of eye-known time with the eyes closed over `perclos_window_s`, and "perclos_high"."""

    def __init__(self, config: DrowsinessConfig) -> None:
        self.config = config
        self._samples: deque[tuple[float, float, bool]] = deque()  # (t, dt, closed)
        self._closed = 0.0
        self._known = 0.0
        self._armed = True

    def update(self, t: float, dt: float, eye_closed: bool | None, events: list[str]) -> tuple[float, float]:
        """(PERCLOS, seconds of eye data in the window)."""
        cfg = self.config
        if eye_closed is not None and dt > 0:
            self._samples.append((t, dt, eye_closed))
            self._known += dt
            self._closed += dt if eye_closed else 0.0
        while self._samples and t - self._samples[0][0] > cfg.perclos_window_s:
            _, old_dt, old_closed = self._samples.popleft()
            self._known -= old_dt
            self._closed -= old_dt if old_closed else 0.0
        known = max(self._known, 0.0)
        perclos = self._closed / known if known > 1e-9 else 0.0
        if known >= cfg.perclos_min_coverage_s:
            if self._armed and perclos >= cfg.perclos_drowsy:
                self._armed = False
                events.append("perclos_high")
            elif not self._armed and perclos < cfg.perclos_rearm:
                self._armed = True
        return perclos, known

    def forget_since(self, t0: float) -> None:
        while self._samples and self._samples[-1][0] >= t0:
            _, dt, closed = self._samples.pop()
            self._known -= dt
            self._closed -= dt if closed else 0.0
        self._armed = True
