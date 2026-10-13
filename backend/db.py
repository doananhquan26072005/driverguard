"""SQLite storage (stdlib sqlite3). Only metadata is stored: there is no column for images."""

from __future__ import annotations

import json
import os
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
    feedback_at       TEXT,
    tags              TEXT,
    versions          TEXT,
    delay_s           REAL
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
    max_level    INTEGER NOT NULL,
    off_road_ratio REAL,
    received_at  TEXT
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
    review_note TEXT,
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
    state_ts  TEXT,
    versions  TEXT,
    perf      TEXT,
    clock_skew_s REAL
);
CREATE TABLE IF NOT EXISTS threshold_versions (
    version    INTEGER PRIMARY KEY,
    vals       TEXT NOT NULL,
    updated_by TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
-- Which thresholds version runs where (M47). No row in threshold_rollout: the newest version is the
-- fleet's (as before M47). A pin gives one device another version (a trial group, "canary").
CREATE TABLE IF NOT EXISTS threshold_rollout (
    id            INTEGER PRIMARY KEY CHECK (id = 1),
    fleet_version INTEGER NOT NULL,
    updated_by    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS threshold_pins (
    device_id  TEXT PRIMARY KEY,
    version    INTEGER NOT NULL,
    updated_by TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
-- A driver asked for their data to be deleted (M48); an admin deletes it or refuses with a reason.
CREATE TABLE IF NOT EXISTS deletion_requests (
    id           INTEGER PRIMARY KEY,
    driver_id    TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    requested_at TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending',
    handled_by   TEXT,
    handled_at   TEXT,
    reason       TEXT
);
CREATE TABLE IF NOT EXISTS access_log (
    id        INTEGER PRIMARY KEY,
    ts        TEXT NOT NULL,
    username  TEXT NOT NULL,
    role      TEXT NOT NULL,
    action    TEXT NOT NULL,
    driver_id TEXT,
    device_id TEXT,
    detail    TEXT
);
CREATE INDEX IF NOT EXISTS idx_access_log_ts ON access_log (ts);
CREATE INDEX IF NOT EXISTS idx_access_log_driver ON access_log (driver_id, ts);
CREATE TRIGGER IF NOT EXISTS access_log_append_only BEFORE UPDATE ON access_log
BEGIN
    SELECT RAISE(ABORT, 'access_log is append-only');
END;
"""

# Events a person set by hand (PRD FR-17, tag "forced") are stored and listed, never counted.
NOT_FORCED = "(tags IS NULL OR tags NOT LIKE '%\"forced\"%')"


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
    if "off_road_ratio" not in {r[1] for r in conn.execute("PRAGMA table_info(fatigue_samples)")}:  # M38
        conn.execute("ALTER TABLE fatigue_samples ADD COLUMN off_road_ratio REAL")
    for table, cols in (("events", ("tags", "versions")), ("device_status", ("versions", "perf"))):  # M41, M49
        have = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        for col in cols:
            if col not in have:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} TEXT")
    # M82: server time decides order, the urgent window and retention; the device's clock is only kept.
    for table, col, kind in (
        ("events", "delay_s", "REAL"),
        ("device_status", "clock_skew_s", "REAL"),
        ("fatigue_samples", "received_at", "TEXT"),
    ):
        if col not in {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {kind}")
    if "review_note" not in {r[1] for r in conn.execute("PRAGMA table_info(trip_summaries)")}:  # M105
        conn.execute("ALTER TABLE trip_summaries ADD COLUMN review_note TEXT")
    # Samples stored before M82 have no arrival time: their own, but never one in the future.
    conn.execute("UPDATE fatigue_samples SET received_at = MIN(ts, ?) WHERE received_at IS NULL", (now_iso(),))


def now_iso() -> str:
    """The current time in UTC as an ISO 8601 string."""
    return datetime.now(UTC).isoformat()


def connect(db_path: str) -> sqlite3.Connection:
    """Open the SQLite database (WAL, foreign keys on), creating its directory when needed."""
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: str) -> None:
    """Create the tables, apply the migrations and restrict the file to its owner."""
    with closing(db_path) as conn:
        conn.executescript(SCHEMA)
        migrate(conn)
    restrict_file(db_path)


def restrict_file(db_path: str) -> None:
    """Owner-only access to the database file (M48): another account on the host must not read drivers'
    metadata. SQLite gives its -wal / -shm files the same mode. Encryption at rest is the host's disk
    encryption (docs/data-policy.md); this only closes the file to other local users."""
    if db_path == ":memory:" or os.name == "nt":
        return
    for path in (db_path, db_path + "-wal", db_path + "-shm"):
        if os.path.exists(path):
            os.chmod(path, 0o600)


@contextmanager
def closing(db_path: str) -> Iterator[sqlite3.Connection]:
    """Context manager: a connection that is committed on success and always closed."""
    conn = connect(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# --------------------------------------------------------------------------- users / devices


def create_user(conn: sqlite3.Connection, username: str, password_hash: str, role: str, driver_id: str | None) -> None:
    """Insert an account; sqlite3.IntegrityError when the username exists."""
    conn.execute(
        "INSERT INTO users (username, password_hash, role, driver_id, created_at) VALUES (?, ?, ?, ?, ?)",
        (username, password_hash, role, driver_id, now_iso()),
    )


def get_user(conn: sqlite3.Connection, username: str) -> sqlite3.Row | None:
    """The account row of `username`, or None."""
    return conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()


def list_users(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Username, role and driver_id of every account, by username."""
    return conn.execute("SELECT username, role, driver_id FROM users ORDER BY username").fetchall()


def create_device(conn: sqlite3.Connection, device_id: str, key_hash: str, driver_id: str | None) -> None:
    """Insert a device with the hash of its key; sqlite3.IntegrityError when the device_id exists."""
    conn.execute(
        "INSERT INTO devices (device_id, key_hash, driver_id, created_at) VALUES (?, ?, ?, ?)",
        (device_id, key_hash, driver_id, now_iso()),
    )


def get_device_by_key_hash(conn: sqlite3.Connection, key_hash: str) -> sqlite3.Row | None:
    """The device row that owns this key hash, or None."""
    return conn.execute("SELECT * FROM devices WHERE key_hash = ?", (key_hash,)).fetchone()


# --------------------------------------------------------------------------- fleet overview (M33)


def touch_device(conn: sqlite3.Connection, device_id: str, driver_id: str | None) -> None:
    """The device (or a user's browser) just posted something: it is alive now (server time)."""
    conn.execute(
        """INSERT INTO device_status (device_id, driver_id, last_seen) VALUES (?, ?, ?)
           ON CONFLICT (device_id) DO UPDATE SET driver_id = excluded.driver_id, last_seen = excluded.last_seen""",
        (device_id, driver_id, now_iso()),
    )


def apply_heartbeat(conn: sqlite3.Connection, device_id: str, h: dict[str, Any], received_at: str) -> float:
    """Trip / monitoring state from a heartbeat. Devices only ever send their newest one, so the one
    that arrives last is the current state (M82): the device's clock does not decide the order. Returns
    the clock skew stored with it, seconds (server time minus the heartbeat's `ts`)."""
    versions = json.dumps(h["versions"], sort_keys=True) if h.get("versions") else None
    perf = json.dumps(h["perf"], sort_keys=True) if h.get("perf") else None  # M49: the last one that had any
    skew_s = (datetime.fromisoformat(received_at) - datetime.fromisoformat(h["ts"])).total_seconds()
    conn.execute(
        """UPDATE device_status SET trip_id = ?, state = ?, moving = ?, state_ts = ?, clock_skew_s = ?,
                  versions = COALESCE(?, versions), perf = COALESCE(?, perf)
           WHERE device_id = ?""",
        (h["trip_id"], h["state"], h["moving"], received_at, skew_s, versions, perf, device_id),
    )
    return skew_s


def device_clock_skew(conn: sqlite3.Connection, device_id: str) -> float | None:
    """Clock skew of the device's last heartbeat, seconds; None: it never sent one."""
    row = conn.execute("SELECT clock_skew_s FROM device_status WHERE device_id = ?", (device_id,)).fetchone()
    return None if row is None else row["clock_skew_s"]


def fleet_devices(conn: sqlite3.Connection, driver_id: str | None = None) -> list[dict[str, Any]]:
    """Every registered device plus every device heard from (browsers are not registered), by id."""
    rows = conn.execute(
        """SELECT d.device_id, COALESCE(s.driver_id, d.driver_id) AS driver_id,
                  s.last_seen, s.trip_id, s.state, s.moving, s.versions, s.perf, s.clock_skew_s
           FROM devices d LEFT JOIN device_status s ON s.device_id = d.device_id
           UNION ALL
           SELECT s.device_id, s.driver_id, s.last_seen, s.trip_id, s.state, s.moving, s.versions, s.perf,
                  s.clock_skew_s
           FROM device_status s WHERE s.device_id NOT IN (SELECT device_id FROM devices)
           ORDER BY 1"""
    ).fetchall()
    out = [dict(r) for r in rows if driver_id is None or r["driver_id"] == driver_id]
    for d in out:
        d["moving"] = None if d["moving"] is None else bool(d["moving"])
        d["versions"] = json.loads(d["versions"]) if d["versions"] else None
        d["perf"] = json.loads(d["perf"]) if d["perf"] else None
    return out


def fleet_alerts(conn: sqlite3.Connection, since: str | None, until: str | None) -> dict[str, dict[int, int]]:
    """device_id -> {level: alerts} in the period (system events are not alerts)."""
    where, args = _where(since=since, until=until)
    rows = conn.execute(
        f"SELECT device_id, level, COUNT(*) AS n FROM events WHERE {where} AND type != 'system' "
        f"AND {NOT_FORCED} GROUP BY device_id, level",
        args,
    ).fetchall()
    out: dict[str, dict[int, int]] = {}
    for r in rows:
        out.setdefault(r["device_id"], {})[r["level"]] = r["n"]
    return out


def last_event(conn: sqlite3.Connection, device_id: str, since: str | None, until: str | None) -> dict[str, Any] | None:
    """The newest event of a device in [since, until] (ts, type, level, reasons), or None."""
    where, args = _where(device_id=device_id, since=since, until=until)
    row = conn.execute(
        f"SELECT ts, type, level, reasons FROM events WHERE {where} ORDER BY ts DESC LIMIT 1", args
    ).fetchone()
    if row is None:
        return None
    return {**dict(row), "reasons": json.loads(row["reasons"])}


URGENT_REASONS = ("unresponsive", "repeated_l3", "no_answer")  # edge_agent/io/publisher.py URGENT_REASONS


def urgent_event(
    conn: sqlite3.Connection, device_id: str, trip_id: str | None, since: str, max_delay_s: float
) -> dict[str, Any] | None:
    """Newest event that needs a manager now (M44): an L3 alert, or one of URGENT_REASONS. Only of the
    trip the device is on (an old trip's alert is history), never a forced one. "Now" is server time
    (M82): it arrived since `since`, and it was not held back on the device for longer than
    `max_delay_s` (an offline queue emptying is history too). The event's own `ts` is not compared."""
    if trip_id is None:
        return None
    rows = conn.execute(
        f"""SELECT event_id, ts, type, level, reasons FROM events
            WHERE device_id = ? AND trip_id = ? AND received_at >= ? AND (delay_s IS NULL OR delay_s <= ?)
                  AND {NOT_FORCED}
            ORDER BY received_at DESC, id DESC LIMIT 50""",
        (device_id, trip_id, since, max_delay_s),
    ).fetchall()
    for row in rows:
        reasons = json.loads(row["reasons"])
        if row["level"] == 3 or set(reasons) & set(URGENT_REASONS):
            return {**dict(row), "reasons": reasons}
    return None


# --------------------------------------------------------------------------- data policy (M37)


def purge_expired(
    conn: sqlite3.Connection, now: datetime, events_days: int, summaries_days: int, access_log_days: int = 0
) -> dict[str, int]:
    """Delete metadata past its retention period (0 days = keep). Returns rows deleted per table.
    The period runs from when the backend received a row (M82), not from the device's timestamp: a
    device with a wrong clock can neither have its rows deleted at once nor kept past the period."""
    out = {"events": 0, "fatigue_samples": 0, "trip_summaries": 0}
    if access_log_days > 0:  # the access log has a retention period of its own
        cutoff = (now - timedelta(days=access_log_days)).astimezone(UTC).isoformat()
        out["access_log"] = conn.execute("DELETE FROM access_log WHERE ts < ?", (cutoff,)).rowcount
    if events_days > 0:
        cutoff = (now - timedelta(days=events_days)).astimezone(UTC).isoformat()
        out["events"] = conn.execute("DELETE FROM events WHERE received_at < ?", (cutoff,)).rowcount
        samples = conn.execute("DELETE FROM fatigue_samples WHERE received_at < ?", (cutoff,))
        out["fatigue_samples"] = samples.rowcount
    if summaries_days > 0:
        cutoff = (now - timedelta(days=summaries_days)).astimezone(UTC).isoformat()
        out["trip_summaries"] = conn.execute("DELETE FROM trip_summaries WHERE received_at < ?", (cutoff,)).rowcount
    return out


def delete_driver_data(conn: sqlite3.Connection, driver_id: str) -> dict[str, int]:
    """Everything stored about one driver (the driver left, or asks for deletion). Accounts and
    device registrations are not touched. Returns rows deleted per table."""
    return {
        table: conn.execute(f"DELETE FROM {table} WHERE driver_id = ?", (driver_id,)).rowcount
        for table in ("events", "fatigue_samples", "trip_summaries", "device_status")
    }


def delete_user(conn: sqlite3.Connection, username: str) -> bool:
    """Remove an account (the person left). Their stored metadata is a separate decision: delete_driver_data."""
    return conn.execute("DELETE FROM users WHERE username = ?", (username,)).rowcount == 1


# --------------------------------------------------------------------------- a driver's own data (M48)


def export_driver_data(conn: sqlite3.Connection, driver_id: str) -> dict[str, Any]:
    """Everything stored about one driver, as the tables hold it: alerts and system events, per-minute
    samples, trip summaries, and who looked at their data. Numbers and short codes only: nothing else
    was ever stored."""
    events = [dict(r) for r in conn.execute("SELECT * FROM events WHERE driver_id = ? ORDER BY ts", (driver_id,))]
    for e in events:
        for key in ("reasons", "metrics", "tags", "versions"):
            e[key] = json.loads(e[key]) if e.get(key) else None
    samples = [
        dict(r) for r in conn.execute("SELECT * FROM fatigue_samples WHERE driver_id = ? ORDER BY ts", (driver_id,))
    ]
    summaries = [
        dict(r)
        for r in conn.execute("SELECT * FROM trip_summaries WHERE driver_id = ? ORDER BY received_at", (driver_id,))
    ]
    for s in summaries:
        s["summary"] = json.loads(s["summary"])
    return {
        "driver_id": driver_id,
        "events": events,
        "fatigue_samples": samples,
        "trip_summaries": summaries,
        "access_log": query_access_log(conn, about_driver=driver_id, limit=100_000),
        "deletion_requests": deletion_requests(conn, driver_id),
    }


def deletion_requests(conn: sqlite3.Connection, driver_id: str | None = None) -> list[dict[str, Any]]:
    """Newest first; pending ones first when listing every driver's."""
    if driver_id is not None:
        rows = conn.execute("SELECT * FROM deletion_requests WHERE driver_id = ? ORDER BY id DESC", (driver_id,))
    else:
        rows = conn.execute("SELECT * FROM deletion_requests ORDER BY status != 'pending', id DESC LIMIT 500")
    return [dict(r) for r in rows]


def request_deletion(conn: sqlite3.Connection, driver_id: str, username: str) -> dict[str, Any]:
    """The driver's request; one pending request per driver (asking twice returns the first)."""
    row = conn.execute(
        "SELECT * FROM deletion_requests WHERE driver_id = ? AND status = 'pending'", (driver_id,)
    ).fetchone()
    if row is None:
        cur = conn.execute(
            "INSERT INTO deletion_requests (driver_id, requested_by, requested_at) VALUES (?, ?, ?)",
            (driver_id, username, now_iso()),
        )
        row = conn.execute("SELECT * FROM deletion_requests WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


def handle_deletion(
    conn: sqlite3.Connection, request_id: int, status: str, username: str, reason: str | None = None
) -> dict[str, Any] | None:
    """Close a pending request as 'done' or 'refused'. None: no such pending request."""
    cur = conn.execute(
        """UPDATE deletion_requests SET status = ?, handled_by = ?, handled_at = ?, reason = ?
           WHERE id = ? AND status = 'pending'""",
        (status, username, now_iso(), reason, request_id),
    )
    if cur.rowcount != 1:
        return None
    return dict(conn.execute("SELECT * FROM deletion_requests WHERE id = ?", (request_id,)).fetchone())


# --------------------------------------------------------------------------- access log (M41)


def log_access(
    conn: sqlite3.Connection,
    username: str,
    role: str,
    action: str,
    driver_id: str | None = None,
    device_id: str | None = None,
    detail: str | None = None,
) -> None:
    """Append one row: who did what, on whose data (driver_id / device_id None = the whole fleet)."""
    conn.execute(
        "INSERT INTO access_log (ts, username, role, action, driver_id, device_id, detail) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (now_iso(), username, role, action, driver_id, device_id, detail),
    )


def query_access_log(
    conn: sqlite3.Connection,
    driver_id: str | None = None,
    username: str | None = None,
    since: str | None = None,
    about_driver: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Newest first. about_driver: what a driver may see about their own data: reads naming them,
    and reads of the whole fleet (which include them), by anyone but themselves."""
    clauses, args = ["1 = 1"], []
    for column, value in (("driver_id", driver_id), ("username", username)):
        if value is not None:
            clauses.append(f"{column} = ?")
            args.append(value)
    if since is not None:
        clauses.append("ts >= ?")
        args.append(since)
    if about_driver is not None:
        clauses.append(
            "(driver_id = ? OR (driver_id IS NULL AND device_id IS NULL AND action LIKE 'read_%' "
            "AND action != 'read_access_log'))"
        )
        args.append(about_driver)
    rows = conn.execute(
        f"SELECT ts, username, role, action, driver_id, device_id, detail FROM access_log "
        f"WHERE {' AND '.join(clauses)} ORDER BY ts DESC, id DESC LIMIT ?",
        [*args, limit],
    ).fetchall()
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------- events


def insert_event(
    conn: sqlite3.Connection,
    device_id: str,
    driver_id: str | None,
    e: dict[str, Any],
    received_at: str | None = None,
    delay_s: float | None = None,
) -> bool:
    """Insert one event; False if its event_id is already stored (idempotent retries). `delay_s`: how
    long the device held it before it arrived, its clock error taken out (None: not known, M82)."""
    cur = conn.execute(
        """INSERT OR IGNORE INTO events (event_id, device_id, driver_id, trip_id, ts, type, level, reasons,
               drowsy_score, distraction_score, speed_kmh, metrics, received_at, tags, versions, delay_s)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
            received_at or now_iso(),
            json.dumps(e["tags"]) if e.get("tags") else None,
            json.dumps(e["versions"], sort_keys=True) if e.get("versions") else None,
            delay_s,
        ),
    )
    return cur.rowcount == 1


def event_device(conn: sqlite3.Connection, event_id: str) -> str | None:
    """The device that stored this event_id, None when nobody did."""
    row = conn.execute("SELECT device_id FROM events WHERE event_id = ?", (event_id,)).fetchone()
    return None if row is None else row["device_id"]


def apply_feedback(conn: sqlite3.Connection, device_id: str, event_id: str, verdict: str, ts: str) -> bool:
    """Mark an event of this device; False if the device has no such event."""
    cur = conn.execute(
        "UPDATE events SET feedback = ?, feedback_at = ? WHERE event_id = ? AND device_id = ?",
        (verdict, ts, event_id, device_id),
    )
    return cur.rowcount == 1


def insert_sample(
    conn: sqlite3.Connection, device_id: str, driver_id: str | None, s: dict[str, Any], received_at: str | None = None
) -> bool:
    """Insert one per-minute fatigue sample; False when its sample_id is already stored."""
    cur = conn.execute(
        """INSERT OR IGNORE INTO fatigue_samples
               (sample_id, device_id, driver_id, trip_id, ts, drowsy_score, perclos_60s, max_level, off_road_ratio,
                received_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            s["sample_id"],
            device_id,
            driver_id,
            s["trip_id"],
            s["ts"],
            s["drowsy_score"],
            s["perclos_60s"],
            s["max_level"],
            s.get("off_road_ratio"),
            received_at or now_iso(),
        ),
    )
    return cur.rowcount == 1


def upsert_summary(
    conn: sqlite3.Connection, device_id: str, driver_id: str | None, s: dict[str, Any], received_at: str | None = None
) -> bool:
    """Store a trip summary; a re-sent one (offline queue retry) replaces it but keeps the review."""
    now = received_at or now_iso()
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
    """Trip summaries, filtered by driver, device, start time or not yet reviewed."""
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
        f"""SELECT trip_id, device_id, driver_id, received_at, rating, reviewed_by, reviewed_at, review_note, summary
            FROM trip_summaries WHERE {" AND ".join(where)} ORDER BY started_at DESC LIMIT ?""",
        [*args, limit],
    ).fetchall()
    return [_summary_row(r) for r in rows]


def get_summary(
    conn: sqlite3.Connection, device_id: str, trip_id: str, driver_id: str | None = None
) -> dict[str, Any] | None:
    """The summary of one trip, or None. With `driver_id`, only when it belongs to that driver."""
    sql = """SELECT trip_id, device_id, driver_id, received_at, rating, reviewed_by, reviewed_at, review_note, summary
             FROM trip_summaries WHERE device_id = ? AND trip_id = ?"""
    args: list[Any] = [device_id, trip_id]
    if driver_id is not None:
        sql += " AND driver_id = ?"
        args.append(driver_id)
    row = conn.execute(sql, args).fetchone()
    return None if row is None else _summary_row(row)


def review_summary(
    conn: sqlite3.Connection, device_id: str, trip_id: str, username: str, note: str | None = None
) -> bool:
    """Mark a trip summary as read by `username`; False when there is no such summary. `note`: what the
    reviewer tells the driver (M105), stored when given; None keeps the one already there."""
    cur = conn.execute(
        """UPDATE trip_summaries SET reviewed_by = ?, reviewed_at = ?, review_note = COALESCE(?, review_note)
           WHERE device_id = ? AND trip_id = ?""",
        (username, datetime.now(UTC).isoformat(), note, device_id, trip_id),
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
    """Per-minute fatigue samples matching the filters, oldest first."""
    where, args = _where(**filters)
    rows = conn.execute(
        "SELECT ts, trip_id, device_id, driver_id, drowsy_score, perclos_60s, max_level, off_road_ratio "
        "FROM fatigue_samples "
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
            FROM (SELECT trip_id, device_id, driver_id, ts, 1 AS is_event, level FROM events
                  WHERE {where} AND {NOT_FORCED}
                  UNION ALL
                  SELECT trip_id, device_id, driver_id, ts, 0, max_level FROM fatigue_samples WHERE {where})
            GROUP BY trip_id, device_id ORDER BY end DESC LIMIT ?""",
        [*args, *args, limit],
    ).fetchall()
    return [dict(r) for r in rows]


def event_stats(conn: sqlite3.Connection, **filters: Any) -> dict[str, Any]:
    """Alert counts for the filters: total, false alarms, by level and by reason (no system events)."""
    where, args = _where(**filters)
    # Alerts only: system events (camera_lost / camera_restored) are listed in the log, not counted here.
    rows = conn.execute(
        f"SELECT level, reasons, feedback FROM events WHERE {where} AND type != 'system' AND {NOT_FORCED}", args
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
    """The newest thresholds version (version, values, updated_by, updated_at), or None."""
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
    """Store the thresholds as a new version and return its number."""
    cur = conn.execute(
        "INSERT INTO threshold_versions (vals, updated_by, updated_at) VALUES (?, ?, ?)",
        (json.dumps(values, sort_keys=True), username, now_iso()),
    )
    return int(cur.lastrowid)


# --------------------------------------------------------------------------- thresholds rollout (M47)


def get_thresholds_version(conn: sqlite3.Connection, version: int) -> dict[str, Any] | None:
    """One thresholds version by its number, or None."""
    row = conn.execute("SELECT * FROM threshold_versions WHERE version = ?", (version,)).fetchone()
    if row is None:
        return None
    return {
        "version": row["version"],
        "values": json.loads(row["vals"]),
        "updated_by": row["updated_by"],
        "updated_at": row["updated_at"],
    }


def fleet_thresholds_version(conn: sqlite3.Connection) -> int:
    """The version every device without a pin runs: the rollout's, else the newest (0 = none stored)."""
    row = conn.execute("SELECT fleet_version FROM threshold_rollout WHERE id = 1").fetchone()
    if row is not None:
        return int(row["fleet_version"])
    latest = latest_thresholds(conn)
    return latest["version"] if latest else 0


def set_fleet_thresholds(conn: sqlite3.Connection, version: int, username: str) -> None:
    """Make `version` the one the whole fleet runs."""
    conn.execute(
        """INSERT INTO threshold_rollout (id, fleet_version, updated_by, updated_at) VALUES (1, ?, ?, ?)
           ON CONFLICT (id) DO UPDATE SET fleet_version = excluded.fleet_version,
                                          updated_by = excluded.updated_by, updated_at = excluded.updated_at""",
        (version, username, now_iso()),
    )


def threshold_pins(conn: sqlite3.Connection) -> dict[str, int]:
    """The thresholds version each pinned device runs: {device_id: version}."""
    return {r["device_id"]: int(r["version"]) for r in conn.execute("SELECT device_id, version FROM threshold_pins")}


def pin_thresholds(conn: sqlite3.Connection, device_ids: list[str], version: int, username: str) -> None:
    """Pin these devices to `version` (a trial on part of the fleet)."""
    now = now_iso()
    conn.executemany(
        """INSERT INTO threshold_pins (device_id, version, updated_by, updated_at) VALUES (?, ?, ?, ?)
           ON CONFLICT (device_id) DO UPDATE SET version = excluded.version,
                                                 updated_by = excluded.updated_by, updated_at = excluded.updated_at""",
        [(d, version, username, now) for d in device_ids],
    )


def clear_threshold_pins(conn: sqlite3.Connection) -> int:
    """Remove every pin; returns how many devices were pinned."""
    return conn.execute("DELETE FROM threshold_pins").rowcount


def thresholds_target(conn: sqlite3.Connection, device_id: str | None) -> int:
    """The version this device should run: its pin, else the fleet's."""
    if device_id is not None:
        row = conn.execute("SELECT version FROM threshold_pins WHERE device_id = ?", (device_id,)).fetchone()
        if row is not None:
            return int(row["version"])
    return fleet_thresholds_version(conn)


def threshold_history(conn: sqlite3.Connection, limit: int = 20) -> list[dict[str, Any]]:
    """Newest versions with what an engineer needs before giving one to the whole fleet: which
    devices run it now (last heartbeat), and its alerts / drivers' false-alarm marks so far."""
    rows = conn.execute("SELECT * FROM threshold_versions ORDER BY version DESC LIMIT ?", (limit,)).fetchall()
    fleet = fleet_thresholds_version(conn)
    pins = threshold_pins(conn)
    running: dict[int, list[str]] = {}
    for r in conn.execute("SELECT device_id, versions FROM device_status WHERE versions IS NOT NULL"):
        v = json.loads(r["versions"]).get("thresholds_version")
        if isinstance(v, int):
            running.setdefault(v, []).append(r["device_id"])
    counts = {
        int(r["v"]): (r["n"], r["fa"] or 0)
        for r in conn.execute(
            f"""SELECT json_extract(versions, '$.thresholds_version') AS v, COUNT(*) AS n,
                       SUM(feedback = 'false_alarm') AS fa
                FROM events WHERE versions IS NOT NULL AND type != 'system' AND {NOT_FORCED} GROUP BY v"""
        )
        if r["v"] is not None
    }
    out, previous = [], None
    for row in reversed(rows):  # oldest first, to name what each version changed
        values = json.loads(row["vals"])
        changed = sorted(k for k, v in values.items() if previous is None or previous.get(k) != v)
        previous = values
        n, fa = counts.get(row["version"], (0, 0))
        out.append(
            {
                "version": row["version"],
                "values": values,
                "updated_by": row["updated_by"],
                "updated_at": row["updated_at"],
                "changed": changed,
                "fleet": row["version"] == fleet,
                "pinned_devices": sorted(d for d, v in pins.items() if v == row["version"]),
                "running_devices": sorted(running.get(row["version"], [])),
                "alerts": n,
                "false_alarms": fa,
            }
        )
    return out[::-1]


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
    """Events matching the filters at `min_level` or above, newest first, JSON columns decoded."""
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
        d["tags"] = json.loads(d["tags"]) if d.get("tags") else []
        d["versions"] = json.loads(d["versions"]) if d.get("versions") else None
        out.append(d)
    return out
