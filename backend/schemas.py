"""Request / response schemas.

Privacy rule: the backend only ever receives metadata. Every event payload is checked
in two layers and rejected (HTTP 422) if it could carry an image:
1. `find_image_data()` scans the raw JSON before any field parsing: forbidden key names
   (image, frame, photo, ...), data URIs, image file signatures in base64 (JPEG /9j/,
   PNG iVBORw0KGgo, ...) and any long base64-looking run.
2. Strict models: unknown fields are forbidden, every string is an enum or a short
   pattern-restricted id, numbers are bounded. There is no free-text field in which a
   blob could hide.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

Role = Literal["admin", "engineer", "manager", "driver"]
Reason = Literal[
    "microsleep",
    "drowsy_score",
    "off_road",
    "phone",
    "no_face",
    "trend",
    "blink_rate",
    "camera_lost",
    "camera_restored",  # system events: the device stopped / resumed monitoring
]
EventType = Literal["drowsiness", "distraction", "system"]
# Ids stay shorter than BASE64_RUN so a legitimate id can never look like base64.
Identifier = Field(pattern=r"^[A-Za-z0-9_.-]{1,48}$")

MAX_EVENTS_PER_BATCH = 100

FORBIDDEN_KEY_PARTS = (
    "image",
    "img",
    "frame",
    "photo",
    "picture",
    "snapshot",
    "thumbnail",
    "jpeg",
    "jpg",
    "png",
    "face_crop",
    "crop",
    "base64",
    "b64",
    "video",
    "blob",
)
DATA_URI = re.compile(r"data:[a-z]+/[a-z0-9.+-]+;base64,", re.IGNORECASE)
IMAGE_SIGNATURES = ("/9j/", "iVBORw0KGgo", "R0lGOD", "UklGR", "Qk0", "SUkq", "TU0AK")  # jpeg png gif webp bmp tiff
BASE64_RUN = re.compile(r"[A-Za-z0-9+/_-]{64,}={0,2}")


def find_image_data(obj: Any, path: str = "$") -> str | None:
    """Return a description of the first image-like content found in a JSON value, else None."""
    if isinstance(obj, (bytes, bytearray, memoryview)):
        return f"{path}: binary data"
    if isinstance(obj, dict):
        for key, value in obj.items():
            k = str(key).lower()
            if any(part in k for part in FORBIDDEN_KEY_PARTS):
                return f"{path}.{key}: forbidden field name"
            found = find_image_data(value, f"{path}.{key}")
            if found:
                return found
        return None
    if isinstance(obj, (list, tuple)):
        for i, value in enumerate(obj):
            found = find_image_data(value, f"{path}[{i}]")
            if found:
                return found
        return None
    if isinstance(obj, str):
        if DATA_URI.search(obj):
            return f"{path}: data URI"
        stripped = obj.strip()
        if len(stripped) >= 16 and stripped.startswith(IMAGE_SIGNATURES):
            return f"{path}: image signature"
        if BASE64_RUN.search(obj):
            return f"{path}: base64-like data"
    return None


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_max_length=64)


class EventMetrics(StrictModel):
    perclos_60s: float | None = Field(default=None, ge=0, le=1)
    closed_duration: float | None = Field(default=None, ge=0, le=3600)
    blink_rate: float | None = Field(default=None, ge=0, le=300)
    yawn_count_10min: int | None = Field(default=None, ge=0, le=1000)
    nod_count_5min: int | None = Field(default=None, ge=0, le=1000)
    off_road_duration: float | None = Field(default=None, ge=0, le=3600)
    phone_ratio_2s: float | None = Field(default=None, ge=0, le=1)


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


class EventBatch(StrictModel):
    device_id: str = Identifier
    events: list[EventIn] = Field(default_factory=list, max_length=MAX_EVENTS_PER_BATCH)
    feedback: list[FeedbackIn] = Field(default_factory=list, max_length=MAX_EVENTS_PER_BATCH)
    samples: list[SampleIn] = Field(default_factory=list, max_length=MAX_EVENTS_PER_BATCH)

    @model_validator(mode="before")
    @classmethod
    def reject_image_data(cls, data: Any) -> Any:
        problem = find_image_data(data)
        if problem:
            raise ValueError(f"image or base64 data is not accepted ({problem})")
        return data

    @model_validator(mode="after")
    def not_empty(self) -> EventBatch:
        if not (self.events or self.feedback or self.samples):
            raise ValueError("batch is empty")
        return self


class BatchResult(BaseModel):
    accepted: int
    duplicates: int
    feedback_applied: int = 0
    samples_accepted: int = 0


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


class SampleOut(BaseModel):
    ts: datetime
    trip_id: str
    device_id: str
    driver_id: str | None
    drowsy_score: float
    perclos_60s: float | None
    max_level: int


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
    "alert.fall_hold_s": (0.0, 30.0, "s"),
    "alert.cooldown_s.1": (0.0, 3600.0, "s"),
    "alert.cooldown_s.2": (0.0, 3600.0, "s"),
    "alert.cooldown_s.3": (0.0, 3600.0, "s"),
}
ThresholdKey = Literal[tuple(THRESHOLD_SPECS)]  # type: ignore[valid-type]


class ThresholdsIn(StrictModel):
    values: dict[ThresholdKey, float] = Field(min_length=1)

    @model_validator(mode="after")
    def within_bounds(self) -> ThresholdsIn:
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
