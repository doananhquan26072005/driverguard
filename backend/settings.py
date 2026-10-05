"""Backend settings, from environment variables prefixed DG_ (or .env)."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BackendSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DG_", env_file=".env", extra="ignore")

    db_path: str = "data/driverguard.db"
    # Required in production: a long random string (python -c "import secrets; print(secrets.token_urlsafe(48))").
    jwt_secret: str = Field(default="", repr=False)
    token_ttl_min: int = Field(default=60, ge=1, le=24 * 60)
    max_body_bytes: int = Field(default=256 * 1024, ge=1024)  # an event batch is a few KB
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    # Fleet overview (M33): a device not heard from for this long is offline. 3 heartbeats of
    # publisher.heartbeat_interval_s (30 s) by default.
    device_offline_after_s: int = Field(default=90, ge=5, le=24 * 3600)
    # Data policy (M37, docs/data-policy.md): metadata older than this is deleted, at start-up and then
    # once a day. Events (alerts, system events, false-alarm marks) and per-minute samples: 60 days;
    # end-of-trip summaries: 365 days. 0 = keep forever. The consent screen states these defaults
    # (frontend/src/lib/labels.ts RETENTION_DAYS): change both together.
    retention_events_days: int = Field(default=60, ge=0, le=3650)
    retention_summaries_days: int = Field(default=365, ge=0, le=3650)
