"""End of trip: block 11 trip summary, the HUD's "end trip" button, the in-browser agent. Fake sequences."""

import http.client
import json
import threading
from datetime import UTC, datetime, timedelta

import pytest

from backend.schemas import EventBatch
from edge_agent.config import load_thresholds
from edge_agent.context.can_sim import CanSimulator, scenario_from_dict
from edge_agent.decision.pipeline import DecisionPipeline
from edge_agent.decision.trip_summary import TripSummaryConfig, assess, suggest
from edge_agent.hud.server import HudServer, HudState
from edge_agent.io.publisher import batch_body
from edge_agent.perception.features import FrameFeatures
from edge_agent.web.bridge import WebAgent
from tests.test_edge_agent.test_web_bridge import H, W, synthetic_face

FPS = 15
START = datetime(2026, 10, 1, 8, 0, tzinfo=UTC)


def drive(seconds, speeds, ear=lambda t: 0.30, face=lambda t: True, enroll=False):
    th = load_thresholds()
    th["enrollment"] = {**th["enrollment"], "enabled": enroll}
    pipeline = DecisionPipeline(th)
    timeline = [{"t": t, "speed_kmh": v} for t, v in speeds] + [{"t": 100000, "speed_kmh": speeds[-1][1]}]
    can = CanSimulator(scenario_from_dict({"name": "t", "start_clock": "15:00", "timeline": timeline}))
    for i in range(round(seconds * FPS)):
        t = i / FPS
        if face(t):
            f = FrameFeatures(i, t, True, 1.0, ear=ear(t), mar=0.05, pitch=0.0, yaw=0.0, roll=0.0)
        else:
            f = FrameFeatures(i, t, False, 0.0)
        pipeline.step(f, False, can.sample(t))
    return pipeline


def summarize(pipeline, seconds, **kw):
    return pipeline.trip_log.summary("trip-t", START, START + timedelta(seconds=seconds), **kw)


# ---------------------------------------------------------------- what the summary adds up


def test_alert_drive_is_good_and_adds_up():
    s = summarize(drive(300, [(0, 60)]), 300)
    assert s.duration_s == pytest.approx(300, abs=1) and s.driving_s == pytest.approx(300, abs=1)
    assert s.avg_speed_kmh == pytest.approx(60)
    assert s.alerts_by_level == {"1": 0, "2": 0, "3": 0} and s.microsleeps == 0
    assert s.monitored_frac == pytest.approx(1.0, abs=0.01)
    assert [p.minute for p in s.minutes] == [0, 1, 2, 3, 4]
    assert s.rating == "good" and s.rating_reasons == []
    assert {"code": "enroll"} in s.suggestions  # not enrolled this trip
    assert s.speed_source == "simulated"


def test_enrollment_eyes_closed_step_is_not_a_microsleep_in_the_summary():
    """Bug (M21 e2e, fixed in M27): step 3 of enrollment (eyes shut ~2 s, parked) raised no alert but the
    summary counted it as a microsleep and rated a 0 s drive "risk: nhắm mắt ngủ gật khi đang lái"."""
    from tests.test_edge_agent.test_enrollment import obedient

    th = load_thresholds()
    pipeline = DecisionPipeline(th)
    can = CanSimulator(
        scenario_from_dict({"name": "t", "start_clock": "15:00", "timeline": [{"t": 0, "speed_kmh": 0}]})
    )
    status, events = "waiting", []
    for i in range(round(20 * FPS)):
        t = i / FPS
        r = pipeline.step(obedient(i, t, status), False, can.sample(t))
        status = r.enrollment.status
        events += r.drowsiness.events
        if status == "consent":
            pipeline.enrollment_answer(True)
    assert r.enrollment.enrolled and "microsleep" in events  # block 7 did see a long closure
    s = summarize(pipeline, 20)
    assert s.microsleeps == 0 and s.longest_closure_s < 1.0
    assert s.rating == "good" and "microsleep" not in s.rating_reasons
    assert all(p.drowsy_score < s.score_l1 for p in s.minutes)


def test_resting_the_eyes_after_parking_is_not_a_microsleep_in_the_summary():
    # Parked longer than context.rest_after_s, then eyes shut 5 s: a rest, as the risk engine sees it.
    s = summarize(drive(200, [(0, 0)], ear=lambda t: 0.06 if 150 <= t < 155 else 0.30), 200)
    assert s.rests == 1 and s.microsleeps == 0 and s.rating == "good"


def test_microsleep_at_a_red_light_still_counts():
    # Standing still but not a rest yet (red light): a real microsleep, still in the summary.
    s = summarize(drive(60, [(0, 60), (20, 0)], ear=lambda t: 0.06 if 30 <= t < 33 else 0.30), 60)
    assert s.microsleeps == 1 and s.rating == "risk"


def test_microsleep_while_driving_is_risk():
    s = summarize(drive(120, [(0, 60)], ear=lambda t: 0.06 if 60 <= t < 63 else 0.30), 120)
    assert s.alerts_by_level["3"] == 1 and s.microsleeps == 1
    assert s.longest_closure_s >= 1.5
    assert s.rating == "risk" and "microsleep" in s.rating_reasons
    assert s.suggestions[0] == {"code": "rest_now"}


def test_stops_rests_and_longest_drive():
    # drive 2 min, park 3 min (a rest after context.rest_after_s = 120 s), drive 1 min
    s = summarize(drive(360, [(0, 50), (120, 50), (120.1, 0), (300, 0), (300.1, 50)]), 360)
    assert s.rests == 1
    assert s.stopped_s == pytest.approx(180, abs=2)
    assert s.longest_drive_s == pytest.approx(120, abs=2)
    assert [p.moving for p in s.minutes] == [True, True, False, False, False, True]


def test_face_lost_lowers_coverage_without_blaming_the_driver():
    s = summarize(drive(300, [(0, 60)], face=lambda t: not 60 <= t < 200), 300)
    assert s.unavailable_s > 100
    assert s.monitored_frac < 0.6
    assert "low_coverage" in s.rating_reasons and s.rating == "good"
    assert {"code": "check_camera"} in s.suggestions


def test_summary_is_metadata_only_and_the_backend_accepts_it():
    d = summarize(drive(120, [(0, 60)]), 120, false_alarms=2, camera_lost_s=4.0).to_dict()
    text = json.dumps(d)
    for word in ("image", "frame", "jpeg", "png", "base64"):
        assert word not in text
    EventBatch.model_validate(batch_body("cam-001", [{"kind": "summary", "data": d}]))


# ---------------------------------------------------------------- assessment rules (thresholds.yaml)


def make(**over):
    base = summarize(drive(60, [(0, 60)]), 60)
    for k, v in over.items():
        setattr(base, k, v)
    return base


def test_frequent_serious_alerts_need_attention():
    cfg = TripSummaryConfig()
    s = make(driving_s=3600.0, alerts_by_level={"1": 0, "2": 2, "3": 0})
    assert assess(s, cfg, 40.0) == ("attention", ["frequent_alerts"])
    s = make(driving_s=3600.0, alerts_by_level={"1": 0, "2": 1, "3": 0})
    assert assess(s, cfg, 40.0)[0] == "good"


def test_tired_minutes_need_attention_and_suggest_a_rest_time():
    cfg = TripSummaryConfig()
    tired = [type(p)(p.minute, 55.0, 1, True) for p in make().minutes] * 5
    s = make(minutes=tired, first_tired_min=95)
    assert assess(s, cfg, 40.0) == ("attention", ["tired_minutes"])
    assert {"code": "rest_after", "minutes": 85} in suggest(s, cfg, 7200.0)


def test_long_drive_and_distraction_suggestions():
    s = make(longest_drive_s=7300.0, alerts_by_reason={"phone": 1, "off_road": 2}, enrolled=True)
    codes = [x["code"] for x in suggest(s, TripSummaryConfig(), 7200.0)]
    assert codes == ["regular_breaks", "phone_away", "eyes_on_road"]


# ---------------------------------------------------------------- "end trip" on the device HUD


def test_hud_end_trip_waits_for_the_main_loop_summary():
    state = HudState()
    server = HudServer(state, lambda _: None, port=0).start()
    try:

        def main_loop():  # what edge_agent.main does on its next frame
            while not state.end_requested:
                threading.Event().wait(0.01)
            state.set_summary({"trip_id": "trip-x", "rating": "good"})
            assert state.wait_delivered(2.0)

        loop = threading.Thread(target=main_loop)
        loop.start()
        conn = http.client.HTTPConnection("127.0.0.1", server.port, timeout=5)
        conn.request("POST", "/end-trip", b"")
        assert json.loads(conn.getresponse().read())["summary"]["trip_id"] == "trip-x"
        conn.close()
        loop.join(2.0)
        assert state.to_json()["trip_ended"] is True
    finally:
        server.stop()


def test_false_alarms_are_counted_for_the_summary():
    state = HudState()
    state.add_alert("e1", 2, ("off_road",))
    assert state.mark_false_alarm("e1") == "ok"
    assert state.false_alarms == 1


# ---------------------------------------------------------------- "end trip" in the browser (#/live)


def test_web_end_trip_returns_and_queues_the_summary():
    agent = WebAgent("web-an", "trip-web-9", scenario="highway_night")
    face = synthetic_face().ravel()
    for i in range(int(20 * 30)):
        agent.frame(i / 30, i, W, H, face, 1, (0.05, 0.05), 12.0, 140.0)
    summary = json.loads(agent.end_trip())
    assert summary["trip_id"] == "trip-web-9" and summary["driving_s"] > 15
    body = json.loads(agent.take_batch())
    assert body["summaries"][0]["trip_id"] == "trip-web-9"
    EventBatch.model_validate(body)
