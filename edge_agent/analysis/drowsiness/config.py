"""Block 7 configuration (thresholds.yaml -> drowsiness) and per-frame output."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from edge_agent.config import config_from_dict


@dataclass(frozen=True)
class DrowsinessConfig:
    max_gap_s: float = 0.5
    baseline_recompute_s: float = 1.0  # the rolling baselines recompute their percentile this often
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
    # Same, when block 5's score is MediaPipe's eyeBlink (web / APK): shut eyes read lower than the CNN's
    eye_blendshape_closed: float = 0.4
    eye_blendshape_open: float = 0.3
    # Keep counting a closure through a head drop (eyes closed at least this long before it)
    head_drop_carry_min_closed_s: float = 0.5
    # ... and for at most this long with neither the eyes nor a lowered head in view (0 = no limit)
    head_drop_carry_max_lost_s: float = 30.0
    # Closure episodes
    blink_max_s: float = 0.5
    blink_window_s: float = 60.0
    blink_rate_min_span_s: float = 10.0  # blink rate divides by at least this much eye data
    microsleep_min_s: float = 1.0
    # Only a deep closure counts toward closed_duration (see eyes.py)
    microsleep_deep_ear_ratio: float = 0.5
    microsleep_deep_cnn: float = 0.8
    microsleep_deep_blendshape: float = 0.55  # block 5 score = eyeBlink
    microsleep_deep_min_frac: float = 0.5
    # Below min_frac, the running stretch of deep frames counts from its own start; frames that are not
    # deep for longer than this end it (< 0 = off)
    microsleep_deep_run_gap_s: float = 0.0
    microsleep_deep_blink: float = 0.5  # EAR deep frames also need eyeBlink >= this when known (0 = off)
    # Enrolled driver: the vote needs this x the driver's own closed-eye eyeBlink, if that is higher (0 = off)
    microsleep_deep_enrolled_blink_ratio: float = 0.0
    microsleep_deep_bowed_pitch_deg: float = 10.0  # head this far below the usual pose = bowed (0 = off)
    microsleep_deep_bowed_ear_ratio: float = 0.35  # bowed: a deep EAR frame needs EAR <= this x baseline
    # Closed-eye time does not count toward microsleep while yawning (see mouth.py)
    microsleep_mask_hold_s: float = 1.5
    microsleep_mask_max_open_s: float = 8.0
    microsleep_mask_talk_window_s: float = 2.0
    microsleep_mask_talk_swing: float = 0.08
    microsleep_mask_talk_min_swings: int = 3  # 0 = no talking mask
    microsleep_mask_talk_spares_deep: bool = True  # talking does not restart a deep closure (see mouth.py)
    # PERCLOS
    perclos_window_s: float = 60.0
    perclos_min_coverage_s: float = 30.0
    perclos_drowsy: float = 0.15
    perclos_rearm: float = 0.12
    perclos_use_mask: bool = True  # skip yawn / talking-masked frames (see mouth.py)
    perclos_close_ratio: float = 0.65  # per-frame closed test for PERCLOS (see eyes.py)
    # P80 measured next to it, never scored: closed = eye aperture below this (0 = the closed EAR)
    perclos_p80_aperture: float = 0.2
    # Yawn
    yawn_mar_open: float = 0.45
    yawn_mar_close: float = 0.34
    yawn_min_s: float = 1.5
    yawn_window_s: float = 600.0
    yawn_enrolled_open_above: float = 0.40  # enrolled: mar_open = closed-mouth MAR + this
    yawn_enrolled_close_above: float = 0.29  # enrolled: mar_close = closed-mouth MAR + this
    yawn_yaw_correct: bool = True  # MAR x cos(yaw): a turned head narrows the mouth in the image (see mouth.py)
    # Slow blinks (see slow_blink.py)
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
    nod_bottom_frac: float = 0.15  # "the bottom" of a dip = within this share of its depth
    nod_require_eyes_closed: bool = True
    nod_eyes_closed_min_frac: float = 0.3
    nod_eyes_deep: bool = True  # "closed" in a dip = firmly shut, as the deep closure judges it (see head.py)
    nod_window_s: float = 300.0
    # Brow raise to keep the eyes open (see brow.py)
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
    blink_rate: float  # blinks per minute of eye data (see eyes.py)
    yawning: bool
    yawn_count_10min: int
    nod_count_5min: int
    ear_open_baseline: float
    ear_closed_threshold: float
    events: tuple[str, ...] = ()
    eye_source: str | None = None  # "ear", "cnn" or "blendshape": what decided eye_closed on this frame
    head_drop: bool = False  # closure carried through a head drop (eye state unknown)
    gaze_down: bool = False  # head bowed, lids lowered but not firmly shut: looking down, not asleep (block 8)
    deep_closed: bool = False  # this frame counts as firmly shut (the deep-closure rule): the iris is not seen
    pitch_baseline: float | None = None  # the driver's usual pitch (eyes-open median)
    closure_masked: bool = False  # yawn mask: closed-eye time is not counted on this frame
    perclos_ready: bool = False  # perclos_coverage_s >= perclos_min_coverage_s: PERCLOS is meaningful
    blink_time_frac: float = 0.0  # time spent in blinks / eye-known time, PERCLOS window
    reopen_s: float | None = None  # median eyelid reopening time of the window's blinks
    reopen_ratio: float | None = None  # reopen_s / the driver's own early-trip median
    slow_blink_score: float = 0.0  # 0..1, a drowsy_score term (needs PERCLOS coverage)
    brow_raise_count_5min: int = 0
    # PERCLOS by the P80 definition (lids more than 80 % closed), EAR frames only. Measured, not scored.
    perclos_p80_60s: float = 0.0
    perclos_p80_coverage_s: float = 0.0
    blink_observed_s: float = 0.0  # seconds of eye data inside the blink window: what blink_rate divides by
