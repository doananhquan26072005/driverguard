"""Block 7: DrowsinessAnalyzer puts the drowsiness sub-modules together, one frame at a time.

Order on each frame: open-eye baseline -> head pose -> eye state (hysteresis) -> closure
episode -> blink timing -> yawn / talking mask -> deep closure (closed_duration) -> PERCLOS (and
the P80 variant, measured only) ->
blink rate, slow blinks -> yawn -> nod -> brow raise. The rules live in the sub-modules:
eyes.py, mouth.py, head.py, slow_blink.py, brow.py.

- A face partly out of frame (FrameFeatures.face_reliable False, block 6) is handled like
  a lost face: its EAR / MAR / pose feed neither PERCLOS, the eye baseline, yawns nor nods.
  Its pitch is only used to see a head drop (a driver slumping forward often slides out
  of frame), so the head-drop carry still starts.
- Driver enrollment (block 6 stage, `set_profile`): the eye baseline, yawn thresholds, head
  pose, blink aperture and resting brow use the driver's own values from then on. Without
  enrollment (skipped, evaluation clips) everything is self-learnt.
- After a rest (the vehicle parked, block 10), `forget_since` drops what was gathered
  since the vehicle stopped: eyes closed to rest and waking-up yawns say nothing about the
  next drive. Events from before the stop stay.
"""

from __future__ import annotations

from edge_agent.analysis.drowsiness.brow import BrowRaise
from edge_agent.analysis.drowsiness.config import DrowsinessConfig, DrowsinessState
from edge_agent.analysis.drowsiness.eyes import EyeBaseline, EyeClosure, Perclos, deep_blink_vote, ear_deep
from edge_agent.analysis.drowsiness.head import HeadPose, NodDetector
from edge_agent.analysis.drowsiness.mouth import MouthMask, YawnCounter
from edge_agent.analysis.drowsiness.slow_blink import SlowBlinks
from edge_agent.perception.features import FrameFeatures


class DrowsinessAnalyzer:
    def __init__(self, config: DrowsinessConfig | None = None) -> None:
        self.config = config or DrowsinessConfig()
        cfg = self.config
        self._mar_open, self._mar_close = cfg.yawn_mar_open, cfg.yawn_mar_close  # enrolled: driver's own
        self._start_t: float | None = None
        self._last_t: float | None = None
        self._baseline = EyeBaseline(cfg)
        self._blink_vote = deep_blink_vote(cfg, None)  # enrolled: from the driver's own shut eyes
        self._pose = HeadPose(cfg)
        self._closure = EyeClosure(cfg)
        self._perclos = Perclos(cfg)
        self._perclos_p80 = Perclos(cfg, emit=False)  # measured next to it, never scored
        self._mask = MouthMask(cfg)
        self._yawn = YawnCounter(cfg)
        self._nod = NodDetector(cfg)
        self._slow = SlowBlinks(cfg)
        self._brow = BrowRaise(cfg)

    # ------------------------------------------------------------------ helpers
    def set_profile(
        self,
        ear_open: float,
        mar_closed: float,
        road_yaw: float,
        road_pitch: float,
        ear_closed: float | None = None,
        brow_neutral: float | None = None,
        blink_closed: float | None = None,
    ) -> None:
        """Use the driver's enrolled reference values from now on (see module doc)."""
        cfg = self.config
        self._baseline.set_enrolled(ear_open, ear_closed)
        self._blink_vote = deep_blink_vote(cfg, blink_closed)
        self._brow.set_enrolled(brow_neutral)
        self._slow.reset()  # blink timing changes scale (aperture between the enrolled EARs)
        self._pose.set_enrolled(road_yaw, road_pitch)
        self._mar_open = mar_closed + cfg.yawn_enrolled_open_above
        self._mar_close = mar_closed + cfg.yawn_enrolled_close_above

    def ear_baseline(self, t: float) -> float:
        return self._baseline.value(t)

    def forget_since(self, t0: float) -> None:
        """Drop what was gathered from t0 on (the vehicle stopped for a rest, block 10): the
        closure episode, PERCLOS samples, blinks, yawns, nods and baseline samples."""
        self._closure.forget_since(t0)
        self._perclos.forget_since(t0)
        self._perclos_p80.forget_since(t0)
        self._yawn.forget_since(t0)
        self._nod.forget_since(t0)
        self._slow.forget_since(t0)
        self._brow.forget_since(t0)
        self._baseline.drop_since(t0)
        self._pose.drop_since(t0)

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
        baseline = self._baseline.value(t)
        close_thr = baseline * cfg.eye_close_ratio
        open_thr = baseline * cfg.eye_open_ratio
        if use_cnn and f.p_closed_source == "blendshape":  # eyeBlink reads lower than the CNN (see eyes.py)
            p_closed_thr, p_open_thr = cfg.eye_blendshape_closed, cfg.eye_blendshape_open
            p_deep_thr = cfg.microsleep_deep_blendshape
        else:
            p_closed_thr, p_open_thr, p_deep_thr = cfg.eye_cnn_closed, cfg.eye_cnn_open, cfg.microsleep_deep_cnn
        if use_cnn:
            ear_low = f.p_closed >= p_closed_thr  # raw, ignores pose (used by nod)
        else:
            ear_low = None if f.ear is None or not face_ok else f.ear < close_thr

        # Head pose relative to the driver's usual pose (rolling median of eyes-open frames).
        yaw_off, pitch_off, pitch_ref = self._pose.update(t, f, face_ok, ear_low)

        # Eye state with a per-driver threshold.
        pose_ok = (
            yaw_off is not None and abs(yaw_off) <= cfg.eye_max_yaw_deg and pitch_off <= cfg.eye_max_pitch_down_deg
        )
        eye_known = face_ok and pose_ok and (use_cnn or f.ear is not None)
        if eye_known and f.ear is not None and (not use_cnn or f.p_closed <= p_open_thr):
            self._baseline.add(t, f.ear)  # an unreliable EAR must not become the driver's "open eye" value

        eye_closed: bool | None = None
        if eye_known:
            if use_cnn:
                closing, opening = f.p_closed >= p_closed_thr, f.p_closed <= p_open_thr
            else:
                closing, opening = f.ear < close_thr, f.ear > open_thr
            eye_closed = self._closure.judge(closing, opening)

        if pitch_off is None and f.face_found and f.pitch is not None and pitch_ref is not None:
            head_off = f.pitch - pitch_ref  # partial face: good enough to see a head drop
        else:
            head_off = pitch_off
        head_down = head_off is not None and head_off > cfg.eye_max_pitch_down_deg
        aperture = None
        if eye_known and not use_cnn and f.ear is not None:
            aperture = self._slow.aperture_of(f.ear, baseline, self._baseline.enrolled, self._baseline.enrolled_closed)
        self._closure.update(t, eye_closed, head_down, pitch_off is None, events)
        self._slow.update(t, aperture, "blink" in events, self._closure.closed_since is not None)
        masked = self._mask.update(t, mar, self._mar_open, self._mar_close)
        talk_only = masked and self._mask.talk_only(t)
        bowed = (
            cfg.microsleep_deep_bowed_pitch_deg > 0
            and pitch_off is not None
            and pitch_off >= cfg.microsleep_deep_bowed_pitch_deg
        )
        deep_frame = bool(eye_closed) and (
            f.p_closed >= p_deep_thr if use_cnn else ear_deep(cfg, f, baseline, bowed, self._blink_vote)
        )
        gaze_down = bool(eye_closed) and bowed and not deep_frame  # looking down, not asleep (block 8)
        spared = (  # only with the blendshape's word for it: EAR alone let talking fake microsleeps (YawDD)
            talk_only
            and cfg.microsleep_mask_talk_spares_deep
            and deep_frame
            and f.eye_blink is not None
            and f.eye_blink >= self._blink_vote
        )
        if masked and not spared:
            self._closure.mask(t)
        closed_duration = self._closure.closed_duration(t, eye_closed, deep_frame, events)

        # Per frame, not the hysteresis state: narrowed eyes after a blink are not closed.
        perclos_eye: bool | None = None
        if eye_known and not (masked and cfg.perclos_use_mask):
            if use_cnn:
                perclos_eye = f.p_closed >= p_closed_thr
            else:
                perclos_eye = f.ear < baseline * cfg.perclos_close_ratio
        perclos, coverage = self._perclos.update(t, dt, perclos_eye, events)
        # P80, the definition the literature means by PERCLOS: lids more than 80 % closed. Only frames
        # where EAR decided (a CNN probability is not an aperture), no yawn / talking mask, blinks kept.
        p80_eye = None if aperture is None else aperture < cfg.perclos_p80_aperture
        perclos_p80, coverage_p80 = self._perclos_p80.update(t, dt, p80_eye, events)
        blink_rate = self._closure.blink_rate(t, self._start_t)
        blink_frac, reopen_s, reopen_ratio = self._slow.stats(t, coverage)
        slow_blink = self._slow.score(coverage, blink_frac, reopen_ratio)
        yawning = self._yawn.update(t, mar, self._mar_open, self._mar_close, events)
        self._nod.update(t, dt, pitch_off, ear_low, self._pose.last_t, events)
        self._brow.update(t, f, face_ok and eye_closed is False and not use_cnn, masked, baseline, events)

        return DrowsinessState(
            timestamp=t,
            eye_closed=eye_closed,
            eye_source=None if eye_closed is None else ((f.p_closed_source or "cnn") if use_cnn else "ear"),
            head_drop=self._closure.head_drop,
            gaze_down=gaze_down,
            deep_closed=deep_frame,
            pitch_baseline=pitch_ref,
            closure_masked=masked,
            closed_duration=closed_duration,
            microsleep=closed_duration >= cfg.microsleep_min_s,
            perclos_60s=perclos,
            perclos_coverage_s=coverage,
            perclos_ready=coverage >= cfg.perclos_min_coverage_s,
            blink_rate=blink_rate,
            yawning=yawning,
            yawn_count_10min=self._yawn.count(t),
            nod_count_5min=self._nod.count(t),
            ear_open_baseline=baseline,
            ear_closed_threshold=close_thr,
            events=tuple(events),
            blink_time_frac=blink_frac,
            reopen_s=reopen_s,
            reopen_ratio=reopen_ratio,
            slow_blink_score=slow_blink,
            brow_raise_count_5min=self._brow.count(t),
            perclos_p80_60s=perclos_p80,
            perclos_p80_coverage_s=coverage_p80,
        )


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
