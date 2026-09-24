"""DriverGuard backend: receives event metadata from edge devices, serves it to 3 roles.

    uvicorn backend.app:app --port 8100         (settings from DG_* env vars / .env)
    python -m backend.manage create-user admin --role admin

Roles:
- admin:   manage users and devices, read all events
- manager: read all events (fleet)
- driver:  read only the events of their own driver_id
Edge devices are not users: they post events with their X-Device-Key.
"""

from __future__ import annotations

import json
import logging
import secrets
import sqlite3
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from typing import Annotated, Any

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ValidationError

from backend import db
from backend.schemas import (
    BatchResult,
    DeviceIn,
    DeviceOut,
    EventBatch,
    EventOut,
    LoginIn,
    TokenOut,
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

log = logging.getLogger("driverguard.backend")
bearer = HTTPBearer(auto_error=False)


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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_methods=["GET", "POST"],
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

    @app.post("/api/v1/events", response_model=BatchResult)
    async def post_events(
        request: Request, device: Annotated[dict[str, Any], Depends(current_device)], conn: Conn
    ) -> BatchResult:
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
        if batch.device_id != device["device_id"]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "device_id does not match the device key")

        def store() -> BatchResult:
            accepted = 0
            for e in batch.events:
                row = e.model_dump(mode="json")
                row["ts"] = e.ts.astimezone(UTC).isoformat()  # one format so ts strings sort in time order
                accepted += db.insert_event(conn, device["device_id"], device["driver_id"], row)
            return BatchResult(accepted=accepted, duplicates=len(batch.events) - accepted)

        return await run_in_threadpool(store)

    @app.get("/api/v1/events", response_model=list[EventOut])
    def get_events(
        user: Annotated[dict[str, Any], Depends(require_roles("admin", "manager", "driver"))],
        conn: Conn,
        min_level: Annotated[int, Query(ge=0, le=3)] = 0,
        since: datetime | None = None,
        driver_id: Annotated[str | None, Query(pattern=r"^[A-Za-z0-9_.-]{1,48}$")] = None,
        device_id: Annotated[str | None, Query(pattern=r"^[A-Za-z0-9_.-]{1,48}$")] = None,
        limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    ) -> list[dict[str, Any]]:
        if user["role"] == "driver":
            driver_id = user.get("driver_id") or "__none__"  # drivers only ever see their own events
            device_id = None
        return db.query_events(
            conn,
            driver_id=driver_id,
            device_id=device_id,
            min_level=min_level,
            since=(since if since.tzinfo else since.replace(tzinfo=UTC)).astimezone(UTC).isoformat() if since else None,
            limit=limit,
        )

    @app.get("/api/v1/users", response_model=list[UserOut])
    def get_users(_: Annotated[dict[str, Any], Depends(require_roles("admin"))], conn: Conn) -> list[dict[str, Any]]:
        return [dict(r) for r in db.list_users(conn)]

    @app.post("/api/v1/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
    def post_user(body: UserIn, _: Annotated[dict[str, Any], Depends(require_roles("admin"))], conn: Conn) -> UserOut:
        try:
            db.create_user(conn, body.username, hash_password(body.password), body.role, body.driver_id)
        except sqlite3.IntegrityError:
            raise HTTPException(status.HTTP_409_CONFLICT, "username already exists") from None
        return UserOut(username=body.username, role=body.role, driver_id=body.driver_id)

    @app.post("/api/v1/devices", response_model=DeviceOut, status_code=status.HTTP_201_CREATED)
    def post_device(
        body: DeviceIn, _: Annotated[dict[str, Any], Depends(require_roles("admin"))], conn: Conn
    ) -> DeviceOut:
        key = new_device_key()
        try:
            db.create_device(conn, body.device_id, hash_device_key(key), body.driver_id)
        except sqlite3.IntegrityError:
            raise HTTPException(status.HTTP_409_CONFLICT, "device_id already exists") from None
        return DeviceOut(device_id=body.device_id, driver_id=body.driver_id, device_key=key)

    return app


def __getattr__(name: str) -> Any:
    # `uvicorn backend.app:app` builds the app lazily, so importing this module in tests has no side effects.
    if name == "app":
        return create_app()
    raise AttributeError(name)
