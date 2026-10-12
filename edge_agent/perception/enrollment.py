"""Block 6 stage - Driver enrollment at the start of a trip.

While the vehicle stands still, the HUD first explains why the face is enrolled and what
happens to the data (`consent`); once the driver agrees, it guides three short steps and this
module learns the driver's own reference values from FrameFeatures:

  1 look_camera  "look straight at the camera"  look_camera_s  open-eye EAR, closed-mouth MAR,
                                                               resting brow height, face signature
  2 look_road    "look at the road ahead"       look_road_s    head pose when looking at the road
  3 close_eyes   "close your eyes until the beep" close_eyes_s closed-eye EAR

The result (`DriverProfile`) replaces what blocks 3, 7 and 8 otherwise guess on the road:
block 3 picks the driver among several faces by the signature, block 7 starts from the
driver's own open-eye EAR / closed-mouth MAR / head pose instead of defaults (and measures
blink speed between the driver's own closed and open EAR, brow raises above the resting
brow), block 8
skips its automatic 5 s road calibration.

Rules (enrollment is mandatory, but monitoring never waits for it):
- Consent first (`require_consent`): at a stop the status is `consent` until the driver answers on
  the HUD (`consent(True)`: the steps start; `consent(False)`, "Để sau": `later`, asked again at
  the next stop). Asked once per driver: after agreeing, an aborted or failed enrollment restarts
  the steps at the next stop without asking again. A new driver ("Đổi tài xế") is asked again.
- Only while the vehicle stands still (block 10). Driving off mid-way aborts the step;
  monitoring runs on the self-learnt baselines meanwhile, and the HUD asks the driver to
  enroll at the next stop.
- Each step only counts "good" frames (face fully in view, EAR trusted by block 5, pose
  known, and per step: facing the camera with the eyes open / eyes shut). Its clock
  pauses otherwise, so a blink or a glance away costs nothing but that time.
- When a step's samples are done they are checked (open EAR in the usual range and
  steady, mouth closed, road pose steady and not too far off). A failed check or
  `step_timeout_s` without finishing redoes that step only, with a hint. After
  `max_attempts` of one step enrollment gives up until the vehicle has moved and
  stopped again.
- One trip only: the profile lives in RAM and is never stored or sent. The backend only
  learns that the driver enrolled, how long it took and how many steps were redone.

Pure logic on timestamps: no image, no clock, testable with fake sequences.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from edge_agent.config import config_from_dict
from edge_agent.perception.features import FrameFeatures
from edge_agent.perception.landmarks import DriverAnchor

STEPS = ("look_camera", "look_road", "close_eyes")


@dataclass(frozen=True)
class EnrollmentConfig:
    enabled: bool = True
    require_consent: bool = True  # the driver agrees on the HUD before the steps start
    look_camera_s: float = 2.0
    look_road_s: float = 3.0
    close_eyes_s: float = 2.0
    road_settle_s: float = 1.0  # start of look_road not used: the eyes are still moving to the road
    step_timeout_s: float = 12.0
    max_attempts: int = 3
    max_gap_s: float = 0.5  # a longer gap between good frames adds no step time
    facing_max_deg: float = 20.0  # look_camera: |yaw| and |pitch| at most this
    eye_blink_shut: float = 0.5  # MediaPipe eyeBlink at or above this = eyes shut
    ear_spread_max: float = 0.15  # look_camera: (p90 - p10) / median of EAR at most this
    mar_closed_max: float = 0.25  # look_camera: mouth closed
    pose_spread_max_deg: float = 6.0  # look_road: p90 - p10 of yaw and of pitch at most this
    closed_ear_ratio: float = 0.6  # close_eyes: EAR below this x enrolled open EAR = shut
    reopen_grace_s: float = 2.0  # drowsiness alerts stay off this long after close_eyes (pipeline)

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> EnrollmentConfig:
        """Build the config from its section of thresholds.yaml; an unknown key is an error."""
        return config_from_dict(cls, d, "enrollment")


@dataclass(frozen=True)
class DriverProfile:
    """The driver's own reference values for this trip. RAM only, never sent."""

    ear_open: float
    ear_closed: float
    mar_closed: float
    road_yaw: float
    road_pitch: float
    anchor: DriverAnchor | None  # None when block 6 gave no face signature
    brow_neutral: float | None = None  # resting browOuterUp; None without blendshapes
    blink_closed: float | None = None  # eyeBlink with the eyes shut (step 3); None without blendshapes
    road_iris_y: float | None = None  # iris_y while looking at the road (step 2); None without iris landmarks


@dataclass(frozen=True)
class EnrollmentState:
    # off (disabled) | waiting (for a stop) | consent (asking the driver) | later (said "later",
    # until the next stop) | look_camera | look_road | close_eyes | done | failed
    status: str
    progress: float = 0.0  # 0..1 of the current step
    hint: str | None = None  # why the step is not moving on (the HUD words it)
    attempts: int = 0  # steps redone so far
    duration_s: float | None = None  # first step start -> done
    profile: DriverProfile | None = None
    events: tuple[str, ...] = ()  # "step_done", "enrolled", "failed"

    @property
    def enrolled(self) -> bool:
        """True once the driver has a profile."""
        return self.profile is not None

    @property
    def step_active(self) -> bool:
        """True while one of the enrollment steps is running."""
        return self.status in STEPS


def _spread(values: list[float]) -> float:
    lo, hi = np.percentile(values, [10, 90])
    return float(hi - lo)


class DriverEnrollment:
    def __init__(
        self,
        config: EnrollmentConfig | None = None,
        ear_min: float = 0.18,
        ear_max: float = 0.42,
        road_max_deg: float = 45.0,
    ) -> None:
        """ear_min / ear_max: plausible open-eye EAR (drowsiness.eye.baseline_min / _max);
        road_max_deg: farthest plausible road pose (distraction.baseline.calibrate_max_deg)."""
        self.config = config or EnrollmentConfig()
        self.ear_min, self.ear_max, self.road_max_deg = ear_min, ear_max, road_max_deg
        self.profile: DriverProfile | None = None
        self._status = "waiting" if self.config.enabled else "off"
        self._consented = not self.config.require_consent
        self._attempts_total = 0  # steps redone, whole trip
        self._tries = 0  # tries of the current step
        self._started_at: float | None = None
        self._duration: float | None = None
        self._values: dict[str, float] = {}  # results of the finished steps
        self._anchor: DriverAnchor | None = None
        self._brow: float | None = None
        self._blink_closed: float | None = None
        self._road_iris: float | None = None
        self._step_reset()

    def _step_reset(self) -> None:
        self._step_start: float | None = None
        self._good_s = 0.0
        self._last_good_t: float | None = None
        self._samples: list[FrameFeatures] = []
        self._retry_hint: str | None = None  # why this step is being redone, until it is done
        self._hint: str | None = None

    def _begin(self, step: str, t: float) -> None:
        self._status = step
        self._step_reset()
        self._step_start = t

    def _redo(self, t: float, hint: str, events: list[str]) -> None:
        """The step failed: do it again, or give up after max_attempts."""
        self._tries += 1
        self._attempts_total += 1
        if self._tries >= self.config.max_attempts:
            self._status = "failed"
            self._step_reset()
            self._hint = hint
            events.append("failed")
            return
        self._begin(self._status, t)
        self._retry_hint = hint

    # ------------------------------------------------------------------ driver's answer
    def consent(self, agree: bool) -> bool:
        """The driver's answer on the consent screen: agree (the steps start on the next frame) or
        "later" (asked again at the next stop). False when nothing was being asked."""
        if self._status != "consent":
            return False
        if agree:
            self._consented = True
            self._status = "waiting"
        else:
            self._status = "later"
        return True

    # ------------------------------------------------------------------ per frame
    def update(self, f: FrameFeatures, stationary: bool) -> EnrollmentState:
        """One frame of driver enrollment. The steps only run while the vehicle is stationary;
        driving off mid-way starts them again at the next stop."""
        cfg = self.config
        t = f.timestamp
        events: list[str] = []
        if self._status in ("off", "done"):
            return self._state(events)
        if self._status in ("failed", "later"):
            if not stationary:  # moved on: try again (failed) / ask again (later) at the next stop
                self._status, self._tries, self._values = "waiting", 0, {}
            return self._state(events)
        if not stationary:
            if self._status != "waiting":  # drove off mid-way: start over at the next stop
                self._status, self._tries, self._values = "waiting", 0, {}
                self._step_reset()
            self._hint = "stop_vehicle"
            return self._state(events)
        if self._status == "waiting" and not self._consented:
            self._status, self._hint = "consent", None
        if self._status == "consent":  # the HUD explains, the driver answers (consent())
            return self._state(events)
        if self._status == "waiting":
            self._started_at = t
            self._tries = 0
            self._begin(STEPS[0], t)

        good, hint = self._good_frame(f)
        if good:
            if self._last_good_t is not None:
                self._good_s += min(max(0.0, t - self._last_good_t), cfg.max_gap_s)
            self._last_good_t = t
            self._samples.append(f)
            self._hint = None
        else:
            self._last_good_t = None
            self._hint = hint

        if self._good_s >= self._needed_s():
            problem = self._finish_step()
            if problem is not None:
                self._redo(t, problem, events)
            else:
                events.append("step_done")
                nxt = STEPS.index(self._status) + 1
                if nxt < len(STEPS):
                    self._tries = 0
                    self._begin(STEPS[nxt], t)
                else:
                    self._complete(t, events)
        elif self._step_start is not None and t - self._step_start > cfg.step_timeout_s:
            self._redo(t, self._hint or "hold_still", events)
        return self._state(events)

    def _needed_s(self) -> float:
        cfg = self.config
        return {"look_camera": cfg.look_camera_s, "look_road": cfg.look_road_s, "close_eyes": cfg.close_eyes_s}[
            self._status
        ]

    def _good_frame(self, f: FrameFeatures) -> tuple[bool, str | None]:
        cfg = self.config
        if not (f.face_found and f.face_reliable):
            return False, "face_not_found"
        step = self._status
        if step == "look_road":
            if self._step_start is not None and f.timestamp - self._step_start < cfg.road_settle_s:
                return False, None
            return (f.yaw is not None and f.pitch is not None), "hold_still"
        if f.ear is None or f.eye_cnn_reason is not None:  # block 5: EAR not trusted (dark, IR, glare)
            return False, "too_dark"
        if step == "look_camera":
            if f.yaw is None or f.pitch is None or max(abs(f.yaw), abs(f.pitch)) > cfg.facing_max_deg:
                return False, "look_camera"
            if f.eye_blink is not None and f.eye_blink >= cfg.eye_blink_shut:
                return False, None  # a blink: just skip the frame
            return True, None
        # close_eyes
        shut = f.ear < cfg.closed_ear_ratio * self._values["ear_open"]
        if f.eye_blink is not None:
            shut = shut and f.eye_blink >= cfg.eye_blink_shut
        return shut, "close_eyes"

    def _finish_step(self) -> str | None:
        """Check the step's samples and keep its values; a hint when they are not usable."""
        cfg, s = self.config, self._samples
        if self._status == "look_camera":
            ears = [f.ear for f in s if f.ear is not None]
            mars = [f.mar for f in s if f.mar is not None]
            ear = float(np.median(ears))
            if not self.ear_min <= ear <= self.ear_max or _spread(ears) > cfg.ear_spread_max * ear:
                return "open_eyes"
            mar = float(np.median(mars)) if mars else 0.0
            if mar > cfg.mar_closed_max:
                return "close_mouth"
            self._values.update(ear_open=ear, mar_closed=mar)
            brows = [f.brow_up for f in s if f.brow_up is not None]
            self._brow = float(np.median(brows)) if brows else None
            self._anchor = self._make_anchor(s)
            return None
        if self._status == "look_road":
            yaws = [f.yaw for f in s if f.yaw is not None]
            pitches = [f.pitch for f in s if f.pitch is not None]
            yaw, pitch = float(np.median(yaws)), float(np.median(pitches))
            if max(_spread(yaws), _spread(pitches)) > cfg.pose_spread_max_deg:
                return "hold_still"
            if max(abs(yaw), abs(pitch)) > self.road_max_deg:
                return "look_road"
            self._values.update(road_yaw=yaw, road_pitch=pitch)
            # Where the iris sits when this driver looks at the road (block 8's gaze-down angle); blinks left out.
            iris = [
                f.iris_y
                for f in s
                if f.iris_y is not None and (f.eye_blink is None or f.eye_blink < cfg.eye_blink_shut)
            ]
            self._road_iris = float(np.median(iris)) if iris else None
            return None
        self._values["ear_closed"] = float(np.median([f.ear for f in s if f.ear is not None]))
        blinks = [f.eye_blink for f in s if f.eye_blink is not None]
        self._blink_closed = float(np.median(blinks)) if blinks else None
        return None

    @staticmethod
    def _make_anchor(samples: list[FrameFeatures]) -> DriverAnchor | None:
        with_shape = [f for f in samples if f.face_shape and f.face_center and f.face_size]
        if not with_shape:
            return None
        return DriverAnchor(
            shape=tuple(float(v) for v in np.median([f.face_shape for f in with_shape], axis=0)),
            center=tuple(float(v) for v in np.median([f.face_center for f in with_shape], axis=0)),  # type: ignore[arg-type]
            size=float(np.median([f.face_size for f in with_shape])),
        )

    def _complete(self, t: float, events: list[str]) -> None:
        v = self._values
        self.profile = DriverProfile(
            ear_open=v["ear_open"],
            ear_closed=v["ear_closed"],
            mar_closed=v["mar_closed"],
            road_yaw=v["road_yaw"],
            road_pitch=v["road_pitch"],
            anchor=self._anchor,
            brow_neutral=self._brow,
            blink_closed=self._blink_closed,
            road_iris_y=self._road_iris,
        )
        self._status = "done"
        self._duration = t - self._started_at if self._started_at is not None else None
        self._step_reset()
        events.append("enrolled")

    def _state(self, events: list[str]) -> EnrollmentState:
        progress = 0.0
        if self._status in STEPS:
            progress = min(self._good_s / self._needed_s(), 1.0)
        elif self._status == "done":
            progress = 1.0
        return EnrollmentState(
            status=self._status,
            progress=progress,
            hint=None if self._status == "done" else (self._hint or self._retry_hint),
            attempts=self._attempts_total,
            duration_s=self._duration,
            profile=self.profile,
            events=tuple(events),
        )
