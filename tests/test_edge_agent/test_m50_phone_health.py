"""M50: the phone detector giving no fresh results is told to the driver and the backend, instead of
phones silently never being seen. Fake frame sequences, no YOLO."""

import json

from backend.schemas import EventBatch
from edge_agent.config import load_thresholds
from edge_agent.io.publisher import batch_body
from edge_agent.perception.phone_detector import PhoneDetectorConfig, PhoneHealth
from edge_agent.web import bridge
from edge_agent.web.bridge import WebAgent
from tests.test_edge_agent.test_enrollment import obedient
from tests.test_edge_agent.test_runtime import make
from tests.test_edge_agent.test_web_bridge import H, W, run, synthetic_face, yolo_output_with_phone

FPS = 30


def feed(health, seconds, known, t0=0.0):
    """`known`: True / False, or a function of the frame index. Returns (unavailable, end time)."""
    out, t = health.unavailable, t0
    for i in range(round(seconds * FPS)):
        t = t0 + i / FPS
        out = health.update(t, known(i) if callable(known) else known)
    return out, t + 1 / FPS


def health(**over):
    return PhoneHealth(PhoneDetectorConfig(**over))


def test_fresh_results_on_every_frame_is_healthy():
    assert feed(health(), 60, True) == (False, 60.0)


def test_no_result_at_all_is_unavailable_after_one_window():
    h = health()
    assert feed(h, 9, False)[0] is False  # not judged before a full window: the first result needs a moment
    assert feed(h, 2, False, t0=9.0)[0] is True


def test_results_coming_back_restore_it_with_hysteresis():
    h = health()
    _, t = feed(h, 12, False)
    assert h.unavailable
    _, t = feed(h, 3, True, t0=t)  # 3 of the last 10 s known: still above the clear ratio
    assert h.unavailable and 0.5 < h.unknown_share < 0.8
    _, t = feed(h, 3, True, t0=t)
    assert not h.unavailable


def test_a_slow_detector_that_is_mostly_stale_is_unavailable_and_a_mostly_fresh_one_is_not():
    # YOLO slower than max_result_age_s: a fresh answer on 1 frame in 10
    assert feed(health(), 20, lambda i: i % 10 == 0)[0] is True
    # ... and one that goes stale for a third of the time is still usable
    assert feed(health(), 20, lambda i: i % 3 != 0)[0] is False


def test_a_frame_gap_does_not_count_as_seconds_of_unknown():
    h = health()
    _, t = feed(h, 12, True)
    h.update(t + 30.0, False)  # the loop stalled: other states report that, not this one
    assert not h.unavailable


def test_window_zero_switches_it_off():
    assert feed(health(unknown_window_s=0.0), 30, False)[0] is False


def test_thresholds_file_has_the_window_and_both_ratios():
    cfg = PhoneDetectorConfig.from_dict(load_thresholds()["phone"])
    assert cfg.unknown_window_s > cfg.max_result_age_s and 0 < cfg.unknown_clear_ratio < cfg.unknown_ratio <= 1


# ---------------------------------------------------------------------------- TripRuntime
def drive(rt, seconds, phone_flag, t0=0.0):
    t = t0
    for i in range(round(seconds * FPS)):
        t = t0 + i / FPS
        rt.step(obedient(i, t, "waiting"), phone_flag, t, clock=t)
    return t + 1 / FPS


def test_runtime_tells_the_hud_and_the_backend_and_takes_it_back():
    rt, rec, _ = make()
    rt.phone_expected = True
    t = drive(rt, 12, None)
    assert rec.reasons() == [["phone_detection_lost"]]
    event = rec.records[0][1]
    assert event["type"] == "system" and event["metrics"]["phone_unknown_ratio"] >= 0.8
    assert rt.hud.to_json()["phone_unavailable"] is True
    assert rt.monitor_state() == "monitoring"  # eyes and head are still watched
    EventBatch.model_validate(batch_body("cam-001", [{"kind": "event", "data": event}]))
    drive(rt, 8, False, t0=t)
    assert rec.reasons() == [["phone_detection_lost"], ["phone_detection_restored"]]
    assert rt.hud.to_json()["phone_unavailable"] is False


def test_runtime_says_nothing_when_the_detector_is_off_on_purpose():
    rt, rec, _ = make()  # phone_expected False: --no-phone on the device
    drive(rt, 30, None)
    assert rec.reasons() == [] and rt.hud.to_json()["phone_unavailable"] is False


def test_other_alerts_go_on_while_phones_are_not_detected():
    rt, rec, _ = make()
    rt.phone_expected = True
    t = drive(rt, 12, None)
    for i in range(round(3 * FPS)):  # eyes shut: still a microsleep alarm
        tt = t + i / FPS
        rt.step(obedient(i, tt, "close_eyes"), None, tt, clock=tt)
    assert ["microsleep"] in rec.reasons()


# ---------------------------------------------------------------------------- the page (bridge)
def test_page_that_expects_the_detector_reports_a_dead_one():
    agent = WebAgent("web-an", "trip-web-1", scenario="highway_night")
    agent.expect_phone(True)  # YOLO failed to load, or every result arrives too late
    state, _, _ = run(agent, 12, points=synthetic_face())
    assert state["phone_unavailable"] is True
    events = json.loads(agent.take_batch())["events"]
    assert ["phone_detection_lost"] in [e["reasons"] for e in events]


def test_page_with_fresh_results_stays_quiet():
    agent = WebAgent("web-an", "trip-web-1", scenario="highway_night")
    agent.expect_phone(True)
    face = synthetic_face()
    empty = yolo_output_with_phone((0, 0, 1, 1)) * 0.0
    state = None
    for i in range(12 * 30):
        t = i / 30
        if i % 6 == 0:  # YOLO 5 times a second on the frame it was given
            agent.phone_output(empty, 8, 1.0, 0, 80, W, H, t)
        state = json.loads(agent.frame(t, i, W, H, face.ravel(), 1, (0.05, 0.05), 12.0, 140.0))
    assert state["phone_unavailable"] is False and agent.take_batch() is None


def test_page_without_the_call_keeps_the_old_behaviour():
    agent = WebAgent("web-an", "trip-web-1", scenario="highway_night")
    state, _, _ = run(agent, 12, points=synthetic_face())
    assert state["phone_unavailable"] is False


def test_thresholds_file_is_parsed_once_per_trip(monkeypatch):
    """M50: YAML parsing is slow in Pyodide; the reloader's base is the same parse, not a second one."""
    calls = []
    real = bridge.load_thresholds
    monkeypatch.setattr(bridge, "load_thresholds", lambda *a: calls.append(1) or real(*a))
    agent = WebAgent(
        "web-an", "trip-web-1", scenario="parked", overrides={"risk.microsleep_l3_s": 2.0}, thresholds_version=3
    )
    assert len(calls) == 1 and agent.problems == []
    assert agent.runtime.decisions.risk.config.microsleep_l3_s == 2.0
    # the tuned value did not leak into the base the next reload starts from
    assert agent.offer_thresholds(0, {}) is True
    agent.frame(0.0, 0, W, H, None)  # parked: the reload is applied on this frame
    assert agent.runtime.decisions.risk.config.microsleep_l3_s == 1.5
    assert len(calls) == 1


def test_a_js_null_from_the_page_is_no_face_not_a_failing_frame():
    """Found by running the production build in a browser (M50): Pyodide hands a JS null over as its own
    JsNull value, not None. A frame without a face then raised in `_floats` and counted as a processing
    error. The page now sends undefined, and the bridge takes a null as None anyway."""

    class JsNull:  # stands in for pyodide.ffi.JsNull, matched by its type name
        pass

    null = JsNull()
    agent = WebAgent("web-an", "trip-web-1", scenario="highway_night")
    state = json.loads(agent.frame(0.0, 0, W, H, null, 0, null, 12.0, 140.0, null, 110.0, 40.0, null))
    assert "error" not in state and state["measures"]["face"] is False
    state, _, _ = run(agent, 5, t0=1 / 30, frame0=1, points=None)
    assert state["processing_error"] is False and state["unavailable"] is True
