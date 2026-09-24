"""SQLite storage (stdlib sqlite3). Only metadata is stored: there is no column for images."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('admin', 'manager', 'driver')),
    driver_id     TEXT,
    created_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS devices (
    id         INTEGER PRIMARY KEY,
    device_id  TEXT NOT NULL UNIQUE,
    key_hash   TEXT NOT NULL UNIQUE,
    driver_id  TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id                INTEGER PRIMARY KEY,
    event_id          TEXT NOT NULL UNIQUE,
    device_id         TEXT NOT NULL,
    driver_id         TEXT,
    trip_id           TEXT NOT NULL,
    ts                TEXT NOT NULL,
    type              TEXT NOT NULL,
    level             INTEGER NOT NULL,
    reasons           TEXT NOT NULL,
    drowsy_score      REAL NOT NULL,
    distraction_score REAL NOT NULL,
    speed_kmh         REAL,
    metrics           TEXT NOT NULL,
    received_at       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events (ts);
CREATE INDEX IF NOT EXISTS idx_events_driver ON events (driver_id, ts);
"""


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def connect(db_path: str) -> sqlite3.Connection:
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: str) -> None:
    with closing(db_path) as conn:
        conn.executescript(SCHEMA)


@contextmanager
def closing(db_path: str) -> Iterator[sqlite3.Connection]:
    conn = connect(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# --------------------------------------------------------------------------- users / devices


def create_user(conn: sqlite3.Connection, username: str, password_hash: str, role: str, driver_id: str | None) -> None:
    conn.execute(
        "INSERT INTO users (username, password_hash, role, driver_id, created_at) VALUES (?, ?, ?, ?, ?)",
        (username, password_hash, role, driver_id, now_iso()),
    )


def get_user(conn: sqlite3.Connection, username: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()


def list_users(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT username, role, driver_id FROM users ORDER BY username").fetchall()


def create_device(conn: sqlite3.Connection, device_id: str, key_hash: str, driver_id: str | None) -> None:
    conn.execute(
        "INSERT INTO devices (device_id, key_hash, driver_id, created_at) VALUES (?, ?, ?, ?)",
        (device_id, key_hash, driver_id, now_iso()),
    )


def get_device_by_key_hash(conn: sqlite3.Connection, key_hash: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM devices WHERE key_hash = ?", (key_hash,)).fetchone()


# --------------------------------------------------------------------------- events


def insert_event(conn: sqlite3.Connection, device_id: str, driver_id: str | None, e: dict[str, Any]) -> bool:
    """Insert one event; False if its event_id is already stored (idempotent retries)."""
    cur = conn.execute(
        """INSERT OR IGNORE INTO events (event_id, device_id, driver_id, trip_id, ts, type, level, reasons,
               drowsy_score, distraction_score, speed_kmh, metrics, received_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            e["event_id"],
            device_id,
            driver_id,
            e["trip_id"],
            e["ts"],
            e["type"],
            e["level"],
            json.dumps(e["reasons"]),
            e["drowsy_score"],
            e["distraction_score"],
            e["speed_kmh"],
            json.dumps(e["metrics"]),
            now_iso(),
        ),
    )
    return cur.rowcount == 1


def query_events(
    conn: sqlite3.Connection,
    driver_id: str | None = None,
    device_id: str | None = None,
    min_level: int = 0,
    since: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM events WHERE level >= ?"
    args: list[Any] = [min_level]
    if driver_id is not None:
        sql += " AND driver_id = ?"
        args.append(driver_id)
    if device_id is not None:
        sql += " AND device_id = ?"
        args.append(device_id)
    if since is not None:
        sql += " AND ts >= ?"
        args.append(since)
    sql += " ORDER BY ts DESC LIMIT ?"
    args.append(limit)
    rows = conn.execute(sql, args).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d.pop("id")
        d["reasons"] = json.loads(d["reasons"])
        d["metrics"] = json.loads(d["metrics"])
        out.append(d)
    return out
