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
