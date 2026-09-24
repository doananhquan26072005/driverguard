"""Passwords (scrypt), user tokens (JWT HS256) and device keys."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 1


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P)
    b64 = base64.b64encode
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${b64(salt).decode()}${b64(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = base64.b64decode(digest)
        actual = hashlib.scrypt(
            password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p), dklen=len(expected)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


# Burn the same time for unknown users as for a wrong password (no username probing).
DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def create_token(secret: str, username: str, role: str, driver_id: str | None, ttl_min: int) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": username,
        "role": role,
        "driver_id": driver_id,
        "iat": now,
        "exp": now + timedelta(minutes=ttl_min),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_token(secret: str, token: str) -> dict[str, Any]:
    """Raises jwt.PyJWTError if the token is invalid or expired."""
    return jwt.decode(token, secret, algorithms=["HS256"], options={"require": ["sub", "role", "exp"]})


def new_device_key() -> str:
    return "dgk_" + secrets.token_urlsafe(32)


def hash_device_key(key: str) -> str:
    # Device keys are 256-bit random values: a plain SHA-256 is enough (no brute force possible).
    return hashlib.sha256(key.encode()).hexdigest()
