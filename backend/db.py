"""SQLite storage (stdlib sqlite3). Only metadata is stored: there is no column for images."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('admin', 'engineer', 'manager', 'driver')),
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
    received_at       TEXT NOT NULL,
    feedback          TEXT,
    feedback_at       TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events (ts);
CREATE INDEX IF NOT EXISTS idx_events_driver ON events (driver_id, ts);
CREATE TABLE IF NOT EXISTS fatigue_samples (
    id           INTEGER PRIMARY KEY,
    sample_id    TEXT NOT NULL UNIQUE,
    device_id    TEXT NOT NULL,
    driver_id    TEXT,
    trip_id      TEXT NOT NULL,
    ts           TEXT NOT NULL,
    drowsy_score REAL NOT NULL,
    perclos_60s  REAL,
    max_level    INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_samples_trip ON fatigue_samples (trip_id, ts);
CREATE TABLE IF NOT EXISTS trip_summaries (
    id          INTEGER PRIMARY KEY,
    trip_id     TEXT NOT NULL,
    device_id   TEXT NOT NULL,
    driver_id   TEXT,
    started_at  TEXT NOT NULL,
    received_at TEXT NOT NULL,
    rating      TEXT NOT NULL,
    summary     TEXT NOT NULL,
    reviewed_by TEXT,
    reviewed_at TEXT,
    UNIQUE (device_id, trip_id)
);
CREATE INDEX IF NOT EXISTS idx_summaries_driver ON trip_summaries (driver_id, started_at);
CREATE TABLE IF NOT EXISTS device_status (
    device_id TEXT PRIMARY KEY,
    driver_id TEXT,
    last_seen TEXT NOT NULL,
    trip_id   TEXT,
    state     TEXT,
    moving    INTEGER,
    state_ts  TEXT
);
CREATE TABLE IF NOT EXISTS threshold_versions (
    version    INTEGER PRIMARY KEY,
    vals       TEXT NOT NULL,
    updated_by TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


USERS_REBUILD = """
CREATE TABLE users_new (
    id            INTEGER PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('admin', 'engineer', 'manager', 'driver')),
    driver_id     TEXT,
    created_at    TEXT NOT NULL
);
INSERT INTO users_new SELECT id, username, password_hash, role, driver_id, created_at FROM users;
DROP TABLE users;
ALTER TABLE users_new RENAME TO users;
"""


def migrate(conn: sqlite3.Connection) -> None:
    """Bring a database created by an older version (M5) up to date, keeping its data."""
    users_sql = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='users'").fetchone()
    if users_sql and "'engineer'" not in users_sql[0]:
        # SQLite cannot alter a CHECK constraint: rebuild the table with the new role list.
        conn.executescript("BEGIN;" + USERS_REBUILD + "COMMIT;")
    columns = {r[1] for r in conn.execute("PRAGMA table_info(events)")}
    for col in ("feedback", "feedback_at"):
        if col not in columns:
            conn.execute(f"ALTER TABLE events ADD COLUMN {col} TEXT")


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
        migrate(conn)


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


# --------------------------------------------------------------------------- fleet overview (M33)


def touch_device(conn: sqlite3.Connection, device_id: str, driver_id: str | None) -> None:
    """The device (or a user's browser) just posted something: it is alive now (server time)."""
    conn.execute(
        """INSERT INTO device_status (device_id, driver_id, last_seen) VALUES (?, ?, ?)
           ON CONFLICT (device_id) DO UPDATE SET driver_id = excluded.driver_id, last_seen = excluded.last_seen""",
        (device_id, driver_id, now_iso()),
    )


def apply_heartbeat(conn: sqlite3.Connection, device_id: str, h: dict[str, Any]) -> bool:
    """Trip / monitoring state from a heartbeat; False if a newer one (device time) is already stored."""
    cur = conn.execute(
        """UPDATE device_status SET trip_id = ?, state = ?, moving = ?, state_ts = ?
           WHERE device_id = ? AND (state_ts IS NULL OR state_ts <= ?)""",
        (h["trip_id"], h["state"], h["moving"], h["ts"], device_id, h["ts"]),
    )
    return cur.rowcount == 1


def fleet_devices(conn: sqlite3.Connection, driver_id: str | None = None) -> list[dict[str, Any]]:
    """Every registered device plus every device heard from (browsers are not registered), by id."""
    rows = conn.execute(
        """SELECT d.device_id, COALESCE(s.driver_id, d.driver_id) AS driver_id,
                  s.last_seen, s.trip_id, s.state, s.moving
           FROM devices d LEFT JOIN device_status s ON s.device_id = d.device_id
           UNION ALL
           SELECT s.device_id, s.driver_id, s.last_seen, s.trip_id, s.state, s.moving
           FROM device_status s WHERE s.device_id NOT IN (SELECT device_id FROM devices)
           ORDER BY 1"""
    ).fetchall()
    out = [dict(r) for r in rows if driver_id is None or r["driver_id"] == driver_id]
    for d in out:
        d["moving"] = None if d["moving"] is None else bool(d["moving"])
    return out


def fleet_alerts(conn: sqlite3.Connection, since: str | None, until: str | None) -> dict[str, dict[int, int]]:
    """device_id -> {level: alerts} in the period (system events are not alerts)."""
    where, args = _where(since=since, until=until)
    rows = conn.execute(
        f"SELECT device_id, level, COUNT(*) AS n FROM events WHERE {where} AND type != 'system' "
        "GROUP BY device_id, level",
        args,
    ).fetchall()
    out: dict[str, dict[int, int]] = {}
    for r in rows:
        out.setdefault(r["device_id"], {})[r["level"]] = r["n"]
    return out


def last_event(conn: sqlite3.Connection, device_id: str, since: str | None, until: str | None) -> dict[str, Any] | None:
    where, args = _where(device_id=device_id, since=since, until=until)
    row = conn.execute(
        f"SELECT ts, type, level, reasons FROM events WHERE {where} ORDER BY ts DESC LIMIT 1", args
    ).fetchone()
    if row is None:
        return None
    return {**dict(row), "reasons": json.loads(row["reasons"])}


# --------------------------------------------------------------------------- data policy (M37)


def purge_expired(conn: sqlite3.Connection, now: datetime, events_days: int, summaries_days: int) -> dict[str, int]:
    """Delete metadata past its retention period (0 days = keep). Returns rows deleted per table."""
    out = {"events": 0, "fatigue_samples": 0, "trip_summaries": 0}
    if events_days > 0:
        cutoff = (now - timedelta(days=events_days)).astimezone(UTC).isoformat()
        out["events"] = conn.execute("DELETE FROM events WHERE ts < ?", (cutoff,)).rowcount
        out["fatigue_samples"] = conn.execute("DELETE FROM fatigue_samples WHERE ts < ?", (cutoff,)).rowcount
    if summaries_days > 0:
        cutoff = (now - timedelta(days=summaries_days)).astimezone(UTC).isoformat()
        out["trip_summaries"] = conn.execute("DELETE FROM trip_summaries WHERE started_at < ?", (cutoff,)).rowcount
    return out


def delete_driver_data(conn: sqlite3.Connection, driver_id: str) -> dict[str, int]:
    """Everything stored about one driver (the driver left, or asks for deletion). Accounts and
    device registrations are not touched. Returns rows deleted per table."""
    return {
        table: conn.execute(f"DELETE FROM {table} WHERE driver_id = ?", (driver_id,)).rowcount
        for table in ("events", "fatigue_samples", "trip_summaries", "device_status")
    }


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


def apply_feedback(conn: sqlite3.Connection, device_id: str, event_id: str, verdict: str, ts: str) -> bool:
    """Mark an event of this device; False if the device has no such event."""
    cur = conn.execute(
        "UPDATE events SET feedback = ?, feedback_at = ? WHERE event_id = ? AND device_id = ?",
        (verdict, ts, event_id, device_id),
    )
    return cur.rowcount == 1


def insert_sample(conn: sqlite3.Connection, device_id: str, driver_id: str | None, s: dict[str, Any]) -> bool:
    cur = conn.execute(
        """INSERT OR IGNORE INTO fatigue_samples
               (sample_id, device_id, driver_id, trip_id, ts, drowsy_score, perclos_60s, max_level)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            s["sample_id"],
            device_id,
            driver_id,
            s["trip_id"],
            s["ts"],
            s["drowsy_score"],
            s["perclos_60s"],
            s["max_level"],
        ),
    )
    return cur.rowcount == 1


def upsert_summary(conn: sqlite3.Connection, device_id: str, driver_id: str | None, s: dict[str, Any]) -> bool:
    """Store a trip summary; a re-sent one (offline queue retry) replaces it but keeps the review."""
    now = datetime.now(UTC).isoformat()
    cur = conn.execute(
        """INSERT INTO trip_summaries (trip_id, device_id, driver_id, started_at, received_at, rating, summary)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT (device_id, trip_id) DO UPDATE SET
               started_at = excluded.started_at, rating = excluded.rating, summary = excluded.summary""",
        (s["trip_id"], device_id, driver_id, s["started_at"], now, s["rating"], json.dumps(s)),
    )
    return cur.rowcount == 1


def _summary_row(r: sqlite3.Row) -> dict[str, Any]:
    d = dict(r)
    d["summary"] = json.loads(d["summary"])
    return d


def query_summaries(
    conn: sqlite3.Connection,
    driver_id: str | None = None,
    device_id: str | None = None,
    since: str | None = None,
    unreviewed_only: bool = False,
    limit: int = 50,
) -> list[dict[str, Any]]:
    where, args = ["1=1"], []
    for col, val in (("driver_id", driver_id), ("device_id", device_id)):
        if val is not None:
            where.append(f"{col} = ?")
            args.append(val)
    if since is not None:
        where.append("started_at >= ?")
        args.append(since)
    if unreviewed_only:
        where.append("reviewed_at IS NULL")
    rows = conn.execute(
        f"""SELECT trip_id, device_id, driver_id, received_at, rating, reviewed_by, reviewed_at, summary
            FROM trip_summaries WHERE {" AND ".join(where)} ORDER BY started_at DESC LIMIT ?""",
        [*args, limit],
    ).fetchall()
    return [_summary_row(r) for r in rows]


def get_summary(
    conn: sqlite3.Connection, device_id: str, trip_id: str, driver_id: str | None = None
) -> dict[str, Any] | None:
    sql = """SELECT trip_id, device_id, driver_id, received_at, rating, reviewed_by, reviewed_at, summary
             FROM trip_summaries WHERE device_id = ? AND trip_id = ?"""
    args: list[Any] = [device_id, trip_id]
    if driver_id is not None:
        sql += " AND driver_id = ?"
        args.append(driver_id)
    row = conn.execute(sql, args).fetchone()
    return None if row is None else _summary_row(row)


def review_summary(conn: sqlite3.Connection, device_id: str, trip_id: str, username: str) -> bool:
    cur = conn.execute(
        "UPDATE trip_summaries SET reviewed_by = ?, reviewed_at = ? WHERE device_id = ? AND trip_id = ?",
        (username, datetime.now(UTC).isoformat(), device_id, trip_id),
    )
    return cur.rowcount > 0


def _where(
    driver_id: str | None = None,
    device_id: str | None = None,
    trip_id: str | None = None,
    since: str | None = None,
    until: str | None = None,
) -> tuple[str, list[Any]]:
    clauses, args = ["1 = 1"], []
    for column, value in (("driver_id", driver_id), ("device_id", device_id), ("trip_id", trip_id)):
        if value is not None:
            clauses.append(f"{column} = ?")
            args.append(value)
    if since is not None:
        clauses.append("ts >= ?")
        args.append(since)
    if until is not None:
        clauses.append("ts <= ?")
        args.append(until)
    return " AND ".join(clauses), args


def query_samples(conn: sqlite3.Connection, limit: int = 2000, **filters: Any) -> list[dict[str, Any]]:
    where, args = _where(**filters)
    rows = conn.execute(
        "SELECT ts, trip_id, device_id, driver_id, drowsy_score, perclos_60s, max_level FROM fatigue_samples "
        f"WHERE {where} ORDER BY ts LIMIT ?",
        [*args, limit],
    ).fetchall()
    return [dict(r) for r in rows]


def query_trips(conn: sqlite3.Connection, limit: int = 100, **filters: Any) -> list[dict[str, Any]]:
    """Trips seen in events or samples, newest first."""
    where, args = _where(**filters)
    rows = conn.execute(
        f"""SELECT trip_id, device_id, MAX(driver_id) AS driver_id, MIN(ts) AS start, MAX(ts) AS end,
                   SUM(is_event) AS events, MAX(level) AS max_level
            FROM (SELECT trip_id, device_id, driver_id, ts, 1 AS is_event, level FROM events WHERE {where}
                  UNION ALL
                  SELECT trip_id, device_id, driver_id, ts, 0, max_level FROM fatigue_samples WHERE {where})
            GROUP BY trip_id, device_id ORDER BY end DESC LIMIT ?""",
        [*args, *args, limit],
    ).fetchall()
    return [dict(r) for r in rows]


def event_stats(conn: sqlite3.Connection, **filters: Any) -> dict[str, Any]:
    where, args = _where(**filters)
    # Alerts only: system events (camera_lost / camera_restored) are listed in the log, not counted here.
    rows = conn.execute(
        f"SELECT level, reasons, feedback FROM events WHERE {where} AND type != 'system'", args
    ).fetchall()
    by_level = {level: 0 for level in range(4)}
    by_reason: dict[str, dict[str, int]] = {}
    false_alarms = 0
    for r in rows:
        by_level[r["level"]] += 1
        is_false = r["feedback"] == "false_alarm"
        false_alarms += is_false
        for reason in json.loads(r["reasons"]):
            stat = by_reason.setdefault(reason, {"total": 0, "false_alarms": 0})
            stat["total"] += 1
            stat["false_alarms"] += is_false
    return {"total": len(rows), "false_alarms": false_alarms, "by_level": by_level, "by_reason": by_reason}


def latest_thresholds(conn: sqlite3.Connection) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM threshold_versions ORDER BY version DESC LIMIT 1").fetchone()
    if row is None:
        return None
    return {
        "version": row["version"],
        "values": json.loads(row["vals"]),
        "updated_by": row["updated_by"],
        "updated_at": row["updated_at"],
    }


def save_thresholds(conn: sqlite3.Connection, values: dict[str, float], username: str) -> int:
    cur = conn.execute(
        "INSERT INTO threshold_versions (vals, updated_by, updated_at) VALUES (?, ?, ?)",
        (json.dumps(values, sort_keys=True), username, now_iso()),
    )
    return int(cur.lastrowid)


def query_events(
    conn: sqlite3.Connection,
    driver_id: str | None = None,
    device_id: str | None = None,
    min_level: int = 0,
    since: str | None = None,
    limit: int = 100,
    trip_id: str | None = None,
    until: str | None = None,
    feedback: str | None = None,
) -> list[dict[str, Any]]:
    where, args = _where(driver_id=driver_id, device_id=device_id, trip_id=trip_id, since=since, until=until)
    sql = f"SELECT * FROM events WHERE {where} AND level >= ?"
    args.append(min_level)
    if feedback is not None:
        sql += " AND feedback = ?"
        args.append(feedback)
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
