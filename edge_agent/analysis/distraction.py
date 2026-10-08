"""Block 8 - Distraction branch.

Per frame, from head pose + phone flag + whether the vehicle is moving, computes:
- off_road_duration: seconds the head has been continuously turned away from the road.
- phone_ratio_2s: fraction of recent samples (window `phone_window_s`) with a phone
  in the driver zone.
- no_face_duration: seconds without any face while the vehicle is not standing still (driver
  slumped out of view, camera covered). The risk engine turns a long one into "monitoring
  unavailable". It is the only number that runs on in a crawl below context.min_speed_kmh
  (`rolling`, M72): the rules below are off there, but a driver out of view is still not watched.

Anti false-positive rules:
- The branch is disabled while the vehicle is not moving (parked / red light: looking
  around or using the phone is fine). All state is reset. "Moving" comes from block 10
  (context.min_speed_kmh), so this branch and the risk engine always agree.
- Head angles are compared to an adaptive "looking at the road" baseline, so a camera
  that is not mounted straight in front of the driver does not look like distraction.
  The baseline only learns from on-road samples, so looking away never shifts it.
- Start-up calibration: during the first `baseline_calibrate_s` of driving with a face,
  the baseline is set to the median head pose (clamped to +-`baseline_calibrate_max_deg`)
  and nothing counts as off road. Without it, a camera mounted more than
  `yaw_off_road_deg` to the side looks "off road" on every frame, so the baseline never
  gets an on-road sample to learn from. Adaptation then stays within
  +-`baseline_max_deg` of the calibrated pose.
- Driver enrollment (block 6 stage) gives the driver's own road pose (`set_road_pose`):
  it replaces the start-up calibration, also when it comes mid-trip at a stop.
  Adaptation then stays within +-`baseline_max_deg` of it.
- Returning to the road must last `on_road_confirm_s` before the off-road timer resets,
  so a quick glance back does not hide a long distraction; a single noisy frame
  cannot reset it either.
- Face partly out of frame (FrameFeatures.face_reliable False): head pose is not trusted,
  handled like a lost pose (previous state kept), but it is not "no face".
- Turn signal (block 10 `turn_side`, held through its grace period): the yaw limit towards the
  signalled side grows by `turn_signal_extra_yaw_deg` (left signal: the driver may look further
  left before it counts as off road). The other side and pitch keep their limits, so looking
  right with the left signal on, or down at a phone, still counts. Which yaw sign is the
  driver's left is `left_yaw_sign` (unmirrored camera facing the driver: the driver's left is
  image right, yaw > 0). The baseline never learns from such widened-band samples.
- Face lost: keep the previous state (turning far away often loses the face, while an
  occlusion when looking forward should not start the timer).
- ... but not for ever (M72): "off road" is held for at most `pose_hold_s` after the last
  reliable head pose. After that nothing says where the driver looks, so the off-road state
  ends (a face partly out of the image used to keep an L2 alert up for as long as it stayed
  there). A driver looking behind (`turned_away`, below) is held for its own, longer time.
- Looking down with the head only partly bowed (block 7 `gaze_down`: head bowed, lids lowered,
  not firmly shut): the eyes are off the road even when the head is within the pitch limit, so the
  frame counts as off road. Such frames never teach the baseline.
- Turned away, then the face is lost (M38): the face disappears while the head was already off road
  and turned more than `turned_away_yaw_deg` (a reliable pose at most `turned_away_pose_age_s`
  old). That is a driver looking behind, not a covered camera: `turned_away` is set for at most
  `turned_away_max_s`, and the risk engine keeps the off-road rule instead of "monitoring
  unavailable" meanwhile. A face lost while looking ahead is unchanged (unavailable, no alert).
- Two frames more than `max_gap_s` apart (the loop stood still, the camera dropped frames): the
  driver was not seen in between, so the off-road, no-face, turned-away and gaze timers start again
  from the frame after the gap. Durations are differences of timestamps: without this, a glance on
  each side of a 3 s freeze read as one 3 s look away (L2). The baseline and the windows stay.

Measured only, never an alert (M38; to be proven on data first, docs/improvements.md):
- off_road_ratio / glance_count: share of the last `glance_window_s` spent off road, and how many
  times the driver looked away in it. Many short glances (1.5 s away, 0.5 s back, again) never reach
  the continuous off-road rule. Same "off road" as above (turn signal, gaze_down included); 0 until
  `glance_min_coverage_s` of driving is in the window. Cleared when the vehicle stops, on a driver
  change, and when monitoring becomes unavailable (`clear_glances`).
- gaze_down_deg / gaze_down_duration: where the eyes point below the road, as an angle = head pitch
  off the road pose + `gaze_iris_gain` x (iris_y off its usual value), and for how long it has stayed
  at or above `gaze_down_deg`. Looking at a phone on the lap or a low mount moves the eyes more than
  the head, so the head-pitch limit alone misses it. The usual iris_y is the median of the first
  `gaze_calibrate_s` of driving (after driver enrollment: the iris_y of its look-at-the-road step),
  then follows on-road frames like the head baseline. Frames block 7
  calls firmly shut are unknown (no iris to see): a gap up to `on_road_confirm_s` is bridged, a
  longer one ends the look. On 3MDAD (50 drivers) and own recordings it never held for 2 s on
  closed eyes or safe driving, and did on 14-26 % of the message sequences: too little for an
  alert, and on FL3D it also held inside real microsleeps (eval/results/gaze_3mdad.md).
- phone_kind: "call" / "text" / "unknown", the most frequent kind (block 4 `phone_kind`) among the
  phone samples of the `phone_window_s` window; None without a phone.

Pure logic on timestamps: no image, no clock, testable with fake sequences.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from typing import Any

import numpy as np

from edge_agent.config import config_from_dict
from edge_agent.perception.features import FrameFeatures


@dataclass(frozen=True)
class DistractionConfig:
    yaw_off_road_deg: float = 30.0
    pitch_down_off_road_deg: float = 20.0
    pitch_up_off_road_deg: float = 25.0
    on_road_confirm_s: float = 0.3
    max_gap_s: float = 0.5  # a longer gap between two frames ends the running timers
    pose_hold_s: float = 3.0  # "off road" held this long after the last reliable pose; 0 = no limit
    phone_window_s: float = 2.0
    baseline_adapt: bool = True
    baseline_tau_s: float = 30.0
    baseline_max_deg: float = 20.0
    baseline_yaw_deg: float = 0.0
    baseline_pitch_deg: float = 0.0
    baseline_calibrate_s: float = 0.0  # 0 = no start-up calibration
    baseline_calibrate_max_deg: float = 45.0
    turn_signal_extra_yaw_deg: float = 30.0
    left_yaw_sign: float = 1.0  # sign of yaw when the driver turns to their own left
    glance_window_s: float = 30.0  # off_road_ratio / glance_count window
    glance_min_coverage_s: float = 10.0  # less driving than this in the window: ratio 0
    glance_max_gap_s: float = 0.5  # a longer gap between frames adds no time to the window
    turned_away_yaw_deg: float = 45.0  # 0 = off
    turned_away_max_s: float = 10.0
    turned_away_pose_age_s: float = 0.5
    gaze_iris_gain: float = 100.0  # degrees of gaze per eye width of iris_y
    gaze_down_deg: float = 12.0  # gaze this far below the road pose = looking down (measured only); 0 = off
    gaze_calibrate_s: float = 5.0  # driving time whose median iris_y is the first "usual" value

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> DistractionConfig:
        return config_from_dict(cls, d, "distraction")


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
    no_face_duration: float = 0.0
    calibrating: bool = False  # start-up baseline calibration, off road not judged yet
    off_road_ratio: float = 0.0  # share of the glance window off road (measured only, no alert)
    glance_count: int = 0  # times the driver looked away in the glance window
    phone_kind: str | None = None  # call | text | unknown while a phone is in the driver zone
    turned_away: bool = False  # face lost right after a large head turn: still judged, not unavailable
    gaze_down_deg: float | None = None  # head pitch + iris, below the road pose (measured only, no alert)
    gaze_down_duration: float = 0.0  # seconds it has stayed at or above distraction.gaze.down_deg


class DistractionAnalyzer:
    def __init__(self, config: DistractionConfig | None = None) -> None:
        self.config = config or DistractionConfig()
        self.baseline_yaw = self.config.baseline_yaw_deg
        self.baseline_pitch = self.config.baseline_pitch_deg
        # Adaptation is clamped around this pose (the calibrated one once calibration is done).
        self._center_yaw, self._center_pitch = self.baseline_yaw, self.baseline_pitch
        self.calibrated = self.config.baseline_calibrate_s <= 0
        self._calib: list[tuple[float, float, float]] = []  # (t, yaw, pitch)
        self.baseline_iris: float | None = None  # the driver's usual iris_y (kept like the pose baseline)
        self._iris_calib: list[tuple[float, float]] = []  # (t, iris_y)
        self.reset()

    def reset(self) -> None:
        """Clear timers and windows (baseline is kept: it describes the camera mount)."""
        self._off_road = False
        self._off_road_since: float | None = None
        self._on_road_since: float | None = None
        self._no_face_since: float | None = None
        self._phone: deque[tuple[float, bool, str | None]] = deque()
        self._last_t: float | None = None
        self._pose_t: float | None = None  # last frame with a reliable head pose
        self._turned_pose_t: float | None = None  # last reliable pose, when it was a large head turn
        self._turned_since: float | None = None  # face lost right after such a pose
        self._gaze_since: float | None = None  # start of the current look down
        self._gaze_last: float | None = None  # last frame the gaze was seen down
        self.clear_glances()

    def _break_episodes(self) -> None:
        """Nothing was seen since the last frame (see module doc): the running timers start again."""
        self._off_road = False
        self._off_road_since = self._on_road_since = None
        self._no_face_since = None
        self._pose_t = None
        self._turned_pose_t = self._turned_since = None
        self._gaze_since = self._gaze_last = None

    def clear_glances(self) -> None:
        """Empty the glance window (also called by the pipeline when monitoring becomes unavailable)."""
        self._glance: deque[tuple[float, float, bool]] = deque()  # (t, seconds, off road)
        self._glance_starts: deque[float] = deque()
        # Running sums of the window (as block 7's Perclos): no pass over 30 s of samples per frame.
        self._glance_total = 0.0  # seconds in the window
        self._glance_off = 0.0  # ... of them off road
        self._glance_off_n = 0  # off-road samples in the window: none = exactly 0, whatever the rounding

    def _glances(self, t: float, dt: float, was_off_road: bool, known: bool) -> tuple[float, int]:
        cfg = self.config
        if known:
            d = min(dt, cfg.glance_max_gap_s)
            self._glance.append((t, d, self._off_road))
            self._glance_total += d
            if self._off_road:
                self._glance_off += d
                self._glance_off_n += 1
                if not was_off_road:
                    self._glance_starts.append(t)
        while self._glance and t - self._glance[0][0] > cfg.glance_window_s:
            _, d, off = self._glance.popleft()
            self._glance_total -= d
            if off:
                self._glance_off -= d
                self._glance_off_n -= 1
        while self._glance_starts and t - self._glance_starts[0] > cfg.glance_window_s:
            self._glance_starts.popleft()
        if not self._glance:
            self._glance_total = 0.0
        if self._glance_off_n == 0:
            self._glance_off = 0.0
        total = self._glance_total
        if total <= 0 or total < cfg.glance_min_coverage_s:
            return 0.0, len(self._glance_starts)
        return min(max(self._glance_off, 0.0) / total, 1.0), len(self._glance_starts)

    def _turned_away(self, t: float, face_found: bool) -> bool:
        cfg = self.config
        if face_found:
            self._turned_since = None
            return False
        if self._turned_since is None and self._no_face_since == t:  # the frame the face is lost
            recent = self._turned_pose_t is not None and t - self._turned_pose_t <= cfg.turned_away_pose_age_s
            if recent and self._off_road:
                self._turned_since = t
        return self._turned_since is not None and t - self._turned_since <= cfg.turned_away_max_s

    def _head_off_road(self, yaw_off: float, pitch_off: float, turn_side: str | None = None) -> bool:
        cfg = self.config
        yaw_limit = cfg.yaw_off_road_deg
        if turn_side in ("left", "right"):
            side_sign = cfg.left_yaw_sign if turn_side == "left" else -cfg.left_yaw_sign
            if yaw_off * side_sign > 0:  # looking towards the signalled side
                yaw_limit += cfg.turn_signal_extra_yaw_deg
        return (
            abs(yaw_off) > yaw_limit
            or pitch_off > cfg.pitch_down_off_road_deg
            or pitch_off < -cfg.pitch_up_off_road_deg
        )

    def _adapt_baseline(self, yaw: float, pitch: float, dt: float) -> None:
        cfg = self.config
        if not cfg.baseline_adapt or dt <= 0 or cfg.baseline_tau_s <= 0:
            return
        alpha = 1.0 - math.exp(-dt / cfg.baseline_tau_s)
        lim = cfg.baseline_max_deg
        yaw_new = self.baseline_yaw + alpha * (yaw - self.baseline_yaw)
        pitch_new = self.baseline_pitch + alpha * (pitch - self.baseline_pitch)
        self.baseline_yaw = min(max(yaw_new, self._center_yaw - lim), self._center_yaw + lim)
        self.baseline_pitch = min(max(pitch_new, self._center_pitch - lim), self._center_pitch + lim)

    def _calibrate(self, t: float, yaw: float, pitch: float) -> None:
        """Collect start-up samples; once `baseline_calibrate_s` is covered, set the baseline."""
        cfg = self.config
        self._calib.append((t, yaw, pitch))
        if t - self._calib[0][0] < cfg.baseline_calibrate_s:
            return
        lim = cfg.baseline_calibrate_max_deg
        yaw_med = float(np.median([y for _, y, _ in self._calib]))
        pitch_med = float(np.median([p for _, _, p in self._calib]))
        self.baseline_yaw = self._center_yaw = min(max(yaw_med, -lim), lim)
        self.baseline_pitch = self._center_pitch = min(max(pitch_med, -lim), lim)
        self.calibrated = True
        self._calib = []

    def set_road_pose(self, yaw: float, pitch: float, iris_y: float | None = None) -> None:
        """The enrolled "looking at the road" pose: the baseline and its centre from now on.
        iris_y: where the iris sat in that step; replaces the usual value learnt at start-up."""
        lim = self.config.baseline_calibrate_max_deg
        self.baseline_yaw = self._center_yaw = min(max(yaw, -lim), lim)
        self.baseline_pitch = self._center_pitch = min(max(pitch, -lim), lim)
        self.calibrated = True
        self._calib = []
        if iris_y is not None:
            self.baseline_iris = iris_y
            self._iris_calib = []

    def _gaze(
        self, t: float, dt: float, f: FrameFeatures, pitch_off: float | None, head_off: bool, shut: bool
    ) -> tuple[float | None, float]:
        """(gaze-down angle or None, seconds it has stayed down). Measured only."""
        cfg = self.config
        seen = cfg.gaze_down_deg > 0 and pitch_off is not None and f.iris_y is not None and not shut
        angle = None
        if seen and self.baseline_iris is None:
            self._iris_calib.append((t, f.iris_y))
            if t - self._iris_calib[0][0] >= cfg.gaze_calibrate_s:
                self.baseline_iris = float(np.median([v for _, v in self._iris_calib]))
                self._iris_calib = []
        elif seen:
            angle = pitch_off + cfg.gaze_iris_gain * (f.iris_y - self.baseline_iris)
            learn = cfg.baseline_adapt and dt > 0 and cfg.baseline_tau_s > 0
            if learn and not head_off and angle < cfg.gaze_down_deg:
                alpha = 1.0 - math.exp(-dt / cfg.baseline_tau_s)  # learns from on-road frames only
                self.baseline_iris += alpha * (f.iris_y - self.baseline_iris)
        if angle is not None and angle >= cfg.gaze_down_deg:
            if self._gaze_since is None:
                self._gaze_since = t
            self._gaze_last = t
        elif self._gaze_since is not None and t - self._gaze_last > cfg.on_road_confirm_s:
            self._gaze_since = self._gaze_last = None  # looked back, or not seen for too long
        return angle, (self._gaze_last - self._gaze_since if self._gaze_since is not None else 0.0)

    def _phone_ratio(self, t: float, phone_near_face: bool | None, kind: str | None = None) -> float:
        if phone_near_face is not None:  # None = no fresh detector result: not counted
            self._phone.append((t, phone_near_face, kind if phone_near_face else None))
        while self._phone and t - self._phone[0][0] > self.config.phone_window_s:
            self._phone.popleft()
        if not self._phone:
            return 0.0
        return sum(1 for _, p, _ in self._phone if p) / len(self._phone)

    def _phone_kind(self) -> str | None:
        """Most frequent kind among the window's phone samples; a tie, or no kind given, is "unknown"."""
        kinds = [k or "unknown" for _, p, k in self._phone if p]
        if not kinds:
            return None
        counts = {k: kinds.count(k) for k in set(kinds)}
        best = max(counts.values())
        winners = [k for k, n in counts.items() if n == best]
        return winners[0] if len(winners) == 1 else "unknown"

    def update(
        self,
        features: FrameFeatures,
        phone_near_face: bool | None,
        moving: bool,
        turn_side: str | None = None,
        gaze_down: bool = False,
        phone_kind: str | None = None,
        eyes_shut: bool = False,
        rolling: bool | None = None,
    ) -> DistractionState:
        """gaze_down: block 7 sees the driver looking down (head bowed, lids lowered): off road.
        phone_kind: how the phone is held on this frame (block 4), None when unknown / no phone.
        eyes_shut: block 7 counts this frame as firmly shut: the gaze angle is not measured on it.
        rolling: the vehicle is not standing still (block 10); None = the same as `moving`."""
        cfg = self.config
        t = features.timestamp
        dt = 0.0 if self._last_t is None else max(0.0, t - self._last_t)
        self._last_t = t
        if dt > cfg.max_gap_s:
            self._break_episodes()

        if not moving:
            # A crawl (rolling, not moving): the rules are off, the no-face time alone runs on.
            lost_since = None
            if rolling and not features.face_found:
                lost_since = t if self._no_face_since is None else self._no_face_since
            self.reset()
            self._last_t, self._no_face_since = t, lost_since
            no_face = 0.0 if lost_since is None else t - lost_since
            return DistractionState(
                t, False, False, 0.0, 0.0, None, None, self.baseline_yaw, self.baseline_pitch, no_face_duration=no_face
            )

        yaw_off = pitch_off = None
        has_pose = (
            features.face_found and features.face_reliable and features.yaw is not None and features.pitch is not None
        )
        if has_pose and not self.calibrated:
            self._calibrate(t, features.yaw, features.pitch)
        calibrating = not self.calibrated
        if has_pose:
            self._pose_t = t
        if calibrating:
            head_off = False  # baseline not known yet: never off road
        elif has_pose:
            yaw_off = features.yaw - self.baseline_yaw
            pitch_off = features.pitch - self.baseline_pitch
            head_off = self._head_off_road(yaw_off, pitch_off, turn_side) or gaze_down
            if not (self._head_off_road(yaw_off, pitch_off) or gaze_down):  # not widened band, not looking down
                self._adapt_baseline(features.yaw, features.pitch, dt)
            turned = cfg.turned_away_yaw_deg > 0 and head_off and abs(yaw_off) > cfg.turned_away_yaw_deg
            self._turned_pose_t = t if turned else None
        else:
            head_off = self._off_road  # face lost: hold previous state
            looking_behind = (  # held by turned_away, for its own time
                not features.face_found
                and self._turned_since is not None
                and t - self._turned_since <= cfg.turned_away_max_s
            )
            stale = self._pose_t is None or t - self._pose_t > cfg.pose_hold_s
            if head_off and cfg.pose_hold_s > 0 and stale and not looking_behind:
                head_off = self._off_road = False  # held too long: where the driver looks is not known
                self._off_road_since = self._on_road_since = None
        if features.face_found:
            self._no_face_since = None
        elif self._no_face_since is None:
            self._no_face_since = t

        was_off_road = self._off_road
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
        gaze_deg, gaze_s = self._gaze(t, dt, features, None if calibrating else pitch_off, head_off, eyes_shut)
        ratio, glances = self._glances(t, dt, was_off_road, known=not calibrating)
        phone_ratio = self._phone_ratio(t, phone_near_face, phone_kind)
        return DistractionState(
            timestamp=t,
            active=True,
            off_road=self._off_road,
            off_road_duration=duration,
            phone_ratio_2s=phone_ratio,
            yaw_offset=yaw_off,
            pitch_offset=pitch_off,
            baseline_yaw=self.baseline_yaw,
            baseline_pitch=self.baseline_pitch,
            no_face_duration=t - self._no_face_since if self._no_face_since is not None else 0.0,
            calibrating=calibrating,
            off_road_ratio=ratio,
            glance_count=glances,
            phone_kind=self._phone_kind(),
            turned_away=self._turned_away(t, features.face_found),
            gaze_down_deg=gaze_deg,
            gaze_down_duration=gaze_s,
        )
