"""DriverGuard backend: receives event metadata from edge devices, serves it to 3 roles.

    uvicorn backend.app:app --port 8100         (settings from DG_* env vars / .env)
    python -m backend.manage create-user admin --role admin

Roles:
- admin:    manage users and devices, everything below
- engineer: read all events / timelines / stats, tune thresholds
- manager:  read all events / timelines / stats (fleet), thresholds read-only
- driver:   read only their own events and timeline
Edge devices are not users: they post events, false-alarm feedback and fatigue samples with
their X-Device-Key, and fetch the tuned thresholds.

Access log (M41): every read of drivers' data by a higher role, every thresholds change, account /
device creation and data deletion is appended to `access_log` (who, role, what, whose data).
Admins read all of it; a driver reads who looked at their own data. A driver reading their own
data is not logged. The same read by the same account is logged once per DG_AUDIT_DEDUPE_S.
"""

from __future__ import annotations

import json
import logging
import secrets
import sqlite3
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, Path, Query, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ValidationError

from backend import db
from backend.drive_link import DriveLinks
from backend.schemas import (
    DRIVE_CODE_PATTERN,
    THRESHOLD_SPECS,
    AccessLogOut,
    BatchResult,
    DeletionDecisionIn,
    DeletionRequestOut,
    DeviceIn,
    DeviceOut,
    DriveSignalIn,
    DriveSignalOut,
    EventBatch,
    EventOut,
    FleetDeviceOut,
    LoginIn,
    PolicyOut,
    RolloutIn,
    StatsOut,
    ThresholdsIn,
    ThresholdsOut,
    ThresholdSpec,
    ThresholdVersionOut,
    TimelineOut,
    TokenOut,
    TripOut,
    TripReportOut,
    UserIn,
    UserOut,
)
from backend.security import (
    DUMMY_HASH,
    create_token,
    decode_token,
    hash_device_key,
    hash_password,
    new_device_key,
    verify_password,
)
from backend.settings import BackendSettings
from edge_agent.config import load_thresholds
from edge_agent.io.remote_config import apply_overrides

log = logging.getLogger("driverguard.backend")
PURGE_EVERY_S = 24 * 3600  # data policy: expired metadata is deleted at start-up, then at most this often
bearer = HTTPBearer(auto_error=False)


ID_PATTERN = r"^[A-Za-z0-9_.-]{1,48}$"
READ_ROLES = ("admin", "engineer", "manager", "driver")


def utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return (value if value.tzinfo else value.replace(tzinfo=UTC)).astimezone(UTC).isoformat()


def scoped(user: dict[str, Any], driver_id: str | None, device_id: str | None) -> dict[str, str | None]:
    """Drivers only ever see their own data, whatever filters they pass."""
    if user["role"] == "driver":
        return {"driver_id": user.get("driver_id") or "__none__", "device_id": None}
    return {"driver_id": driver_id, "device_id": device_id}


def thresholds_out(conn: sqlite3.Connection, device_id: str | None = None, for_device: bool = False) -> ThresholdsOut:
    """The dashboard gets the newest version (what an edit builds on). A device (for_device) gets the
    one it should run: its pin if it is in a trial group, else the fleet's (M47)."""
    fleet = db.fleet_thresholds_version(conn)
    if for_device:
        target = db.thresholds_target(conn, device_id)
        stored = db.get_thresholds_version(conn, target) if target else None
    else:
        stored = db.latest_thresholds(conn)
    specs = {k: ThresholdSpec(min=lo, max=hi, unit=unit) for k, (lo, hi, unit) in THRESHOLD_SPECS.items()}
    if stored is None:
        return ThresholdsOut(version=0, values={}, updated_by=None, updated_at=None, specs=specs, fleet_version=fleet)
    return ThresholdsOut(**stored, specs=specs, fleet_version=fleet)


def web_device_id(username: str) -> str:
    """Device id of a user's browser running the in-browser agent (fits the 48-char identifier)."""
    return f"web-{username}"[:48]


def fleet_status(row: dict[str, Any], now: datetime, offline_after_s: int) -> str:
    """online / offline / ended / never for one device of the fleet overview (M33)."""
    if row["last_seen"] is None:
        return "never"
    if row["state"] == "ended":
        return "ended"
    quiet_s = (now - datetime.fromisoformat(row["last_seen"])).total_seconds()
    return "offline" if quiet_s > offline_after_s else "online"


def store_batch(conn: sqlite3.Connection, batch: EventBatch, dev: str, drv: str | None) -> BatchResult:
    accepted = feedback = samples = 0
    db.touch_device(conn, dev, drv)  # any post is a sign of life (M33)
    if batch.heartbeat is not None:
        beat = batch.heartbeat.model_dump(mode="json")
        beat["ts"] = batch.heartbeat.ts.astimezone(UTC).isoformat()
        db.apply_heartbeat(conn, dev, beat)
    for e in batch.events:  # events first: feedback in the same batch may refer to them
        row = e.model_dump(mode="json")  # tags / versions (M41) are stored with the event
        row["ts"] = e.ts.astimezone(UTC).isoformat()  # one format so ts strings sort in time order
        accepted += db.insert_event(conn, dev, drv, row)
    for f in batch.feedback:
        feedback += db.apply_feedback(conn, dev, str(f.event_id), f.verdict, f.ts.astimezone(UTC).isoformat())
    for smp in batch.samples:
        row = smp.model_dump(mode="json")
        row["ts"] = smp.ts.astimezone(UTC).isoformat()
        samples += db.insert_sample(conn, dev, drv, row)
    summaries = 0
    for summ in batch.summaries:
        row = summ.model_dump(mode="json")
        row["started_at"] = summ.started_at.astimezone(UTC).isoformat()
        row["ended_at"] = summ.ended_at.astimezone(UTC).isoformat()
        summaries += db.upsert_summary(conn, dev, drv, row)
    return BatchResult(
        accepted=accepted,
        duplicates=len(batch.events) - accepted,
        feedback_applied=feedback,
        samples_accepted=samples,
        summaries_accepted=summaries,
    )


def safe_errors(exc: ValidationError) -> list[dict[str, Any]]:
    """Validation errors without the offending input, so a rejected payload is never echoed back."""
    return [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]


# --------------------------------------------------------------------------- dependencies
# Settings live in app.state so these can be module-level (one app per test).


def get_conn(request: Request) -> Iterator[sqlite3.Connection]:
    conn = db.connect(request.app.state.settings.db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


Conn = Annotated[sqlite3.Connection, Depends(get_conn)]


def current_user(
    request: Request, creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
) -> dict[str, Any]:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "not authenticated", {"WWW-Authenticate": "Bearer"})
    try:
        return decode_token(request.app.state.jwt_secret, creds.credentials)
    except jwt.PyJWTError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "invalid or expired token", {"WWW-Authenticate": "Bearer"}
        ) from None


def require_roles(*roles: str) -> Callable[..., dict[str, Any]]:
    def check(user: Annotated[dict[str, Any], Depends(current_user)]) -> dict[str, Any]:
        if user["role"] not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "role not allowed")
        return user

    return check


def current_device(conn: Conn, x_device_key: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    if not x_device_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing X-Device-Key")
    row = db.get_device_by_key_hash(conn, hash_device_key(x_device_key))
    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unknown device key")
    return dict(row)


def create_app(settings: BackendSettings | None = None) -> FastAPI:
    settings = settings or BackendSettings()
    secret = settings.jwt_secret
    if not secret:
        secret = secrets.token_urlsafe(48)
        log.warning("DG_JWT_SECRET not set: using a random secret, tokens die with this process")
    db.init_db(settings.db_path)

    app = FastAPI(title="DriverGuard backend", version="0.1.0")
    app.state.settings = settings
    app.state.jwt_secret = secret
    app.state.next_purge = 0.0  # monotonic time of the next retention purge
    app.state.audit_seen = {}  # (username, action, driver_id, device_id) -> monotonic time last logged

    def audit(
        conn: sqlite3.Connection,
        user: dict[str, Any],
        action: str,
        driver_id: str | None = None,
        device_id: str | None = None,
        detail: str | None = None,
    ) -> None:
        """Append to the access log (see module doc). Reads are de-duplicated, changes never are."""
        is_read = action.startswith("read_")
        if is_read and user["role"] == "driver":
            return  # their own data (scoped() allows nothing else)
        if is_read and settings.audit_dedupe_s > 0:
            key = (user["sub"], action, driver_id, device_id)
            last = app.state.audit_seen.get(key)
            if last is not None and time.monotonic() - last < settings.audit_dedupe_s:
                return
            app.state.audit_seen[key] = time.monotonic()
        db.log_access(conn, user["sub"], user["role"], action, driver_id, device_id, detail)

    def purge_if_due(conn: sqlite3.Connection) -> None:
        """Data policy (M37): delete metadata past its retention period. Counts only in the log."""
        if time.monotonic() < app.state.next_purge:
            return
        app.state.next_purge = time.monotonic() + PURGE_EVERY_S
        deleted = db.purge_expired(
            conn,
            datetime.now(UTC),
            settings.retention_events_days,
            settings.retention_summaries_days,
            settings.retention_access_log_days,
        )
        if any(deleted.values()):
            log.info("retention: deleted %s", deleted)

    with db.closing(settings.db_path) as conn:
        purge_if_due(conn)
    drive_links = DriveLinks()  # M31: #/drive -> #/live relay, in memory only
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Authorization", "Content-Type", "X-Device-Key"],
    )

    @app.middleware("http")
    async def limit_body_size(request: Request, call_next: Callable) -> Any:
        length = request.headers.get("content-length")
        if length is not None and length.isdigit() and int(length) > settings.max_body_bytes:
            return JSONResponse({"detail": "payload too large"}, status_code=413)
        return await call_next(request)

    # ------------------------------------------------------------------ routes
    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    # Web driving controls (M31): no login, a pairing code shown by #/live; numbers only, in memory.
    @app.put("/api/v1/drive/{code}", status_code=status.HTTP_204_NO_CONTENT)
    def put_drive(body: DriveSignalIn, code: Annotated[str, Path(pattern=DRIVE_CODE_PATTERN)]) -> None:
        drive_links.put(code, body.speed_kmh, body.turn_signal)

    @app.get("/api/v1/drive/{code}", response_model=DriveSignalOut)
    def get_drive(code: Annotated[str, Path(pattern=DRIVE_CODE_PATTERN)]) -> DriveSignalOut:
        reading = drive_links.get(code)
        if reading is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "no driving controls for this code")
        return DriveSignalOut(
            speed_kmh=reading.speed_kmh, turn_signal=reading.turn_signal, age_s=round(reading.age_s, 2)
        )

    @app.get("/api/v1/policy", response_model=PolicyOut)
    def get_policy() -> PolicyOut:
        """How long metadata is kept (docs/data-policy.md). Public: two numbers, shown on the dashboard."""
        return PolicyOut(
            retention_events_days=settings.retention_events_days,
            retention_summaries_days=settings.retention_summaries_days,
            retention_access_log_days=settings.retention_access_log_days,
        )

    @app.post("/auth/login", response_model=TokenOut)
    def login(body: LoginIn, conn: Conn) -> TokenOut:
        row = db.get_user(conn, body.username)
        ok = verify_password(body.password, row["password_hash"] if row else DUMMY_HASH)
        if row is None or not ok:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "wrong username or password")
        token = create_token(secret, row["username"], row["role"], row["driver_id"], settings.token_ttl_min)
        return TokenOut(access_token=token, role=row["role"], expires_in=settings.token_ttl_min * 60)

    @app.get("/auth/me", response_model=UserOut)
    def me(user: Annotated[dict[str, Any], Depends(current_user)]) -> UserOut:
        return UserOut(username=user["sub"], role=user["role"], driver_id=user.get("driver_id"))

    async def read_batch(request: Request, device_id: str) -> EventBatch:
        raw = await request.body()
        if len(raw) > settings.max_body_bytes:  # chunked uploads have no content-length
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "payload too large")
        try:
            data = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "body must be JSON") from None
        try:
            batch = EventBatch.model_validate(data)
        except ValidationError as exc:
            raise HTTPException(422, safe_errors(exc)) from None
        if batch.device_id != device_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "device_id does not match the device key")
        return batch

    @app.post("/api/v1/events", response_model=BatchResult)
    async def post_events(
        request: Request, device: Annotated[dict[str, Any], Depends(current_device)], conn: Conn
    ) -> BatchResult:
        batch = await read_batch(request, device["device_id"])
        purge_if_due(conn)
        return await run_in_threadpool(store_batch, conn, batch, device["device_id"], device["driver_id"])

    @app.post("/api/v1/web/events", response_model=BatchResult)
    async def post_web_events(
        request: Request, user: Annotated[dict[str, Any], Depends(require_roles(*READ_ROLES))], conn: Conn
    ) -> BatchResult:
        """The in-browser agent (#/live): same batch, sent with the signed-in user's token.

        The device is the user's browser, web-<username>; events belong to the user's own driver_id,
        so a driver cannot post for someone else.
        """
        batch = await read_batch(request, web_device_id(user["sub"]))
        purge_if_due(conn)
        return await run_in_threadpool(store_batch, conn, batch, batch.device_id, user.get("driver_id"))

    @app.get("/api/v1/web/thresholds", response_model=ThresholdsOut)
    def get_web_thresholds(
        user: Annotated[dict[str, Any], Depends(require_roles(*READ_ROLES))], conn: Conn
    ) -> ThresholdsOut:
        return thresholds_out(conn, web_device_id(user["sub"]), for_device=True)  # the browser is a device too

    @app.get("/api/v1/events", response_model=list[EventOut])
    def get_events(
        user: Annotated[dict[str, Any], Depends(require_roles(*READ_ROLES))],
        conn: Conn,
        min_level: Annotated[int, Query(ge=0, le=3)] = 0,
        since: datetime | None = None,
        until: datetime | None = None,
        driver_id: Annotated[str | None, Query(pattern=ID_PATTERN)] = None,
        device_id: Annotated[str | None, Query(pattern=ID_PATTERN)] = None,
        trip_id: Annotated[str | None, Query(pattern=ID_PATTERN)] = None,
        false_alarm_only: bool = False,
        limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    ) -> list[dict[str, Any]]:
        audit(conn, user, "read_events", driver_id, device_id)
        return db.query_events(
            conn,
            **scoped(user, driver_id, device_id),
            trip_id=trip_id,
            min_level=min_level,
            since=utc_iso(since),
            until=utc_iso(until),
            feedback="false_alarm" if false_alarm_only else None,
            limit=limit,
        )

    @app.get("/api/v1/trips", response_model=list[TripOut])
    def get_trips(
        user: Annotated[dict[str, Any], Depends(require_roles(*READ_ROLES))],
        conn: Conn,
        driver_id: Annotated[str | None, Query(pattern=ID_PATTERN)] = None,
        since: datetime | None = None,
        limit: Annotated[int, Query(ge=1, le=500)] = 50,
    ) -> list[dict[str, Any]]:
        audit(conn, user, "read_trips", driver_id)
        return db.query_trips(conn, **scoped(user, driver_id, None), since=utc_iso(since), limit=limit)

    @app.get("/api/v1/timeline", response_model=TimelineOut)
    def get_timeline(
        user: Annotated[dict[str, Any], Depends(require_roles(*READ_ROLES))],
        conn: Conn,
        trip_id: Annotated[str | None, Query(pattern=ID_PATTERN)] = None,
        driver_id: Annotated[str | None, Query(pattern=ID_PATTERN)] = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> TimelineOut:
        """Per-minute drowsy_score samples plus the alerts of the same period, oldest first."""
        audit(conn, user, "read_timeline", driver_id, detail=f"trip {trip_id}" if trip_id else None)
        filters = {
            **scoped(user, driver_id, None),
            "trip_id": trip_id,
            "since": utc_iso(since),
            "until": utc_iso(until),
        }
        events = db.query_events(conn, **filters, limit=1000)
        return TimelineOut(samples=db.query_samples(conn, **filters), events=list(reversed(events)))

    @app.get("/api/v1/stats", response_model=StatsOut)
    def get_stats(
        user: Annotated[dict[str, Any], Depends(require_roles(*READ_ROLES))],
        conn: Conn,
        driver_id: Annotated[str | None, Query(pattern=ID_PATTERN)] = None,
        since: datetime | None = None,
    ) -> dict[str, Any]:
        audit(conn, user, "read_stats", driver_id)
        return db.event_stats(conn, **scoped(user, driver_id, None), since=utc_iso(since))

    @app.get("/api/v1/fleet", response_model=list[FleetDeviceOut])
    def get_fleet(
        user: Annotated[dict[str, Any], Depends(require_roles(*READ_ROLES))],
        conn: Conn,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Fleet overview (M33): which vehicles are running, which went quiet, and their alerts in
        [since, until]. Drivers only get the devices bound to their own driver_id."""
        lo, hi = utc_iso(since), utc_iso(until)
        now = datetime.now(UTC)
        audit(conn, user, "read_fleet")
        alerts = db.fleet_alerts(conn, lo, hi)
        fleet_version = db.fleet_thresholds_version(conn)
        pins = db.threshold_pins(conn)  # trial devices run another version on purpose (M47)
        urgent_since = (now - timedelta(seconds=settings.fleet_urgent_window_s)).isoformat()
        out = []
        for row in db.fleet_devices(conn, scoped(user, None, None)["driver_id"]):
            by_level = alerts.get(row["device_id"], {})
            status = fleet_status(row, now, settings.device_offline_after_s)
            urgent = None
            if status == "online":  # a vehicle that went quiet is already shown as lost
                urgent = db.urgent_event(conn, row["device_id"], row["trip_id"], urgent_since)
            v = row["versions"]
            newest = pins.get(row["device_id"], fleet_version)  # what this device should run
            current = None if v is None else v["thresholds_version"] == newest and not v.get("thresholds_ignored")
            out.append(
                {
                    **row,
                    "thresholds_current": current,
                    "thresholds_latest": newest,
                    "status": status,
                    "urgent": urgent,
                    "alerts_by_level": {level: by_level.get(level, 0) for level in (1, 2, 3)},
                    "last_event": db.last_event(conn, row["device_id"], lo, hi),
                }
            )
        return out

    @app.get("/api/v1/trip-reports", response_model=list[TripReportOut])
    def get_trip_reports(
        user: Annotated[dict[str, Any], Depends(require_roles(*READ_ROLES))],
        conn: Conn,
        driver_id: Annotated[str | None, Query(pattern=ID_PATTERN)] = None,
        since: datetime | None = None,
        unreviewed_only: bool = False,
        limit: Annotated[int, Query(ge=1, le=500)] = 50,
    ) -> list[dict[str, Any]]:
        """End-of-trip summaries, newest first. Drivers see their own; the higher roles see every
        driver's, and which ones nobody has reviewed yet."""
        audit(conn, user, "read_trip_reports", driver_id)
        return db.query_summaries(
            conn, **scoped(user, driver_id, None), since=utc_iso(since), unreviewed_only=unreviewed_only, limit=limit
        )

    @app.get("/api/v1/trip-reports/{device_id}/{trip_id}", response_model=TripReportOut)
    def get_trip_report(
        device_id: Annotated[str, Path(pattern=ID_PATTERN)],
        trip_id: Annotated[str, Path(pattern=ID_PATTERN)],
        user: Annotated[dict[str, Any], Depends(require_roles(*READ_ROLES))],
        conn: Conn,
    ) -> dict[str, Any]:
        own = scoped(user, None, None)["driver_id"]
        report = db.get_summary(conn, device_id, trip_id, own)
        if report is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "no such trip report")
        audit(conn, user, "read_trip_report", report["driver_id"], device_id, f"trip {trip_id}")
        return report

    @app.post("/api/v1/trip-reports/{device_id}/{trip_id}/review", response_model=TripReportOut)
    def review_trip_report(
        device_id: Annotated[str, Path(pattern=ID_PATTERN)],
        trip_id: Annotated[str, Path(pattern=ID_PATTERN)],
        user: Annotated[dict[str, Any], Depends(require_roles("admin", "engineer", "manager"))],
        conn: Conn,
    ) -> dict[str, Any]:
        """A higher role has read the report (the driver's report reached someone)."""
        if not db.review_summary(conn, device_id, trip_id, user["sub"]):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "no such trip report")
        report = db.get_summary(conn, device_id, trip_id)
        assert report is not None
        audit(conn, user, "review_trip_report", report["driver_id"], device_id, f"trip {trip_id}")
        return report

    @app.get("/api/v1/thresholds", response_model=ThresholdsOut)
    def get_thresholds(
        _: Annotated[dict[str, Any], Depends(require_roles("admin", "engineer", "manager"))], conn: Conn
    ) -> ThresholdsOut:
        return thresholds_out(conn)

    @app.put("/api/v1/thresholds", response_model=ThresholdsOut)
    def put_thresholds(
        body: ThresholdsIn,
        user: Annotated[dict[str, Any], Depends(require_roles("admin", "engineer"))],
        conn: Conn,
    ) -> ThresholdsOut:
        """Store a new version: the previous overrides updated with the given keys."""
        current = db.latest_thresholds(conn)
        merged = {**(current["values"] if current else {}), **body.values}
        # Same rules as the device, on the repo's thresholds.yaml + all overrides: a version
        # the device would ignore (e.g. microsleep event after the L3 rule) is refused here.
        _, problems = apply_overrides(load_thresholds(), merged)
        if problems:
            raise HTTPException(422, "; ".join(problems))
        fleet_before = db.fleet_thresholds_version(conn)
        version = db.save_thresholds(conn, merged, user["sub"])
        detail = f"version {version}: {', '.join(sorted(body.values))}"
        if body.trial_devices:  # a trial: only these devices, the fleet stays where it is (M47)
            db.set_fleet_thresholds(conn, fleet_before, user["sub"])
            db.pin_thresholds(conn, body.trial_devices, version, user["sub"])
            detail += f"; trial on {', '.join(sorted(body.trial_devices))}"
        else:  # the whole fleet at once: trials are over
            db.set_fleet_thresholds(conn, version, user["sub"])
            db.clear_threshold_pins(conn)
        audit(conn, user, "update_thresholds", detail=detail[:240])
        return thresholds_out(conn)

    @app.get("/api/v1/thresholds/versions", response_model=list[ThresholdVersionOut])
    def get_threshold_versions(
        _: Annotated[dict[str, Any], Depends(require_roles("admin", "engineer", "manager"))], conn: Conn
    ) -> list[dict[str, Any]]:
        """Recent versions: which is the fleet's, which devices are on a trial, what each one changed,
        and its alerts / drivers' false-alarm marks so far (what to look at before a rollout)."""
        return db.threshold_history(conn)

    @app.post("/api/v1/thresholds/rollout", response_model=ThresholdsOut)
    def rollout_thresholds(
        body: RolloutIn,
        user: Annotated[dict[str, Any], Depends(require_roles("admin", "engineer"))],
        conn: Conn,
    ) -> ThresholdsOut:
        """Give a stored version to the whole fleet: a trial that went well, or an older version (roll
        back). Trial pins end. Devices take it at their next poll, while parked."""
        stored = db.get_thresholds_version(conn, body.version)
        if stored is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "no such thresholds version")
        _, problems = apply_overrides(load_thresholds(), stored["values"])  # the YAML may have moved on
        if problems:
            raise HTTPException(422, "; ".join(problems))
        before = db.fleet_thresholds_version(conn)
        db.set_fleet_thresholds(conn, body.version, user["sub"])
        db.clear_threshold_pins(conn)
        audit(conn, user, "rollout_thresholds", detail=f"fleet version {before} -> {body.version}")
        return thresholds_out(conn)

    @app.get("/api/v1/device/thresholds", response_model=ThresholdsOut)
    def get_device_thresholds(device: Annotated[dict[str, Any], Depends(current_device)], conn: Conn) -> ThresholdsOut:
        return thresholds_out(conn, device["device_id"], for_device=True)

    @app.get("/api/v1/access-log", response_model=list[AccessLogOut])
    def get_access_log(
        admin: Annotated[dict[str, Any], Depends(require_roles("admin"))],
        conn: Conn,
        driver_id: Annotated[str | None, Query(pattern=ID_PATTERN)] = None,
        username: Annotated[str | None, Query(pattern=ID_PATTERN)] = None,
        since: datetime | None = None,
        limit: Annotated[int, Query(ge=1, le=1000)] = 200,
    ) -> list[dict[str, Any]]:
        """Who read whose data, who changed what (M41), newest first. Admins only; reading it is logged too."""
        rows = db.query_access_log(conn, driver_id=driver_id, username=username, since=utc_iso(since), limit=limit)
        audit(conn, admin, "read_access_log", driver_id)
        return rows

    @app.get("/api/v1/access-log/mine", response_model=list[AccessLogOut])
    def get_my_access_log(
        user: Annotated[dict[str, Any], Depends(require_roles("driver"))],
        conn: Conn,
        since: datetime | None = None,
        limit: Annotated[int, Query(ge=1, le=1000)] = 200,
    ) -> list[dict[str, Any]]:
        """A driver sees who looked at their data: reads naming them and reads of the whole fleet."""
        driver = user.get("driver_id") or "__none__"
        return db.query_access_log(conn, since=utc_iso(since), about_driver=driver, limit=limit)

    # ---- a driver's own data (M48): export, ask for deletion; an admin answers ----
    @app.get("/api/v1/me/data")
    def export_my_data(user: Annotated[dict[str, Any], Depends(require_roles("driver"))], conn: Conn) -> dict[str, Any]:
        """Everything stored about the signed-in driver, as JSON (the page offers it as a file)."""
        driver = user.get("driver_id")
        if not driver:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "this account is not bound to a driver")
        return {
            "exported_at": datetime.now(UTC).isoformat(),
            "account": user["sub"],
            "retention_days": {
                "events": settings.retention_events_days,
                "trip_summaries": settings.retention_summaries_days,
            },
            **db.export_driver_data(conn, driver),
        }

    @app.get("/api/v1/me/deletion-request", response_model=DeletionRequestOut | None)
    def get_my_deletion_request(
        user: Annotated[dict[str, Any], Depends(require_roles("driver"))], conn: Conn
    ) -> dict[str, Any] | None:
        """The driver's newest deletion request, or null."""
        rows = db.deletion_requests(conn, user.get("driver_id") or "__none__")
        return rows[0] if rows else None

    @app.post("/api/v1/me/deletion-request", response_model=DeletionRequestOut)
    def post_my_deletion_request(
        user: Annotated[dict[str, Any], Depends(require_roles("driver"))], conn: Conn
    ) -> dict[str, Any]:
        """Ask for everything stored about me to be deleted. An admin deletes it or refuses with a reason."""
        driver = user.get("driver_id")
        if not driver:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "this account is not bound to a driver")
        return db.request_deletion(conn, driver, user["sub"])

    @app.get("/api/v1/deletion-requests", response_model=list[DeletionRequestOut])
    def get_deletion_requests(
        _: Annotated[dict[str, Any], Depends(require_roles("admin"))], conn: Conn
    ) -> list[dict[str, Any]]:
        return db.deletion_requests(conn)

    @app.post("/api/v1/deletion-requests/{request_id}", response_model=DeletionRequestOut)
    def decide_deletion_request(
        request_id: int,
        body: DeletionDecisionIn,
        admin: Annotated[dict[str, Any], Depends(require_roles("admin"))],
        conn: Conn,
    ) -> dict[str, Any]:
        """Delete the driver's data (as `manage delete-driver-data` does) or refuse; both are logged."""
        done = db.handle_deletion(
            conn, request_id, "done" if body.action == "delete" else "refused", admin["sub"], body.reason
        )
        if done is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "no such pending request")
        if body.action == "delete":
            deleted = db.delete_driver_data(conn, done["driver_id"])
            audit(conn, admin, "delete_driver_data", done["driver_id"], detail=f"request {request_id}: {deleted}")
        else:
            audit(conn, admin, "refuse_deletion", done["driver_id"], detail=f"request {request_id}: {body.reason}")
        return done

    @app.get("/api/v1/users", response_model=list[UserOut])
    def get_users(_: Annotated[dict[str, Any], Depends(require_roles("admin"))], conn: Conn) -> list[dict[str, Any]]:
        return [dict(r) for r in db.list_users(conn)]

    @app.post("/api/v1/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
    def post_user(
        body: UserIn, admin: Annotated[dict[str, Any], Depends(require_roles("admin"))], conn: Conn
    ) -> UserOut:
        try:
            db.create_user(conn, body.username, hash_password(body.password), body.role, body.driver_id)
        except sqlite3.IntegrityError:
            raise HTTPException(status.HTTP_409_CONFLICT, "username already exists") from None
        audit(conn, admin, "create_user", body.driver_id, detail=f"{body.role} {body.username}")
        return UserOut(username=body.username, role=body.role, driver_id=body.driver_id)

    @app.post("/api/v1/devices", response_model=DeviceOut, status_code=status.HTTP_201_CREATED)
    def post_device(
        body: DeviceIn, admin: Annotated[dict[str, Any], Depends(require_roles("admin"))], conn: Conn
    ) -> DeviceOut:
        key = new_device_key()
        try:
            db.create_device(conn, body.device_id, hash_device_key(key), body.driver_id)
        except sqlite3.IntegrityError:
            raise HTTPException(status.HTTP_409_CONFLICT, "device_id already exists") from None
        audit(conn, admin, "create_device", body.driver_id, body.device_id)
        return DeviceOut(device_id=body.device_id, driver_id=body.driver_id, device_key=key)

    return app


def __getattr__(name: str) -> Any:
    # `uvicorn backend.app:app` builds the app lazily, so importing this module in tests has no side effects.
    if name == "app":
        return create_app()
    raise AttributeError(name)
