"""Request / response schemas.

Privacy rule: the backend only ever receives metadata. Every event payload is checked
in two layers and rejected (HTTP 422) if it could carry an image:
1. `find_image_data()` (edge_agent/io/metadata_guard.py, the same rules the device applies
   before sending) scans the raw JSON before any field parsing: forbidden key names
   (image, frame, photo, ...), data URIs, image file signatures in base64 (JPEG /9j/,
   PNG iVBORw0KGgo, ...) and any long base64-looking run.
2. Strict models: unknown fields are forbidden, every string is an enum or a short
   pattern-restricted id, numbers are bounded. There is no free-text field in which a
   blob could hide.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

# One list of forbidden words and one scanner for the device, the page and this backend (M84).
from edge_agent.io.metadata_guard import find_image_data

Role = Literal["admin", "engineer", "manager", "driver"]
Reason = Literal[
    "microsleep",
    "drowsy_score",
    "off_road",
    "phone",
    "no_face",  # v1 only (now monitoring_unavailable, no alert): kept for events already stored
    "trend",
    "blink_rate",
    "repeated_l1",  # M32: added to an L1 alert raised as L2 because it kept coming back
    "unresponsive",  # M44: eyes still closed seconds into the L3 alarm
    "repeated_l3",  # M44: added to an L3 alert that keeps coming back
    "no_answer",  # M44, system event: "Bạn còn ở đó không?" was not answered
    "config_applied",  # M47, system events: reloaded thresholds applied while parked / refused
    "config_refused",
    "camera_lost",
    "camera_restored",  # system events: the device stopped / resumed monitoring
    "driver_enrolled",  # system event: from now on judged with the driver's own baselines
    "monitoring_unavailable",  # system events: face lost while moving (FR-6) / back
    "monitoring_restored",
    "driver_changed",  # system event: "Đổi tài xế" on the HUD, a new driver enrolls
    "vehicle_signal_lost",  # system events: vehicle link (speed / turn signal) lost while driving / back
    "vehicle_signal_restored",
    "agent_error",  # system events (M28): frames keep failing, not monitored / processing again
    "agent_recovered",
    "low_fps",  # system events (M28): too slow for a while, alerts may be late / back up
    "fps_restored",
    "phone_detection_lost",  # system events (M50): the phone detector gives no fresh results / again
    "phone_detection_restored",
    "road_pose_recalibrated",  # system event (M80): block 8 took a pose held off road for long as the road pose
]
EventType = Literal["drowsiness", "distraction", "system"]
# Ids stay shorter than metadata_guard.BASE64_RUN so a legitimate id can never look like base64.
Identifier = Field(pattern=r"^[A-Za-z0-9_.-]{1,48}$")

MAX_EVENTS_PER_BATCH = 100


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_max_length=64)


# Why monitoring is unavailable (edge_agent/decision/risk_engine.py unavailable_reason).
UnavailableCause = Literal["no_face", "camera_blocked", "bad_angle", "low_light", "glare", "blur", "slow_loop"]


class EventMetrics(StrictModel):
    perclos_60s: float | None = Field(default=None, ge=0, le=1)
    perclos_p80: float | None = Field(default=None, ge=0, le=1)  # M40: P80 definition, measured only
    closed_duration: float | None = Field(default=None, ge=0, le=3600)
    blink_rate: float | None = Field(default=None, ge=0, le=300)
    yawn_count_10min: int | None = Field(default=None, ge=0, le=1000)
    nod_count_5min: int | None = Field(default=None, ge=0, le=1000)
    off_road_duration: float | None = Field(default=None, ge=0, le=3600)
    phone_ratio_2s: float | None = Field(default=None, ge=0, le=1)
    phone_kind: Literal["call", "text", "unknown"] | None = None  # M38: how the phone is held
    off_road_ratio: float | None = Field(default=None, ge=0, le=1)  # M38: share of the glance window off road
    glance_count: int | None = Field(default=None, ge=0, le=10_000)
    blink_time_frac: float | None = Field(default=None, ge=0, le=1)  # v2 slow blinks
    reopen_ratio: float | None = Field(default=None, ge=0, le=100)  # v2 slow blinks
    brow_raise_count_5min: int | None = Field(default=None, ge=0, le=1000)  # v2 brow raise
    enrolled: int | None = Field(default=None, ge=0, le=1)  # driver enrollment done before this alert
    enroll_s: float | None = Field(default=None, ge=0, le=3600)  # driver_enrolled: time it took
    enroll_redo: int | None = Field(default=None, ge=0, le=1000)  # driver_enrolled: steps redone
    fps: float | None = Field(default=None, ge=0, le=1000)  # low_fps / fps_restored: smoothed FPS
    phone_unknown_ratio: float | None = Field(default=None, ge=0, le=1)  # M50, phone_detection_lost / restored
    cause: UnavailableCause | None = None  # M43, monitoring_unavailable: why (older agents: face lost)


EventTag = Literal["simulated", "forced"]


class VersionInfo(StrictModel):
    """What the device runs (edge_agent/version.py): app version, thresholds version, model fingerprints."""

    app: str = Field(pattern=r"^[A-Za-z0-9_.+-]{1,32}$")
    thresholds_version: int = Field(ge=0, le=10_000_000)  # 0 = the device's own thresholds.yaml only
    thresholds_ignored: bool = False  # tuned thresholds were fetched but refused as inconsistent
    models: dict[str, str] = Field(default_factory=dict, max_length=8)  # section -> short SHA-256

    @model_validator(mode="after")
    def models_are_short_hex(self) -> VersionInfo:
        """Validator: every model fingerprint is a short name mapped to 8-16 hex characters."""
        for name, digest in self.models.items():
            if not re.fullmatch(r"[a-z0-9_]{1,32}", name) or not re.fullmatch(r"[0-9a-f]{8,16}", digest):
                raise ValueError("models must map a section name to 8-16 hex characters")
        return self


class EventIn(StrictModel):
    event_id: UUID
    ts: AwareDatetime  # timezone required
    trip_id: str = Identifier
    type: EventType
    level: int = Field(ge=0, le=3)
    reasons: list[Reason] = Field(max_length=6)
    drowsy_score: float = Field(ge=0, le=100)
    distraction_score: float = Field(ge=0, le=100)
    speed_kmh: float | None = Field(default=None, ge=0, le=400)
    metrics: EventMetrics = Field(default_factory=EventMetrics)
    # M41 (agents older than it send neither). simulated: the vehicle signals were simulated;
    # forced: a state set by hand (PRD FR-17), stored but never counted in any statistic.
    tags: list[EventTag] = Field(default_factory=list, max_length=2)
    versions: VersionInfo | None = None


class FeedbackIn(StrictModel):
    """Driver pressed "false alarm" on the in-car HUD for an alert."""

    event_id: UUID
    verdict: Literal["false_alarm"]
    ts: AwareDatetime


class SampleIn(StrictModel):
    """One point of the fatigue timeline: drowsy_score averaged over one minute."""

    sample_id: UUID
    ts: AwareDatetime  # end of the minute
    trip_id: str = Identifier
    drowsy_score: float = Field(ge=0, le=100)
    perclos_60s: float | None = Field(default=None, ge=0, le=1)
    max_level: int = Field(ge=0, le=3)
    off_road_ratio: float | None = Field(default=None, ge=0, le=1)  # M38; older agents omit it


Rating = Literal["good", "attention", "risk"]
RatingReason = Literal["microsleep", "frequent_alerts", "tired_minutes", "low_coverage"]
SuggestionCode = Literal[
    "rest_now", "rest_after", "regular_breaks", "phone_away", "eyes_on_road", "check_camera", "enroll"
]
MAX_TRIP_MINUTES = 24 * 60


class MinuteIn(StrictModel):
    minute: int = Field(ge=0, le=MAX_TRIP_MINUTES)
    drowsy_score: float = Field(ge=0, le=100)
    max_level: int = Field(ge=0, le=3)
    moving: bool


class SuggestionIn(StrictModel):
    code: SuggestionCode
    minutes: int | None = Field(default=None, ge=0, le=MAX_TRIP_MINUTES)


class TripSummaryIn(StrictModel):
    """End-of-trip summary built on the device (edge_agent/decision/trip_summary.py). Numbers only."""

    trip_id: str = Identifier
    started_at: AwareDatetime
    ended_at: AwareDatetime
    duration_s: float = Field(ge=0, le=MAX_TRIP_MINUTES * 60)
    driving_s: float = Field(ge=0, le=MAX_TRIP_MINUTES * 60)
    stopped_s: float = Field(ge=0, le=MAX_TRIP_MINUTES * 60)
    rests: int = Field(ge=0, le=1000)
    longest_drive_s: float = Field(ge=0, le=MAX_TRIP_MINUTES * 60)
    avg_speed_kmh: float | None = Field(default=None, ge=0, le=400)
    speed_source: Literal["simulated", "can"]
    alerts_by_level: dict[Literal["1", "2", "3"], int]
    alerts_by_reason: dict[Reason, int] = Field(max_length=16)
    false_alarms: int = Field(ge=0, le=100_000)
    microsleeps: int = Field(ge=0, le=100_000)
    longest_closure_s: float = Field(ge=0, le=3600)
    yawns: int = Field(ge=0, le=100_000)
    nods: int = Field(ge=0, le=100_000)
    brow_raises: int = Field(ge=0, le=100_000)
    off_road_s: float = Field(ge=0, le=MAX_TRIP_MINUTES * 60)
    phone_s: float = Field(ge=0, le=MAX_TRIP_MINUTES * 60)
    # M38 (measured only); agents older than it omit them.
    phone_call_s: float = Field(default=0.0, ge=0, le=MAX_TRIP_MINUTES * 60)
    phone_text_s: float = Field(default=0.0, ge=0, le=MAX_TRIP_MINUTES * 60)
    glances: int = Field(default=0, ge=0, le=1_000_000)
    off_road_ratio_max: float = Field(default=0.0, ge=0, le=1)
    turned_away_s: float = Field(default=0.0, ge=0, le=MAX_TRIP_MINUTES * 60)
    monitored_frac: float | None = Field(default=None, ge=0, le=1)
    unavailable_s: float = Field(ge=0, le=MAX_TRIP_MINUTES * 60)
    # M43: seconds per reason; agents older than it omit it.
    unavailable_by_cause: dict[UnavailableCause, float] = Field(default_factory=dict, max_length=8)
    camera_lost_s: float = Field(ge=0, le=MAX_TRIP_MINUTES * 60)
    vehicle_signal_lost_s: float = Field(default=0.0, ge=0, le=MAX_TRIP_MINUTES * 60)  # M26; older agents omit it
    enrolled: bool
    driver_changes: int = Field(default=0, ge=0, le=1000)
    drowsy_mean: float = Field(ge=0, le=100)
    drowsy_p90: float = Field(ge=0, le=100)
    drowsy_max: float = Field(ge=0, le=100)
    first_tired_min: int | None = Field(default=None, ge=0, le=MAX_TRIP_MINUTES)
    score_l1: float = Field(ge=0, le=100)
    score_l2: float = Field(ge=0, le=100)
    rating: Rating
    rating_reasons: list[RatingReason] = Field(max_length=8)
    suggestions: list[SuggestionIn] = Field(max_length=10)
    minutes: list[MinuteIn] = Field(max_length=MAX_TRIP_MINUTES + 1)


# Monitoring state of a heartbeat (edge_agent.runtime.MONITOR_STATES).
MonitorState = Literal["monitoring", "unavailable", "camera_lost", "stalled", "error", "ended"]


# Stages of the loop a device may time (edge_agent/io/publisher.py PERF_STAGES).
PerfStage = Literal["camera_lag", "capture", "landmarks", "measure", "yolo_prep", "python", "total", "yolo", "yolo_age"]
PerfMs = Field(ge=0, le=600_000)


class StageMsIn(StrictModel):
    p50: float = PerfMs
    p95: float = PerfMs
    max: float = PerfMs


class PerfIn(StrictModel):
    """The loop's own timings over its last seconds (M49): milliseconds per stage, no measurement of the driver."""

    samples: int = Field(ge=1, le=100_000)  # processed frames behind the numbers
    stages_ms: dict[PerfStage, StageMsIn] = Field(min_length=1, max_length=9)
    landmarks_delegate: Literal["GPU", "CPU"] | None = None
    gpu: Literal["hardware", "software", "none"] | None = None  # M51: what draws WebGL on the page
    yolo_threads: int | None = Field(default=None, ge=1, le=64)
    yolo_provider: Literal["webgpu", "wasm"] | None = None  # M67: where the page runs the phone detector
    camera_delivered: int | None = Field(default=None, ge=0, le=10_000_000)
    camera_dropped: int | None = Field(default=None, ge=0, le=10_000_000)


class HeartbeatIn(StrictModel):
    """Still alive (M33): the trip, the monitoring state, whether the vehicle moves. No position."""

    ts: AwareDatetime
    trip_id: str = Identifier
    state: MonitorState
    moving: bool | None = None  # None: speed unknown
    versions: VersionInfo | None = None  # M41; older agents send none
    perf: PerfIn | None = None  # M49; only agents that time their loop send it


class EventBatch(StrictModel):
    device_id: str = Identifier
    heartbeat: HeartbeatIn | None = None  # agents older than M33 send none
    events: list[EventIn] = Field(default_factory=list, max_length=MAX_EVENTS_PER_BATCH)
    feedback: list[FeedbackIn] = Field(default_factory=list, max_length=MAX_EVENTS_PER_BATCH)
    samples: list[SampleIn] = Field(default_factory=list, max_length=MAX_EVENTS_PER_BATCH)
    summaries: list[TripSummaryIn] = Field(default_factory=list, max_length=5)

    @model_validator(mode="before")
    @classmethod
    def reject_image_data(cls, data: Any) -> Any:
        """Validator: refuse a batch that carries image or base64 data anywhere."""
        problem = find_image_data(data)
        if problem:
            raise ValueError(f"image or base64 data is not accepted ({problem})")
        return data

    @model_validator(mode="after")
    def not_empty(self) -> EventBatch:
        """Validator: a batch carries at least one record or a heartbeat."""
        if not (self.events or self.feedback or self.samples or self.summaries or self.heartbeat):
            raise ValueError("batch is empty")
        return self


class BatchResult(BaseModel):
    accepted: int
    duplicates: int
    conflicts: int = 0  # events whose event_id another device already used: not stored
    feedback_applied: int = 0
    samples_accepted: int = 0
    summaries_accepted: int = 0


class EventOut(BaseModel):
    event_id: str
    device_id: str
    driver_id: str | None
    trip_id: str
    ts: datetime
    type: EventType
    level: int
    reasons: list[str]
    drowsy_score: float
    distraction_score: float
    speed_kmh: float | None
    metrics: dict[str, Any]
    received_at: datetime
    feedback: str | None = None
    feedback_at: datetime | None = None
    tags: list[str] = []
    versions: dict[str, Any] | None = None


class SampleOut(BaseModel):
    ts: datetime
    trip_id: str
    device_id: str
    driver_id: str | None
    drowsy_score: float
    perclos_60s: float | None
    max_level: int
    off_road_ratio: float | None = None


class TimelineOut(BaseModel):
    samples: list[SampleOut]
    events: list[EventOut]


class TripOut(BaseModel):
    trip_id: str
    device_id: str
    driver_id: str | None
    start: datetime
    end: datetime
    events: int
    max_level: int


class TripReportOut(BaseModel):
    """A trip summary as stored, with who sent it and whether a higher role has looked at it."""

    trip_id: str
    device_id: str
    driver_id: str | None
    received_at: datetime
    rating: Rating
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = None  # M105: what the reviewer tells the driver ("Lưu ý")
    summary: dict[str, Any]


class TripReviewIn(StrictModel):
    """POST /api/v1/trip-reports/{device}/{trip}/review (M105): an optional note for the driver. Empty text
    clears it; no body or no note keeps the one already there."""

    note: str | None = Field(default=None, max_length=500)


FleetStatus = Literal["online", "offline", "ended", "never"]


class FleetEventOut(BaseModel):
    ts: datetime
    type: EventType
    level: int
    reasons: list[str]
    event_id: str | None = None  # set on `urgent`: the page beeps once per event


class FleetDeviceOut(BaseModel):
    """One vehicle in the fleet overview (M33). status: online = heard from within the offline limit;
    offline = went quiet without ending its trip; ended = the trip was ended; never = registered,
    never heard from. state / moving / trip_id: from its last heartbeat."""

    device_id: str
    driver_id: str | None
    status: FleetStatus
    state: MonitorState | None
    moving: bool | None
    trip_id: str | None
    last_seen: datetime | None
    alerts_by_level: dict[int, int]  # alerts (not system events) in the asked period
    last_event: FleetEventOut | None  # newest event in the asked period, system events included
    # M44: newest L3 / unresponsive / repeated_l3 / no_answer of the running trip within
    # DG_FLEET_URGENT_WINDOW_S, while the device is online. None = nothing needs attention now.
    urgent: FleetEventOut | None = None
    # M41: what the device said it runs in its last heartbeat (None: an agent older than M41), and
    # whether that is the newest thresholds version (None when it reported none).
    versions: dict[str, Any] | None = None
    thresholds_current: bool | None = None
    thresholds_latest: int = 0
    # M49: the loop timings of its last heartbeat that carried any (PerfIn); None: never sent.
    perf: dict[str, Any] | None = None
    # M82: server time minus the `ts` of its last heartbeat, seconds (positive: the device's clock is
    # behind), and whether that is past DG_CLOCK_SKEW_WARN_S: the times this device reports (`ts` of
    # events, the trip id) are then not to be trusted. None: no heartbeat yet.
    clock_skew_s: float | None = None
    clock_wrong: bool | None = None


class PolicyOut(BaseModel):
    """Data policy numbers the pages show (docs/data-policy.md). 0 days = kept until deleted by hand."""

    retention_events_days: int
    retention_summaries_days: int
    retention_access_log_days: int = 0


# A driver's own data (M48, docs/data-policy.md section 5).
DeletionStatus = Literal["pending", "done", "refused"]
# Why an admin refuses a deletion request. Codes, not free text: no place for anything else to be typed.
RefusalReason = Literal["legal_hold", "incident_open", "duplicate", "other"]


class DeletionRequestOut(BaseModel):
    id: int
    driver_id: str
    requested_by: str
    requested_at: datetime
    status: DeletionStatus
    handled_by: str | None = None
    handled_at: datetime | None = None
    reason: RefusalReason | None = None


class DeletionDecisionIn(StrictModel):
    action: Literal["delete", "refuse"]
    reason: RefusalReason | None = None

    @model_validator(mode="after")
    def refusal_names_a_reason(self) -> DeletionDecisionIn:
        """Validator: a refusal names its reason, a deletion takes none."""
        if (self.action == "refuse") != (self.reason is not None):
            raise ValueError("a refusal needs a reason, a deletion takes none")
        return self


# Access log (M41): who looked at whose data, who changed what. Append-only.
AuditAction = Literal[
    "read_events",
    "read_timeline",
    "read_trips",
    "read_stats",
    "read_fleet",
    "read_trip_reports",
    "read_trip_report",
    "review_trip_report",
    "read_access_log",
    "update_thresholds",
    "rollout_thresholds",  # M47: a version given to the whole fleet (a trial promoted, or a roll back)
    "create_user",
    "create_device",
    "purge_expired",
    "delete_driver_data",
    "refuse_deletion",  # M48: a driver's deletion request was refused (the reason is in the detail)
    "delete_user",
]


class AccessLogOut(BaseModel):
    """One access-log row. driver_id / device_id None = not limited to one (the whole fleet)."""

    ts: datetime
    username: str
    role: str
    action: str
    driver_id: str | None
    device_id: str | None
    detail: str | None


class ReasonStats(BaseModel):
    total: int
    false_alarms: int


class StatsOut(BaseModel):
    total: int
    false_alarms: int
    by_level: dict[int, int]
    by_reason: dict[str, ReasonStats]


class LoginIn(StrictModel):
    username: str = Identifier
    password: str = Field(min_length=1, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role
    expires_in: int


class UserIn(StrictModel):
    username: str = Identifier
    password: str = Field(min_length=8, max_length=128)
    role: Role
    driver_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_.-]{1,48}$")

    @model_validator(mode="after")
    def driver_needs_driver_id(self) -> UserIn:
        """Validator: a driver account is bound to a driver_id."""
        if self.role == "driver" and not self.driver_id:
            raise ValueError("a driver account needs driver_id")
        return self


class UserOut(BaseModel):
    username: str
    role: Role
    driver_id: str | None


class DeviceIn(StrictModel):
    device_id: str = Identifier
    driver_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_.-]{1,48}$")


class DeviceOut(BaseModel):
    device_id: str
    driver_id: str | None
    device_key: str | None = None  # only returned once, at creation


# --------------------------------------------------------------------------- thresholds
# Engineers may tune only these keys (dotted paths into config/thresholds.yaml), within bounds.
THRESHOLD_SPECS: dict[str, tuple[float, float, str]] = {
    "risk.microsleep_l3_s": (0.5, 5.0, "s"),
    "risk.drowsy.l1": (5.0, 100.0, "score"),
    "risk.drowsy.l2": (5.0, 100.0, "score"),
    "risk.distraction.off_road_s": (0.5, 10.0, "s"),
    "risk.distraction.off_road_high_speed_s": (0.5, 10.0, "s"),
    "risk.distraction.phone_ratio": (0.1, 1.0, "ratio"),
    "drowsiness.microsleep_min_s": (0.3, 5.0, "s"),
    "drowsiness.perclos_drowsy": (0.05, 0.5, "ratio"),
    "drowsiness.yawn.min_s": (0.5, 6.0, "s"),
    "drowsiness.nod.max_s": (0.5, 5.0, "s"),
    "distraction.yaw_off_road_deg": (10.0, 90.0, "deg"),
    "distraction.turn_signal_extra_yaw_deg": (0.0, 60.0, "deg"),
    "alert.fall_hold_s": (0.0, 30.0, "s"),
    "alert.cooldown_s.1": (0.0, 3600.0, "s"),
    "alert.cooldown_s.2": (0.0, 3600.0, "s"),
    "alert.cooldown_s.3": (0.0, 3600.0, "s"),
}
ThresholdKey = Literal[tuple(THRESHOLD_SPECS)]  # type: ignore[valid-type]


class ThresholdsIn(StrictModel):
    values: dict[ThresholdKey, float] = Field(min_length=1)
    # M47: only these devices get the new version (a trial group); the fleet keeps its version until
    # the new one is rolled out. Empty = the whole fleet at once, as before.
    trial_devices: list[Annotated[str, Identifier]] = Field(default_factory=list, max_length=200)

    @model_validator(mode="after")
    def within_bounds(self) -> ThresholdsIn:
        """Validator: every threshold lies within the bounds of THRESHOLD_SPECS."""
        for key, value in self.values.items():
            lo, hi, _ = THRESHOLD_SPECS[key]
            if not lo <= value <= hi:
                raise ValueError(f"{key} must be between {lo} and {hi}")
        return self


class ThresholdSpec(BaseModel):
    min: float
    max: float
    unit: str


class ThresholdsOut(BaseModel):
    version: int  # 0 = no override yet, the device uses its own thresholds.yaml
    values: dict[str, float]
    updated_by: str | None
    updated_at: datetime | None
    specs: dict[str, ThresholdSpec]
    # M47: the version every device without a pin runs. On the dashboard `version` is the newest one
    # (what an edit builds on), which may be a trial not yet given to the fleet.
    fleet_version: int = 0


class RolloutIn(StrictModel):
    """Give an existing version to the whole fleet: a trial that went well, or an older one (roll back)."""

    version: int = Field(ge=1, le=10_000_000)


class ThresholdVersionOut(BaseModel):
    version: int
    values: dict[str, float]
    updated_by: str
    updated_at: datetime
    changed: list[str]  # keys whose value differs from the version before
    fleet: bool  # the fleet's version now
    pinned_devices: list[str]  # devices given this version for a trial
    running_devices: list[str]  # devices whose last heartbeat reported it
    alerts: int  # alerts raised under it (not system events, not forced)
    false_alarms: int  # ... of which the driver marked "false alarm"


# Web driving controls (M31, backend/drive_link.py): numbers only, no user data.
DRIVE_CODE_PATTERN = r"^[A-Z0-9]{6}$"  # pairing code shown by #/live


class DriveSignalIn(StrictModel):
    speed_kmh: float = Field(ge=0, le=250)
    turn_signal: Literal["left", "right"] | None = None


class DriveSignalOut(BaseModel):
    speed_kmh: float
    turn_signal: Literal["left", "right"] | None
    age_s: float  # seconds since the remote page last sent it
