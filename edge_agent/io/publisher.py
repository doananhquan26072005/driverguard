"""Block 14 - Metadata publisher.

Sends metadata (never images) to the backend in batches, with an offline queue. Four
kinds of records share the queue and the batches:
- events:   one per emitted alert (`build_event`), plus system events such as the camera
            being lost / back (`build_system_event`: type "system", level 0)
- feedback: the driver pressed "false alarm" on the HUD for an event (`publish_feedback`)
- samples:  one fatigue-timeline point per minute of driving (`build_sample`)
- summaries: one per trip when it ends (block 11 `TripSummary.to_dict()`), for the driver and
            the higher roles

Heartbeat (M33, `build_heartbeat`): "still alive" every `heartbeat_interval_s` and on every change
of the monitoring state, so the backend can tell a vehicle that is running from one that went
quiet. Only the newest one matters, so it never enters the outbox: it is kept in memory and sent
in a POST of its own before the queued records. A backend that does not know it yet refuses it
(422) and it is dropped; the records still go through.

- `publish()` only checks the event and hands it over, so the main loop never waits on the
  network, and not on the disk either: while the sender thread runs, the record waits in memory
  and that thread writes it to the persistent outbox (SQLite file, metadata JSON only) at once,
  before it sends anything. One synchronous write on eMMC storage can take tens of ms, and it
  used to happen on the loop's thread on the very frame that raised the alert. A record is only
  in memory for that moment; without a sender thread (tools, tests) it is written by the caller.
- A background thread flushes up to `batch_size` events every `flush_interval_s`
  (sooner when a full batch is waiting). Events leave the outbox only after the
  backend answered 2xx, so nothing is lost when the network is down or the device
  restarts. Failed attempts back off exponentially up to `backoff_max_s`, each wait stretched by
  up to `backoff_jitter` of itself at random: a fleet that lost the backend together does not
  come back at the same second.
- The outbox file is readable by its owner only, like the backend's database.
- Retries are safe: every event has an event_id and the backend ignores duplicates.
- A batch the backend refuses as invalid (400 / 413 / 422) is retried event by event and
  only the refused events are dropped, so one bad event cannot block the queue.
- The outbox is capped at `max_queue` events (oldest dropped first).
- Privacy guard before anything is queued: binary data, image-like field names and
  base64 / data-URI strings are refused on the device already, by the rules the backend applies
  (edge_agent/io/metadata_guard.py).
"""

from __future__ import annotations

import json
import logging
import os
import random
import threading
import time
import urllib.error
import urllib.request
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from edge_agent.config import PROJECT_ROOT, config_from_dict
from edge_agent.decision.alert_manager import Alert
from edge_agent.decision.pipeline import DecisionResult
from edge_agent.io.metadata_guard import find_image_data

if TYPE_CHECKING:
    import sqlite3

log = logging.getLogger("driverguard.publisher")

DROWSINESS_REASONS = {"microsleep", "unresponsive", "drowsy_score", "trend", "blink_rate"}
# Sent at once instead of with the next batch (M44): the fleet view shows these while they happen.
URGENT_REASONS = {"unresponsive", "repeated_l3", "no_answer"}
DROP_STATUSES = {400, 413, 422}  # the backend will never accept this content

# body (JSON-ready dict) -> HTTP status code; raises OSError when the backend is unreachable
Transport = Callable[[dict[str, Any]], int]
KINDS = {"event": "events", "feedback": "feedback", "sample": "samples", "summary": "summaries"}  # kind -> field
DELIVERED_KEEP = 64  # accepted event_ids remembered for the HUD (M65): a few minutes of events
OWNER_ONLY = 0o600  # mode of the outbox file


@dataclass(frozen=True)
class PublisherConfig:
    batch_size: int = 20
    web_batch_size: int = 100  # the page: records of each kind per POST (the backend's limit)
    flush_interval_s: float = 5.0
    timeout_s: float = 5.0
    outbox_path: str = "data/outbox.db"
    max_queue: int = 10000
    backoff_initial_s: float = 1.0
    backoff_max_s: float = 60.0
    backoff_jitter: float = 0.2  # each retry wait is longer by up to this share of itself, at random
    heartbeat_interval_s: float = 30.0  # 0 = no heartbeat
    heartbeat_stalled_s: float = 10.0  # no frame for this long (camera not reported lost): "stalled"
    config_poll_s: float = 300.0  # ask the backend for tuned thresholds this often (M47); 0 = start-up only

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> PublisherConfig:
        return config_from_dict(cls, d, "publisher")

    def resolved_outbox_path(self) -> str:
        if self.outbox_path == ":memory:":
            return self.outbox_path
        p = Path(self.outbox_path)
        return str(p if p.is_absolute() else PROJECT_ROOT / p)


# --------------------------------------------------------------------------- event building


def check_metadata_only(obj: Any) -> None:
    """Raise ValueError if `obj` could carry image data (device-side privacy guard). The rules are
    the backend's own (edge_agent/io/metadata_guard.py)."""
    problem = find_image_data(obj)
    if problem:
        raise ValueError(f"not metadata ({problem})")


def _round(x: float | None, nd: int = 3) -> float | None:
    return None if x is None else round(float(x), nd)


def is_urgent(event: dict[str, Any]) -> bool:
    """An L3 alert, or one of URGENT_REASONS: do not wait for the flush interval."""
    return event.get("level") == 3 or bool(URGENT_REASONS & set(event.get("reasons") or ()))


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
            "perclos_p80": _round(d.perclos_p80_60s),  # M40: P80 definition, measured next to it, not scored
            "closed_duration": _round(d.closed_duration, 2),
            "blink_rate": _round(d.blink_rate, 1),
            "yawn_count_10min": d.yawn_count_10min,
            "nod_count_5min": d.nod_count_5min,
            "off_road_duration": _round(x.off_road_duration, 2),
            "phone_ratio_2s": _round(x.phone_ratio_2s),
            "phone_kind": x.phone_kind,  # M38: call | text | unknown while a phone is in the driver zone
            "off_road_ratio": _round(x.off_road_ratio),  # M38: share of the glance window off road
            "glance_count": x.glance_count,
            "blink_time_frac": _round(d.blink_time_frac),  # v2: time in blinks (slow blinks)
            "reopen_ratio": _round(d.reopen_ratio, 2),  # v2: eyelid reopening vs the driver's own start
            "brow_raise_count_5min": d.brow_raise_count_5min,  # v2: brows raised to keep the eyes open
            "enrolled": int(r.enrollment.enrolled),  # judged with the driver's own baselines
        },
    }


def build_sample(
    minute_score: float,
    perclos: float | None,
    max_level: int,
    trip_id: str,
    now: datetime | None = None,
    off_road_ratio: float | None = None,
) -> dict[str, Any]:
    """One fatigue-timeline point: drowsy_score averaged over the minute that just ended.
    off_road_ratio: the highest glance-window ratio of that minute (block 8, measured only)."""
    extra = {} if off_road_ratio is None else {"off_road_ratio": _round(off_road_ratio)}
    return {
        **extra,
        "sample_id": str(uuid.uuid4()),
        "ts": (now or datetime.now(UTC)).isoformat(),
        "trip_id": trip_id,
        "drowsy_score": _round(min(max(minute_score, 0.0), 100.0), 1),
        "perclos_60s": _round(perclos),
        "max_level": max_level,
    }


def build_system_event(
    reason: str,
    trip_id: str,
    speed_kmh: float | None = None,
    now: datetime | None = None,
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Device status change: camera_lost / camera_restored and monitoring_unavailable /
    monitoring_restored (the driver is (not) monitored from now on), driver_enrolled (from now on
    with the driver's own baselines)."""
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
        "metrics": dict(metrics or {}),
    }


def build_enrolled_event(r: DecisionResult, trip_id: str, now: datetime | None = None) -> dict[str, Any]:
    """Driver enrollment done: how long it took and how many steps were redone. Never the profile."""
    e = r.enrollment
    metrics = {"enroll_s": _round(e.duration_s, 1), "enroll_redo": e.attempts}
    return build_system_event("driver_enrolled", trip_id, r.context.speed_kmh, now, metrics)


# Loop timings a caller may attach to the heartbeat (M49; the page's frontend/src/live/perf.ts, the
# backend's schemas.PerfIn): stage -> p50 / p95 / max in milliseconds over the last seconds. No name
# here may contain a metadata_guard.FORBIDDEN_KEY_PARTS word ("total", not "frame"): the image guard reads key names.
PERF_STAGES = ("camera_lag", "capture", "landmarks", "measure", "yolo_prep", "python", "total", "yolo", "yolo_age")
PERF_MAX_MS = 600_000.0
PERF_DELEGATES = ("GPU", "CPU")
PERF_GPU_KINDS = ("hardware", "software", "none")  # what draws WebGL on the page (M51)
PERF_YOLO_PROVIDERS = ("webgpu", "wasm")  # where the page runs the phone detector (M67)


def perf_record(raw: Any) -> dict[str, Any] | None:
    """What the loop measured about itself, cleaned for the heartbeat: known stages, finite numbers in
    range, nothing else. None when there is nothing usable: a heartbeat must never be refused by the
    backend because of its timings."""
    if not isinstance(raw, dict):
        return None

    def count(key: str, top: int) -> int | None:
        v = raw.get(key)
        return int(v) if isinstance(v, int | float) and not isinstance(v, bool) and 0 <= v <= top else None

    stages: dict[str, dict[str, float]] = {}
    given = raw.get("stages_ms")
    for name in PERF_STAGES:
        s = given.get(name) if isinstance(given, dict) else None
        if not isinstance(s, dict):
            continue
        values = [s.get(k) for k in ("p50", "p95", "max")]
        if all(isinstance(v, int | float) and not isinstance(v, bool) and 0 <= v <= PERF_MAX_MS for v in values):
            stages[name] = {k: round(float(v), 1) for k, v in zip(("p50", "p95", "max"), values, strict=True)}
    samples = count("samples", 100_000)
    if not stages or not samples:
        return None
    delegate = raw.get("landmarks_delegate")
    gpu = raw.get("gpu")
    provider = raw.get("yolo_provider")
    yolo_threads = count("yolo_threads", 64)
    return {
        "samples": samples,
        "stages_ms": stages,
        "landmarks_delegate": delegate if delegate in PERF_DELEGATES else None,
        "gpu": gpu if gpu in PERF_GPU_KINDS else None,
        "yolo_threads": yolo_threads or None,
        "yolo_provider": provider if provider in PERF_YOLO_PROVIDERS else None,
        "camera_delivered": count("camera_delivered", 10_000_000),
        "camera_dropped": count("camera_dropped", 10_000_000),
    }


def build_heartbeat(
    state: str,
    trip_id: str,
    moving: bool | None,
    now: datetime | None = None,
    versions: dict[str, Any] | None = None,
    perf: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Still alive: the trip, the monitoring state (edge_agent.runtime.MONITOR_STATES) and whether the
    vehicle moves (None: speed unknown). No position, no measurement of the driver.
    versions: what this device runs (edge_agent/version.py), left out when not given.
    perf: the loop's own timings (`perf_record`), left out when not given."""
    beat = {"ts": (now or datetime.now(UTC)).isoformat(), "trip_id": trip_id, "state": state, "moving": moving}
    if versions is not None:
        beat["versions"] = versions
    if perf is not None:
        beat["perf"] = perf
    return beat


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
        # Imported here: the page (Pyodide) builds its records with this module and has no outbox,
        # so it does not have to download the sqlite3 package.
        import sqlite3

        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS outbox (id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT NOT NULL)"
        )
        self._conn.commit()
        if path != ":memory:" and os.name != "nt":
            try:  # drivers' metadata: closed to the other accounts of the device
                os.chmod(path, OWNER_ONLY)
            except OSError as e:
                log.warning("cannot restrict %s to its owner: %s", path, e)
        self._lock = threading.Lock()
        self._n = self._conn.execute("SELECT COUNT(*) FROM outbox").fetchone()[0]  # rows, kept in step below

    def put(self, event: dict[str, Any], max_queue: int) -> int:
        """Append; returns how many old events were dropped to respect max_queue."""
        return self.put_many([event], max_queue)

    def put_many(self, events: list[dict[str, Any]], max_queue: int) -> int:
        """Append in one transaction; returns how many old events were dropped to respect max_queue."""
        if not events:
            return 0
        with self._lock:
            self._conn.executemany("INSERT INTO outbox (event) VALUES (?)", [(json.dumps(e),) for e in events])
            excess = max(self._n + len(events) - max_queue, 0)
            if excess:
                self._conn.execute(
                    "DELETE FROM outbox WHERE id IN (SELECT id FROM outbox ORDER BY id LIMIT ?)", (excess,)
                )
            self._conn.commit()
            self._n += len(events) - excess
            return excess

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
            cur = self._conn.executemany("DELETE FROM outbox WHERE id = ?", [(i,) for i in ids])
            self._conn.commit()
            self._n -= cur.rowcount

    def count(self) -> int:
        """Rows in the outbox. Counted once when it is opened, then kept in step: no query per record."""
        with self._lock:
            return self._n

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
        jitter: Callable[[], float] = random.random,
    ) -> None:
        """jitter: a number in [0, 1) for each retry wait (see `backoff_jitter`); tests hand in a fixed one."""
        self.config = config or PublisherConfig()
        self.device_id = device_id
        self._transport = transport
        self._clock = clock
        self._jitter = jitter
        self._outbox = Outbox(self.config.resolved_outbox_path())
        # Records the loop handed over that the sender thread has not written to the outbox yet.
        self._pending: deque[dict[str, Any]] = deque()
        self._pending_lock = threading.Lock()
        self._flush_now = threading.Event()  # a full batch or an urgent event is waiting
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
        self._heartbeat: dict[str, Any] | None = None  # newest one not sent yet (never in the outbox)
        self._heartbeat_refused = False
        # event_ids the backend accepted, newest last (M65: the HUD says "Đã báo cho quản lý" only then)
        self._delivered: deque[str] = deque(maxlen=DELIVERED_KEEP)
        self._delivered_lock = threading.Lock()  # not _send_lock: that one is held during network I/O

    # ------------------------------------------------------------------ API for the main loop
    def publish(self, event: dict[str, Any]) -> None:
        self._enqueue("event", event)

    def publish_feedback(self, event_id: str) -> None:
        """The driver marked this alert as a false alarm."""
        self._enqueue("feedback", build_feedback(event_id))

    def publish_sample(self, sample: dict[str, Any]) -> None:
        self._enqueue("sample", sample)

    def publish_summary(self, summary: dict[str, Any]) -> None:
        """The trip ended: its summary (block 11), for the driver and the higher roles."""
        self._enqueue("summary", summary)

    def publish_record(self, kind: str, data: dict[str, Any]) -> None:
        """A record built elsewhere (edge_agent.runtime): kind "event", "sample", "feedback", "summary",
        or "heartbeat" (kept apart: only the newest one is sent)."""
        if kind == "heartbeat":
            check_metadata_only(data)
            self._heartbeat = data
            return
        if kind not in KINDS:
            raise ValueError(f"unknown record kind {kind!r}")
        self._enqueue(kind, data)

    def _enqueue(self, kind: str, data: dict[str, Any]) -> None:
        check_metadata_only(data)
        with self._pending_lock:
            self._pending.append({"kind": kind, "data": data})
            overflow = len(self._pending) - self.config.max_queue  # the disk is not taking them
            if overflow > 0:
                self._pending.popleft()
                self.dropped += 1
        if self._thread is None:
            self._persist()  # no sender thread (tools, tests): written here
        if self.queued >= self.config.batch_size or (kind == "event" and is_urgent(data)):
            self._flush_now.set()  # a full batch, or an alert that cannot wait for the flush interval (M44)
        self._wake.set()  # the sender thread writes it to the outbox now, whenever it sends

    def _persist(self) -> None:
        """Write the records handed over since the last call to the outbox, in one transaction."""
        with self._pending_lock:
            records = list(self._pending)
            self._pending.clear()
        overflow = self._outbox.put_many(records, self.config.max_queue)
        if overflow:
            self.dropped += overflow
            log.warning("outbox full: dropped %d oldest events", overflow)

    @property
    def queued(self) -> int:
        if self._queued_at_stop is not None:  # outbox already closed
            return self._queued_at_stop
        return len(self._pending) + self._outbox.count()

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
        self._persist()  # what the thread had not written yet
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

    def _send_heartbeat(self) -> bool:
        """Send the waiting heartbeat, if any. False: the backend is unreachable or failing, try later."""
        heartbeat = self._heartbeat
        if heartbeat is None:
            return True
        try:
            status = self._transport({"device_id": self.device_id, "heartbeat": heartbeat})
        except OSError as e:
            log.info("backend unreachable: %s", e)
            status = None
        if status is not None and 200 <= status < 300:
            self._succeeded(0)
        elif status in DROP_STATUSES:  # a backend older than M33: go on without heartbeats
            if not self._heartbeat_refused:
                log.warning("backend refused the heartbeat (HTTP %s): it will not see this device as online", status)
            self._heartbeat_refused = True
        else:
            self._failed(status)
            return False
        if self._heartbeat is heartbeat:  # a newer one may have arrived meanwhile
            self._heartbeat = None
        return True

    def flush_once(self) -> int:
        """Try to send one batch. Returns the number of events the backend accepted."""
        with self._send_lock:
            self._persist()
            if self._clock() < self._next_attempt:
                return 0
            if not self._send_heartbeat():
                return 0
            rows = self._outbox.peek(self.config.batch_size)
            if not rows:
                return 0
            status = self._send([rec for _, rec in rows])
            if status is not None and 200 <= status < 300:
                self._outbox.delete([i for i, _ in rows])
                self._mark_delivered([rec for _, rec in rows])
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
                self._mark_delivered([rec])
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

    def _mark_delivered(self, records: list[dict[str, Any]]) -> None:
        ids = [
            rec["data"]["event_id"]
            for rec in records
            if rec.get("kind") == "event" and "event_id" in rec.get("data", {})
        ]
        with self._delivered_lock:
            self._delivered.extend(ids)

    def delivered(self, event_id: str) -> bool:
        """The backend accepted this event (one of the last DELIVERED_KEEP)."""
        with self._delivered_lock:
            return event_id in self._delivered

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
        self._next_attempt = self._clock() + self._backoff * (1.0 + cfg.backoff_jitter * self._jitter())
        if status is not None:
            log.warning("backend answered HTTP %s, retrying in %.0f s", status, self._backoff)

    def _run(self) -> None:
        due = time.monotonic() + self.config.flush_interval_s
        while not self._stop.is_set():
            self._wake.wait(max(due - time.monotonic(), 0.0))
            self._wake.clear()
            if self._stop.is_set():
                break
            self._persist()  # every wake-up: a record handed over is on disk before anything else
            if not self._flush_now.is_set() and time.monotonic() < due:
                continue  # woken only to write
            self._flush_now.clear()
            due = time.monotonic() + self.config.flush_interval_s
            # Drain full batches while the backend keeps accepting.
            while self.flush_once() >= self.config.batch_size and not self._stop.is_set():
                pass
