"""Block 7, eyes: open-eye baseline, closure episodes (blinks, microsleep) and PERCLOS.

Anti false-positive rules:
- Eye closure is relative to the driver's own open-eye EAR (a high percentile of recent
  EAR), so narrow eyes are not "always closed". Hysteresis between close / reopen.
- Deep closure: closed_duration (microsleep event + L3 rule) only counts a closure that is
  mostly "firmly shut": EAR <= `microsleep_deep_ear_ratio` x the open-eye baseline (or CNN
  p_closed >= `microsleep_deep_cnn`) for at least `microsleep_deep_min_frac` of its time
  (`TimeShare`, M93: a share of time, which at an even frame rate is the share of eye frames). Narrowed eyes (looking down, squinting in sunlight, smiling) sit around 0.55-0.75
  x baseline and stay inside the close / reopen hysteresis for seconds; a real closure drops
  well below. Once the closure is deep, its whole length counts (no added delay). Blinks
  keep the looser close_ratio. With `microsleep_deep_blink` > 0, an EAR frame is deep only
  when MediaPipe's eyeBlink blendshape (block 3, pretrained, no per-driver baseline) agrees
  it is at least that shut: EAR alone also collapses for glare on glasses, a head tilted
  down and eyes that are narrow before the driver's own baseline is learnt.
- Lids droop, then shut (how falling asleep looks): the drooping sits inside the same closure and
  dilutes `microsleep_deep_min_frac`, so the L3 rule came late by about its length, or never. While
  the closure as a whole is not deep, the running stretch of firmly shut frames counts from its own
  first frame; frames that are not firmly shut for longer than `microsleep_deep_run_gap_s` end it
  (narrowed again). The yawn / talking mask restarts it like the rest of the counted part, and such
  a stretch of `head_drop_carry_min_closed_s` also starts the head-drop carry.
- Block 5's score is the eye CNN on the device and MediaPipe's eyeBlink in the web / APK build
  (FrameFeatures.p_closed_source). They are not on one scale: shut eyes give the CNN ~0.9 and
  eyeBlink 0.55-0.7, so with the CNN's 0.6 / 0.8 an eyeBlink closure never became "deep" (own
  recordings 0 / 48 closures at L3, FL3D 0 / 95). eyeBlink frames use `eye_blendshape_closed` /
  `eye_blendshape_open` / `microsleep_deep_blendshape` instead (thresholds.yaml for the numbers).
- PERCLOS judges every frame on its own (EAR < `perclos_close_ratio` x the open-eye
  baseline, or CNN p_closed >= `eye_cnn_closed`), not with the close / reopen hysteresis:
  after a blink, the hysteresis keeps narrowed eyes (squinting in sunlight, 0.65-0.75 x
  baseline) "closed" until they open wide again, which reads as PERCLOS near 100 %.
  Hysteresis is for episodes (blinks, microsleep); PERCLOS is a time fraction.
- PERCLOS only raises "perclos_high" after `perclos_min_coverage_s` of eye data.
- Short face dropouts (< max_gap_s) do not break episodes; longer ones end them
  without counting a blink. So does a gap that long between two frames (analyzer.py): the eyes
  were not seen in it, and a carried closure (head drop) ends there too.
- Head drop: when the eyes were seen closed for `head_drop_carry_min_closed_s` and the
  head then drops past `eye_max_pitch_down_deg` (eyes can no longer be judged), the
  closure keeps counting while the head stays down or the face is lost, so falling
  asleep with a head drop still reaches the microsleep L3 rule. A blink followed by a
  glance down is shorter than the minimum and is not carried. Only a deep closure is
  carried (`microsleep_deep_min_frac` of the episode's time firmly shut): lids lowered
  while slowly bowing to the phone / dashboard used to start the carry and raise L3.
  The carry needs something to go on: after `head_drop_carry_max_lost_s` with neither the eyes nor a
  lowered head in view (the face is gone) it ends. Nothing says the eyes are still shut then, and
  only a face coming back could end it: the L3 stayed up for as long as the camera was covered, and
  "monitoring unavailable" with its "Bạn còn ở đó không?" (blocks 9, 12) never ran. They do now.
- Blink rate is blinks per minute of eye data: the blinks of the last `blink_window_s` over the
  seconds the eyes were read in it (at least `blink_rate_min_span_s`). Over clock time, as before, a
  driver seen half the time read half the rate (15 blinks a minute as 8), and so did the first
  minute after the scores were dropped (rest, enrollment).
- Looking down: the upper lids follow the gaze, so EAR drops to about half the open-eye value
  and MediaPipe's eyeBlink rises too (real microsleeps on FL3D: eyeBlink p50 0.63, so the
  blendshape vote cannot tell them apart). With the head bowed at least
  `microsleep_deep_bowed_pitch_deg` below the usual pose, a deep EAR frame needs EAR <=
  `microsleep_deep_bowed_ear_ratio` x baseline (FL3D microsleeps with the head bowed: EAR p90
  0.33-0.41 x, all 83 L3 alerts kept at 0.35). Lowered lids that are not that shut are
  "gaze_down": block 8 counts them as looking off the road (L2), not as sleep.
- Looking down, enrolled driver (off by default): how far eyeBlink goes with the eyes shut differs
  per person, and lids lowered to look at a phone on the lap stay below it (own recordings, one
  person: 0.46-0.57 against 0.67-0.71 shut). With `microsleep_deep_enrolled_blink_ratio` > 0 the
  vote needs that x the eyeBlink measured in the close-eyes step of the enrollment instead of the
  fixed `microsleep_deep_blink`. Off because a drowsy closure is shallower than a deliberate one:
  every ratio that removed the false L3 also lost real FL3D microsleeps (thresholds.yaml).
- Driver enrollment: the open-eye baseline starts at the driver's enrolled EAR and only
  drifts within `eye_enrolled_max_drop` below / `eye_enrolled_max_rise` above it: eyes
  narrowing over tens of minutes of drowsiness no longer drag the baseline down and hide
  PERCLOS / deep closures.
"""

from __future__ import annotations

from collections import deque

from edge_agent.analysis.drowsiness.common import RollingWindow, TimeShare, drop_since, expire
from edge_agent.analysis.drowsiness.config import DrowsinessConfig
from edge_agent.perception.features import FrameFeatures


class EyeBaseline:
    """The driver's open-eye EAR: a high percentile of recent EAR, held near the enrolled value."""

    def __init__(self, config: DrowsinessConfig) -> None:
        self.config = config
        self._window = RollingWindow(config.eye_baseline_window_s, config.baseline_recompute_s)
        self.enrolled: float | None = None  # open-eye EAR from driver enrollment
        self.enrolled_closed: float | None = None  # closed-eye EAR from driver enrollment

    def set_enrolled(self, ear_open: float, ear_closed: float | None) -> None:
        """Set the open-eye and closed-eye EAR measured at enrollment."""
        self.enrolled = ear_open
        self.enrolled_closed = ear_closed

    def add(self, t: float, ear: float) -> None:
        """Add one open-eye EAR reading."""
        self._window.add(t, ear)

    def value(self, t: float) -> float:
        """The open-eye EAR at time t: the initial or enrolled value until enough data, then the
        percentile of the window, held near the enrolled value and inside the configured bounds."""
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
        """Forget the readings taken at or after t0."""
        self._window.drop_since(t0)


def deep_blink_vote(config: DrowsinessConfig, blink_closed: float | None) -> float:
    """eyeBlink an EAR deep frame needs: `microsleep_deep_blink`, or for an enrolled driver
    `microsleep_deep_enrolled_blink_ratio` x the eyeBlink of that driver's own shut eyes when that is
    higher. 0 = no vote."""
    vote = config.microsleep_deep_blink
    if vote <= 0 or blink_closed is None or config.microsleep_deep_enrolled_blink_ratio <= 0:
        return vote
    return max(vote, blink_closed * config.microsleep_deep_enrolled_blink_ratio)


def ear_deep(
    config: DrowsinessConfig, f: FrameFeatures, baseline: float, bowed: bool = False, blink_vote: float | None = None
) -> bool:
    """EAR firmly shut, confirmed by the eyeBlink blendshape when that vote is on and known. Bowed
    head: the stricter `microsleep_deep_bowed_ear_ratio` (lids lowered to look down are not shut).
    blink_vote: the driver's own vote (`deep_blink_vote`); None = `microsleep_deep_blink`."""
    ratio = config.microsleep_deep_bowed_ear_ratio if bowed else config.microsleep_deep_ear_ratio
    if f.ear is None or f.ear > baseline * ratio:
        return False
    vote = config.microsleep_deep_blink if blink_vote is None else blink_vote
    return vote <= 0 or f.eye_blink is None or f.eye_blink >= vote


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
        self._counted = TimeShare()  # time of the counted closure firmly shut (M93: time, not frames)
        self._episode = TimeShare()  # same, over the whole episode (not reset by the yawn / talking mask)
        self._run_since: float | None = None  # first frame of the running stretch of firmly shut frames
        self._run_last = 0.0  # its latest firmly shut frame
        self._carry_seen_t = 0.0  # head-drop carry: last frame that showed the head down
        self._blinks: deque[float] = deque()
        self._seen: deque[tuple[float, float]] = deque()  # (t, dt) of the frames with the eyes read
        self._seen_s = 0.0

    def judge(self, closing: bool, opening: bool) -> bool:
        """Eye state with hysteresis: closes on `closing`, reopens only on `opening`."""
        if self._eye_closed and opening:
            self._eye_closed = False
        elif not self._eye_closed and closing:
            self._eye_closed = True
        return self._eye_closed

    def end(self) -> None:
        """The closure episode is over: its durations and flags start again."""
        self.closed_since = None
        self._count_since = None
        self._microsleep_fired = False
        self.head_drop = False
        self._counted.reset()
        self._episode.reset()
        self._run_since = None

    def _episode_is_deep(self) -> bool:
        return self._episode.at_least(self.config.microsleep_deep_min_frac)

    def update(self, t: float, eye_closed: bool | None, head_down: bool, face_lost: bool, events: list[str]) -> None:
        """One frame of the eye state (None = not read): times the closure, counts blinks, appends
        "microsleep" to `events` and carries a closure through a head drop or a lost face."""
        cfg = self.config
        if eye_closed is None:
            if self.closed_since is None or self._last_eye_t is None:
                return
            if self.head_drop:
                # Carried closure: goes on while the head stays down or the face is lost, the latter
                # for `head_drop_carry_max_lost_s` at most.
                if head_down:
                    self._carry_seen_t = t
                lost_s = cfg.head_drop_carry_max_lost_s
                if not (head_down or face_lost) or (lost_s > 0 and t - self._carry_seen_t > lost_s):
                    self.end()
                return
            # From the start of the closure, not of its counted part: eyes shut during a
            # yawn / talking still qualify for the carry when the head drops.
            closed_before = self._last_eye_t - self.closed_since
            if (
                head_down
                and t - self._last_eye_t <= cfg.max_gap_s
                and closed_before >= cfg.head_drop_carry_min_closed_s
                # lids lowered to look down are not carried
                and (self._episode_is_deep() or self._run_s(self._last_eye_t) >= cfg.head_drop_carry_min_closed_s)
            ):
                self.head_drop = True  # eyes shut, then the head dropped: keep counting
                self._carry_seen_t = t
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
            self._counted.reset()
            self._run_since = None

    def _run_s(self, t: float) -> float:
        """Seconds since the running stretch of firmly shut frames began (0: none, or the rule is off)."""
        return (
            t - self._run_since if self._run_since is not None and self.config.microsleep_deep_run_gap_s >= 0 else 0.0
        )

    def closed_duration(
        self, t: float, dt: float, eye_closed: bool | None, deep_frame: bool, events: list[str]
    ) -> float:
        """Seconds of the counted, deep closure (0 when not deep); fires "microsleep" once.
        dt: seconds since the frame before (the share of firmly shut frames is a share of time)."""
        cfg = self.config
        self._episode.step(dt, deep_frame if eye_closed and self.closed_since is not None else None)
        counted = bool(eye_closed) and self._count_since is not None
        self._counted.step(dt, deep_frame if counted else None)
        if counted:
            if deep_frame:
                if self._run_since is None:
                    self._run_since = t
                self._run_last = t
            elif self._run_since is not None and t - self._run_last > cfg.microsleep_deep_run_gap_s:
                self._run_since = None  # the lids came back up: narrowed again, not shut
        deep = self._counted.at_least(cfg.microsleep_deep_min_frac)
        if self._count_since is None:
            duration = 0.0
        elif deep:
            duration = t - self._count_since
        else:  # too much narrowing before it: only the firmly shut stretch counts
            duration = self._run_s(t)
        if duration >= cfg.microsleep_min_s and not self._microsleep_fired:
            self._microsleep_fired = True
            events.append("microsleep")
        return duration

    def blink_rate(self, t: float, dt: float, eye_known: bool) -> tuple[float, float]:
        """(blinks per minute of eye data over `blink_window_s`, seconds of eye data in that window).
        dt: seconds this frame adds; eye_known: the eyes were read on it."""
        cfg = self.config
        expire(self._blinks, t, cfg.blink_window_s)
        if eye_known and dt > 0:
            self._seen.append((t, dt))
            self._seen_s += dt
        while self._seen and t - self._seen[0][0] > cfg.blink_window_s:
            self._seen_s -= self._seen.popleft()[1]
        if not self._seen:  # no rounding residue in the running sum
            self._seen_s = 0.0
        observed = min(max(self._seen_s, 0.0), cfg.blink_window_s)
        return len(self._blinks) / max(observed, cfg.blink_rate_min_span_s) * 60.0, observed

    def forget_since(self, t0: float) -> None:
        """End the running closure and forget the blinks and frames seen at or after t0."""
        self.end()
        drop_since(self._blinks, t0)
        while self._seen and self._seen[-1][0] >= t0:
            self._seen_s -= self._seen.pop()[1]


class Perclos:
    """Fraction of eye-known time with the eyes closed over `perclos_window_s`, and "perclos_high"."""

    def __init__(self, config: DrowsinessConfig, emit: bool = True) -> None:
        """emit False: only measured (the P80 variant), never a "perclos_high" event."""
        self.config = config
        self._emit = emit
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
        if self._emit and known >= cfg.perclos_min_coverage_s:
            if self._armed and perclos >= cfg.perclos_drowsy:
                self._armed = False
                events.append("perclos_high")
            elif not self._armed and perclos < cfg.perclos_rearm:
                self._armed = True
        return perclos, known

    def forget_since(self, t0: float) -> None:
        """Forget the samples taken at or after t0."""
        while self._samples and self._samples[-1][0] >= t0:
            _, dt, closed = self._samples.pop()
            self._known -= dt
            self._closed -= dt if closed else 0.0
        if not self._samples:  # nothing left: no rounding residue in the running sums
            self._known = self._closed = 0.0
        self._armed = True
