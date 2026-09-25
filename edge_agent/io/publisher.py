"""Block 14 - Metadata publisher.

Sends metadata (never images) to the backend in batches, with an offline queue. Three
kinds of records share the queue and the batches:
- events:   one per emitted alert (`build_event`), plus system events such as the camera
            being lost / back (`build_system_event`: type "system", level 0)
- feedback: the driver pressed "false alarm" on the HUD for an event (`publish_feedback`)
- samples:  one fatigue-timeline point per minute of driving (`build_sample`)

- `publish()` only checks the event and appends it to a persistent outbox (SQLite file,
  metadata JSON only), so the main loop never waits on the network.
- A background thread flushes up to `batch_size` events every `flush_interval_s`
  (sooner when a full batch is waiting). Events leave the outbox only after the
  backend answered 2xx, so nothing is lost when the network is down or the device
  restarts. Failed attempts back off exponentially up to `backoff_max_s`.
- Retries are safe: every event has an event_id and the backend ignores duplicates.
- A batch the backend refuses as invalid (400 / 413 / 422) is retried event by event and
  only the refused events are dropped, so one bad event cannot block the queue.
- The outbox is capped at `max_queue` events (oldest dropped first).
- Privacy guard before anything is queued: binary data, image-like field names and
  base64 / data-URI strings are refused on the device already.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import threading
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from edge_agent.config import PROJECT_ROOT, config_from_dict
from edge_agent.decision.alert_manager import Alert
from edge_agent.decision.pipeline import DecisionResult

log = logging.getLogger("driverguard.publisher")

DROWSINESS_REASONS = {"microsleep", "drowsy_score", "trend", "blink_rate"}
DROP_STATUSES = {400, 413, 422}  # the backend will never accept this content
FORBIDDEN_KEY_PARTS = ("image", "img", "frame", "photo", "picture", "snapshot", "thumbnail", "jpeg", "png", "crop")
BASE64_RUN = re.compile(r"[A-Za-z0-9+/_-]{64,}={0,2}")

# body (JSON-ready dict) -> HTTP status code; raises OSError when the backend is unreachable
Transport = Callable[[dict[str, Any]], int]
KINDS = {"event": "events", "feedback": "feedback", "sample": "samples"}  # record kind -> batch field


@dataclass(frozen=True)
class PublisherConfig:
    batch_size: int = 20
    flush_interval_s: float = 5.0
    timeout_s: float = 5.0
    outbox_path: str = "data/outbox.db"
    max_queue: int = 10000
    backoff_initial_s: float = 1.0
    backoff_max_s: float = 60.0

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> PublisherConfig:
        return config_from_dict(cls, d, "publisher")

    def resolved_outbox_path(self) -> str:
        if self.outbox_path == ":memory:":
            return self.outbox_path
        p = Path(self.outbox_path)
        return str(p if p.is_absolute() else PROJECT_ROOT / p)


# --------------------------------------------------------------------------- event building


def check_metadata_only(obj: Any, path: str = "$") -> None:
    """Raise ValueError if `obj` could carry image data (device-side privacy guard)."""
    if isinstance(obj, (bytes, bytearray, memoryview)) or hasattr(obj, "__array__"):
        raise ValueError(f"{path}: binary / array data is not metadata")
    if isinstance(obj, dict):
        for k, v in obj.items():
            if any(part in str(k).lower() for part in FORBIDDEN_KEY_PARTS):
                raise ValueError(f"{path}.{k}: image-like field name")
            check_metadata_only(v, f"{path}.{k}")
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            check_metadata_only(v, f"{path}[{i}]")
    elif isinstance(obj, str) and (";base64," in obj or BASE64_RUN.search(obj)):
        raise ValueError(f"{path}: base64-like string")


def _round(x: float | None, nd: int = 3) -> float | None:
    return None if x is None else round(float(x), nd)


def build_event(alert: Alert, r: DecisionResult, trip_id: str, now: datetime | None = None) -> dict[str, Any]:
    """Alert + decision state of that frame -> event metadata (schema of POST /api/v1/events)."""
    reasons = list(alert.reasons)
    kind = "drowsiness" if (not reasons or reasons[0] in DROWSINESS_REASONS) else "distraction"
    d, x = r.drowsiness, r.distraction
    return {
        "event_id": str(uuid.uuid4()),
        "ts": (now or datetime.now(UTC)).isoformat(),
        "trip_id": trip_id,
        "type": kind,
        "level": alert.level,
        "reasons": reasons,
        "drowsy_score": _round(alert.drowsy_score, 1),
        "distraction_score": _round(alert.distraction_score, 1),
        "speed_kmh": _round(r.context.speed_kmh, 1),
        "metrics": {
            "perclos_60s": _round(d.perclos_60s),
            "closed_duration": _round(d.closed_duration, 2),
            "blink_rate": _round(d.blink_rate, 1),
            "yawn_count_10min": d.yawn_count_10min,
            "nod_count_5min": d.nod_count_5min,
            "off_road_duration": _round(x.off_road_duration, 2),
            "phone_ratio_2s": _round(x.phone_ratio_2s),
        },
    }


def build_sample(
    minute_score: float, perclos: float | None, max_level: int, trip_id: str, now: datetime | None = None
) -> dict[str, Any]:
    """One fatigue-timeline point: drowsy_score averaged over the minute that just ended."""
    return {
        "sample_id": str(uuid.uuid4()),
        "ts": (now or datetime.now(UTC)).isoformat(),
        "trip_id": trip_id,
        "drowsy_score": _round(min(max(minute_score, 0.0), 100.0), 1),
        "perclos_60s": _round(perclos),
        "max_level": max_level,
    }


def build_system_event(
    reason: str, trip_id: str, speed_kmh: float | None = None, now: datetime | None = None
) -> dict[str, Any]:
    """Device status change (camera_lost / camera_restored): the driver is (not) monitored from now on."""
    return {
        "event_id": str(uuid.uuid4()),
        "ts": (now or datetime.now(UTC)).isoformat(),
        "trip_id": trip_id,
        "type": "system",
        "level": 0,  # not a driver risk level; the dashboard shows it by its reason
        "reasons": [reason],
        "drowsy_score": 0.0,
        "distraction_score": 0.0,
        "speed_kmh": _round(speed_kmh, 1),
        "metrics": {},
    }


def build_feedback(event_id: str, now: datetime | None = None) -> dict[str, Any]:
    return {"event_id": event_id, "verdict": "false_alarm", "ts": (now or datetime.now(UTC)).isoformat()}


def batch_body(device_id: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    """Queue records ({"kind", "data"}) -> POST /api/v1/events body; empty lists are left out."""
    body: dict[str, Any] = {"device_id": device_id}
    for rec in records:
        body.setdefault(KINDS[rec["kind"]], []).append(rec["data"])
    return body


# --------------------------------------------------------------------------- persistent outbox


class Outbox:
    """FIFO of {"kind", "data"} records as JSON in SQLite. Thread-safe."""

    def __init__(self, path: str) -> None:
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS outbox (id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT NOT NULL)"
        )
        self._conn.commit()
        self._lock = threading.Lock()

    def put(self, event: dict[str, Any], max_queue: int) -> int:
        """Append; returns how many old events were dropped to respect max_queue."""
        with self._lock:
            self._conn.execute("INSERT INTO outbox (event) VALUES (?)", (json.dumps(event),))
            excess = self._count() - max_queue
            if excess > 0:
                self._conn.execute(
                    "DELETE FROM outbox WHERE id IN (SELECT id FROM outbox ORDER BY id LIMIT ?)", (excess,)
                )
            self._conn.commit()
            return max(excess, 0)

    def peek(self, n: int) -> list[tuple[int, dict[str, Any]]]:
        with self._lock:
            rows = self._conn.execute("SELECT id, event FROM outbox ORDER BY id LIMIT ?", (n,)).fetchall()
        out = []
        for i, raw in rows:
            rec = json.loads(raw)
            if "kind" not in rec:  # queued by the M5 version: a bare event
                rec = {"kind": "event", "data": rec}
            out.append((i, rec))
        return out

    def delete(self, ids: list[int]) -> None:
        if not ids:
            return
        with self._lock:
            self._conn.executemany("DELETE FROM outbox WHERE id = ?", [(i,) for i in ids])
            self._conn.commit()

    def _count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM outbox").fetchone()[0]

    def count(self) -> int:
        with self._lock:
            return self._count()

    def close(self) -> None:
        with self._lock:
            self._conn.close()


# --------------------------------------------------------------------------- transport


def http_transport(base_url: str, device_key: str, timeout_s: float) -> Transport:
    url = base_url.rstrip("/") + "/api/v1/events"

    def send(body: dict[str, Any]) -> int:
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "X-Device-Key": device_key},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                return resp.status
        except urllib.error.HTTPError as e:  # got an answer: 4xx / 5xx
            return e.code

    return send


# --------------------------------------------------------------------------- publisher


class MetadataPublisher:
    def __init__(
        self,
        device_id: str,
        transport: Transport,
        config: PublisherConfig | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config or PublisherConfig()
        self.device_id = device_id
        self._transport = transport
        self._clock = clock
        self._outbox = Outbox(self.config.resolved_outbox_path())
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._send_lock = threading.Lock()
        self._backoff = 0.0
        self._next_attempt = 0.0
        self.sent = 0
        self.dropped = 0  # refused by the backend or pushed out of a full queue
        self.failed_attempts = 0
        self.online: bool | None = None  # None until the first attempt
        self._queued_at_stop: int | None = None

    # ------------------------------------------------------------------ API for the main loop
    def publish(self, event: dict[str, Any]) -> None:
        self._enqueue("event", event)

    def publish_feedback(self, event_id: str) -> None:
        """The driver marked this alert as a false alarm."""
        self._enqueue("feedback", build_feedback(event_id))

    def publish_sample(self, sample: dict[str, Any]) -> None:
        self._enqueue("sample", sample)

    def _enqueue(self, kind: str, data: dict[str, Any]) -> None:
        check_metadata_only(data)
        overflow = self._outbox.put({"kind": kind, "data": data}, self.config.max_queue)
        if overflow:
            self.dropped += overflow
            log.warning("outbox full: dropped %d oldest events", overflow)
        if self._outbox.count() >= self.config.batch_size:
            self._wake.set()

    @property
    def queued(self) -> int:
        if self._queued_at_stop is not None:  # outbox already closed
            return self._queued_at_stop
        return self._outbox.count()

    def start(self) -> MetadataPublisher:
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name="MetadataPublisher", daemon=True)
            self._thread.start()
        return self

    def stop(self, final_flush: bool = True) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout=self.config.timeout_s + 2.0)
            self._thread = None
        if final_flush:
            self._next_attempt = 0.0
            self.flush_once()  # best effort; whatever is left stays in the outbox for next start
        self._queued_at_stop = self._outbox.count()
        self._outbox.close()

    def __enter__(self) -> MetadataPublisher:
        return self.start()

    def __exit__(self, *exc: object) -> None:
        self.stop()

    # ------------------------------------------------------------------ sending
    def _send(self, records: list[dict[str, Any]]) -> int | None:
        try:
            return self._transport(batch_body(self.device_id, records))
        except OSError as e:
            log.info("backend unreachable: %s", e)
            return None

    def flush_once(self) -> int:
        """Try to send one batch. Returns the number of events the backend accepted."""
        with self._send_lock:
            if self._clock() < self._next_attempt:
                return 0
            rows = self._outbox.peek(self.config.batch_size)
            if not rows:
                return 0
            status = self._send([rec for _, rec in rows])
            if status is not None and 200 <= status < 300:
                self._outbox.delete([i for i, _ in rows])
                self._succeeded(len(rows))
                return len(rows)
            if status in DROP_STATUSES:
                return self._send_one_by_one(rows)
            self._failed(status)
            return 0

    def _send_one_by_one(self, rows: list[tuple[int, dict[str, Any]]]) -> int:
        accepted = 0
        for row_id, rec in rows:
            status = self._send([rec])
            if status is not None and 200 <= status < 300:
                accepted += 1
            elif status in DROP_STATUSES:
                self.dropped += 1
                log.error("backend refused a %s record (HTTP %s): dropped", rec["kind"], status)
            else:
                self.sent += accepted
                self._failed(status)
                return accepted  # network went away mid-way: keep the rest for later
            self._outbox.delete([row_id])
        self._succeeded(accepted)
        return accepted

    def _succeeded(self, n: int) -> None:
        self.sent += n
        self.online = True
        self._backoff = 0.0
        self._next_attempt = 0.0

    def _failed(self, status: int | None) -> None:
        self.online = False
        self.failed_attempts += 1
        cfg = self.config
        self._backoff = min(max(cfg.backoff_initial_s, self._backoff * 2), cfg.backoff_max_s)
        self._next_attempt = self._clock() + self._backoff
        if status is not None:
            log.warning("backend answered HTTP %s, retrying in %.0f s", status, self._backoff)

    def _run(self) -> None:
        while not self._stop.is_set():
            self._wake.wait(self.config.flush_interval_s)
            self._wake.clear()
            if self._stop.is_set():
                break
            # Drain full batches while the backend keeps accepting.
            while self.flush_once() >= self.config.batch_size and not self._stop.is_set():
                pass
