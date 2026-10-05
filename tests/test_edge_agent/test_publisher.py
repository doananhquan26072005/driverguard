"""Block 14: batching, offline queue, retries, privacy guard, and end-to-end with the backend."""

import time
import uuid

import numpy as np
import pytest

from edge_agent.io.publisher import (
    MetadataPublisher,
    Outbox,
    PublisherConfig,
    batch_body,
    build_event,
    build_sample,
    check_metadata_only,
)


def event(i=0, **extra):
    e = {
        "event_id": str(uuid.uuid4()),
        "ts": "2026-09-24T08:00:00+00:00",
        "trip_id": "trip-1",
        "type": "distraction",
        "level": 2,
        "reasons": ["phone"],
        "drowsy_score": 0.0,
        "distraction_score": 100.0,
        "speed_kmh": 50.0,
        "metrics": {"phone_ratio_2s": 0.7},
        "seq": i,
    }
    e.update(extra)
    return e


class FakeBackend:
    """Transport stub: records batches; `down` raises like an unreachable server."""

    def __init__(self):
        self.batches = []
        self.down = False
        self.status = 200
        self.reject_seq = set()  # events with these seq get 422

    def __call__(self, body):
        if self.down:
            raise OSError("connection refused")
        if any(e.get("seq") in self.reject_seq for e in body["events"]):
            return 422
        if self.status >= 300:
            return self.status
        self.batches.append(body)
        return 200

    @property
    def received(self):
        return [e["seq"] for b in self.batches for e in b["events"]]


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


@pytest.fixture
def outbox_path(tmp_path):
    return str(tmp_path / "outbox.db")


def make(outbox_path, backend, clock=None, **cfg):
    config = PublisherConfig(outbox_path=outbox_path, **{"batch_size": 3, **cfg})
    return MetadataPublisher("cam-001", backend, config, clock=clock or Clock())


def test_sends_in_batches_in_order(outbox_path):
    backend = FakeBackend()
    pub = make(outbox_path, backend)
    for i in range(7):
        pub.publish(event(i))
    while pub.flush_once():
        pass
    assert [len(b["events"]) for b in backend.batches] == [3, 3, 1]
    assert backend.received == list(range(7))
    assert all(b["device_id"] == "cam-001" for b in backend.batches)
    assert pub.queued == 0 and pub.sent == 7 and pub.online is True


def test_offline_keeps_events_and_backs_off(outbox_path):
    backend, clock = FakeBackend(), Clock()
    pub = make(outbox_path, backend, clock, backoff_initial_s=1.0, backoff_max_s=8.0)
    backend.down = True
    for i in range(5):
        pub.publish(event(i))
    delays = []
    for _ in range(6):
        clock.t = pub._next_attempt
        pub.flush_once()
        delays.append(pub._backoff)
    assert delays == [1.0, 2.0, 4.0, 8.0, 8.0, 8.0]  # exponential, capped
    assert pub.queued == 5 and pub.online is False
    assert pub.flush_once() == 0  # still inside the backoff window: no attempt
    backend.down = False
    clock.t = pub._next_attempt
    while pub.flush_once():
        pass
    assert backend.received == [0, 1, 2, 3, 4] and pub.queued == 0 and pub.online is True


def test_server_error_is_retried_not_dropped(outbox_path):
    backend = FakeBackend()
    backend.status = 503
    pub = make(outbox_path, backend)
    pub.publish(event(0))
    assert pub.flush_once() == 0
    assert pub.queued == 1 and pub.dropped == 0


def test_queue_survives_restart(outbox_path):
    backend = FakeBackend()
    backend.down = True
    pub = make(outbox_path, backend)
    for i in range(4):
        pub.publish(event(i))
    pub.stop()  # final flush fails, events stay on disk
    assert pub.queued == 4
    backend.down = False
    pub2 = make(outbox_path, backend)
    assert pub2.queued == 4
    while pub2.flush_once():
        pass
    assert backend.received == [0, 1, 2, 3]
    pub2.stop()


def test_refused_event_dropped_alone(outbox_path):
    backend = FakeBackend()
    backend.reject_seq = {1}
    pub = make(outbox_path, backend)
    for i in range(3):
        pub.publish(event(i))
    assert pub.flush_once() == 2
    assert backend.received == [0, 2] and pub.dropped == 1 and pub.queued == 0


def test_queue_is_capped(outbox_path):
    pub = make(outbox_path, FakeBackend(), max_queue=5, batch_size=100)
    for i in range(8):
        pub.publish(event(i))
    assert pub.queued == 5 and pub.dropped == 3
    assert [r["data"]["seq"] for _, r in pub._outbox.peek(10)] == [3, 4, 5, 6, 7]  # oldest dropped


def test_background_thread_flushes(outbox_path):
    backend = FakeBackend()
    config = PublisherConfig(outbox_path=outbox_path, batch_size=2, flush_interval_s=0.05)
    with MetadataPublisher("cam-001", backend, config) as pub:
        for i in range(5):
            pub.publish(event(i))
        deadline = time.monotonic() + 2.0
        while pub.queued and time.monotonic() < deadline:
            time.sleep(0.02)
    assert backend.received == [0, 1, 2, 3, 4]


def test_publish_does_not_block_when_backend_hangs(outbox_path):
    def slow(body):
        time.sleep(1.0)
        return 200

    config = PublisherConfig(outbox_path=outbox_path, batch_size=1, flush_interval_s=0.01)
    pub = MetadataPublisher("cam-001", slow, config).start()
    t0 = time.perf_counter()
    for i in range(20):
        pub.publish(event(i))
    assert time.perf_counter() - t0 < 0.5
    pub.stop(final_flush=False)


# ---------------------------------------------------------------- privacy guard (device side)


@pytest.mark.parametrize(
    "bad",
    [
        {"image": "x"},
        {"face_crop": 1},
        {"metrics": {"frame": 1}},
        {"trip_id": "data:image/jpeg;base64,/9j/4AAQ"},
        {"trip_id": "QUJD" * 20},
        {"blob": b"\xff\xd8"},
        {"metrics": {"x": np.zeros((2, 2), np.uint8)}},
    ],
)
def test_privacy_guard_refuses_image_data(outbox_path, bad):
    pub = make(outbox_path, FakeBackend())
    with pytest.raises(ValueError):
        pub.publish(event(0, **bad))
    assert pub.queued == 0


def test_real_events_pass_the_guard():
    check_metadata_only(event(0))


def test_outbox_fifo(tmp_path):
    ob = Outbox(str(tmp_path / "o.db"))
    for i in range(3):
        ob.put({"kind": "event", "data": {"i": i}}, max_queue=10)
    rows = ob.peek(2)
    assert [r["data"]["i"] for _, r in rows] == [0, 1]
    ob.delete([rows[0][0]])
    assert [r["data"]["i"] for _, r in ob.peek(5)] == [1, 2] and ob.count() == 2


def test_m5_queue_rows_are_read_as_events(tmp_path):
    ob = Outbox(str(tmp_path / "o.db"))
    ob.put({"event_id": "x", "level": 2}, max_queue=10)  # an M5 row: bare event, no kind
    assert ob.peek(1)[0][1] == {"kind": "event", "data": {"event_id": "x", "level": 2}}


def test_feedback_and_samples_share_the_batches(outbox_path):
    backend = FakeBackend()
    pub = make(outbox_path, backend, batch_size=10)
    e = event(0)
    pub.publish(e)
    pub.publish_feedback(e["event_id"])
    pub.publish_sample(build_sample(42.123, 0.08, 1, "trip-1"))
    assert pub.flush_once() == 3
    body = backend.batches[0]
    assert [x["event_id"] for x in body["events"]] == [e["event_id"]]
    assert body["feedback"][0]["event_id"] == e["event_id"] and body["feedback"][0]["verdict"] == "false_alarm"
    assert body["samples"][0]["drowsy_score"] == 42.1 and body["samples"][0]["max_level"] == 1


def test_batch_body_leaves_out_empty_kinds():
    body = batch_body("cam-001", [{"kind": "sample", "data": {"x": 1}}])
    assert body == {"device_id": "cam-001", "samples": [{"x": 1}]}


# ---------------------------------------------------------------- end to end with the backend


def test_decision_pipeline_to_backend(tmp_path):
    """A phone-use scenario through blocks 7-12, published by block 14, lands in the backend DB."""
    from fastapi.testclient import TestClient

    from backend import db
    from backend.app import create_app
    from backend.security import hash_device_key, hash_password
    from backend.settings import BackendSettings
    from edge_agent.config import load_thresholds
    from edge_agent.context.can_sim import CanSimulator, scenario_from_dict
    from edge_agent.decision.pipeline import DecisionPipeline
    from edge_agent.perception.features import FrameFeatures

    settings = BackendSettings(db_path=str(tmp_path / "backend.db"), jwt_secret="s" * 48)
    app = create_app(settings)
    with db.closing(settings.db_path) as conn:
        db.create_user(conn, "boss", hash_password("pw-12345678"), "manager", None)
        db.create_device(conn, "cam-001", hash_device_key("dgk_e2e"), "drv-001")

    with TestClient(app) as client:

        def transport(body):
            return client.post("/api/v1/events", json=body, headers={"X-Device-Key": "dgk_e2e"}).status_code

        pipeline = DecisionPipeline(load_thresholds())
        scenario = scenario_from_dict({"start_clock": "15:00", "timeline": [{"t": 0, "speed_kmh": 50}]})
        can = CanSimulator(scenario)
        pub = MetadataPublisher("cam-001", transport, PublisherConfig(outbox_path=str(tmp_path / "outbox.db")))
        for i in range(20 * 30):  # 20 s at 30 FPS, phone in hand from 5 s to 12 s
            t = i / 30
            f = FrameFeatures(i, t, True, 1.0, ear=0.3, mar=0.05, pitch=0.0, yaw=0.0, roll=0.0)
            r = pipeline.step(f, 5 <= t < 12, can.sample(t))
            if r.alert.new_alert is not None:
                pub.publish(build_event(r.alert.new_alert, r, "trip-e2e"))
        pub.stop()

        token = client.post("/auth/login", json={"username": "boss", "password": "pw-12345678"}).json()
        events = client.get("/api/v1/events", headers={"Authorization": f"Bearer {token['access_token']}"}).json()

    assert len(events) == 1
    e = events[0]
    assert (e["level"], e["reasons"], e["type"]) == (2, ["phone"], "distraction")
    assert (e["device_id"], e["driver_id"], e["trip_id"]) == ("cam-001", "drv-001", "trip-e2e")
    assert e["speed_kmh"] == 50.0 and e["metrics"]["phone_ratio_2s"] >= 0.6


# ---------------------------------------------------------------- heartbeat (M33)


class BeatBackend:
    """Transport stub that tells heartbeat POSTs from record batches."""

    def __init__(self, heartbeat_status=200):
        self.bodies = []
        self.down = False
        self.heartbeat_status = heartbeat_status

    def __call__(self, body):
        if self.down:
            raise OSError("connection refused")
        self.bodies.append(body)
        return self.heartbeat_status if "heartbeat" in body else 200

    @property
    def states(self):
        return [b["heartbeat"]["state"] for b in self.bodies if "heartbeat" in b]


def beat(state="monitoring"):
    return {"ts": "2026-10-05T08:00:00+00:00", "trip_id": "trip-1", "state": state, "moving": True}


def test_heartbeat_is_sent_alone_and_never_queued(outbox_path):
    backend = BeatBackend()
    pub = make(outbox_path, backend)
    pub.publish_record("heartbeat", beat())
    assert pub.queued == 0
    assert pub.flush_once() == 0  # no record accepted, but the heartbeat went out
    assert backend.bodies == [{"device_id": "cam-001", "heartbeat": beat()}]
    assert pub.online is True and pub.sent == 0
    pub.flush_once()
    assert len(backend.bodies) == 1  # sent once


def test_only_the_newest_heartbeat_survives_an_outage(outbox_path):
    backend, clock = BeatBackend(), Clock()
    backend.down = True
    pub = make(outbox_path, backend, clock)
    pub.publish(event(0))
    for state in ("monitoring", "unavailable", "camera_lost"):
        pub.publish_record("heartbeat", beat(state))
        pub.flush_once()
    assert pub.online is False and pub.queued == 1
    backend.down = False
    clock.t += 1000
    assert pub.flush_once() == 1
    assert backend.states == ["camera_lost"]
    assert "heartbeat" in backend.bodies[0] and len(backend.bodies[1]["events"]) == 1  # heartbeat first


def test_backend_without_heartbeats_still_gets_the_records(outbox_path):
    backend = BeatBackend(heartbeat_status=422)  # a backend older than M33 refuses the unknown field
    pub = make(outbox_path, backend)
    pub.publish(event(0))
    pub.publish_record("heartbeat", beat())
    assert pub.flush_once() == 1
    assert pub.queued == 0 and pub.online is True and pub.dropped == 0
    pub.flush_once()
    assert backend.states == ["monitoring"]  # dropped, not retried


def test_heartbeat_is_checked_for_image_data(outbox_path):
    pub = make(outbox_path, BeatBackend())
    with pytest.raises(ValueError):
        pub.publish_record("heartbeat", {**beat(), "frame": "x"})
