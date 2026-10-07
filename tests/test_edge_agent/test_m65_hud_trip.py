"""M65: what the HUD shows of the running trip comes from the agent, so a HUD reload loses nothing.

Continuous driving and the recent minutes (block 11's TripCollector.hud_view), the numbers behind an
alert, since when the driver is not monitored, camera reopen attempts (block 1) and whether the
backend has the event (block 14). Fake sequences, no video.
"""

import json
import time
from datetime import timedelta

import pytest

from edge_agent.capture import CaptureConfig, FrameSource
from edge_agent.io.publisher import check_metadata_only
from edge_agent.perception.features import FrameFeatures
from edge_agent.web.bridge import WebAgent
from tests.test_edge_agent.test_frame_source import FakeCapture, FlakyCamera
from tests.test_edge_agent.test_publisher import Clock, FakeBackend, event
from tests.test_edge_agent.test_publisher import make as make_publisher
from tests.test_edge_agent.test_runtime import FPS, make
from tests.test_edge_agent.test_trip_summary import START, drive
from tests.test_edge_agent.test_web_bridge import H, W, synthetic_face


def face(i, t, ear=0.30, yaw=0.0):
    return FrameFeatures(i, t, True, 1.0, ear=ear, mar=0.05, pitch=0.0, yaw=yaw, roll=0.0)


def feed(rt, seconds, t0=0.0, ear=lambda t: 0.30, yaw=lambda t: 0.0):
    for i in range(round(seconds * FPS)):
        t = t0 + i / FPS
        rt.step(face(i, t, ear(t), yaw(t)), False, t)
    return t0 + round(seconds * FPS) / FPS


# ---------------------------------------------------------------- block 11: continuous driving, recent minutes


def test_continuous_driving_restarts_after_a_rest_and_the_summary_is_unchanged():
    # drive 2 min, park 3 min (a rest after context.rest_after_s = 120 s), drive 1 min
    p = drive(360, [(0, 50), (120, 50), (120.1, 0), (300, 0), (300.1, 50)])
    view = p.trip_log.hud_view(15)
    assert view["drive_run_s"] == pytest.approx(60, abs=2)  # only since the rest
    assert view["driving_s"] == pytest.approx(180, abs=2)  # the whole trip
    s = p.trip_log.summary("trip-t", START, START + timedelta(seconds=360))
    assert s.longest_drive_s == pytest.approx(120, abs=2) and s.rests == 1 and s.driving_s == pytest.approx(180, abs=2)


def test_new_driver_starts_at_zero_but_the_trip_keeps_its_numbers():
    p = drive(120, [(0, 60)])
    before = p.trip_log.summary("trip-t", START, START + timedelta(seconds=120))
    p.change_driver()
    view = p.trip_log.hud_view(15)
    assert view["drive_run_s"] == 0 and view["driving_s"] == pytest.approx(120, abs=1)
    after = p.trip_log.summary("trip-t", START, START + timedelta(seconds=120))
    assert after.driver_changes == 1
    assert after.longest_drive_s == before.longest_drive_s and after.minutes == before.minutes


def test_recent_minutes_are_the_last_window_oldest_first_with_the_running_minute():
    p = drive(5 * 60 + 20, [(0, 60)])  # 5 full minutes and 20 s of the sixth
    recent = p.trip_log.hud_view(3)["recent_minutes"]
    assert [m["minute"] for m in recent] == [3, 4, 5]
    assert all(0 <= m["drowsy_score"] <= 100 and m["max_level"] == 0 for m in recent)


def test_a_rest_minute_is_a_gap_not_a_zero():
    # drive 2 min, park 4 min: a rest from 240 s (context.rest_after_s = 120 s), drive 1 min
    p = drive(480, [(0, 50), (120, 50), (120.1, 0), (420, 0), (420.1, 50)])
    recent = p.trip_log.hud_view(8)["recent_minutes"]
    assert len(recent) == 8
    assert recent[0] is not None and recent[7] is not None
    assert recent[5] is None and recent[6] is None  # 300-420 s: wholly a rest, eyes not judged


def test_short_trip_has_only_its_own_minutes():
    p = drive(30, [(0, 60)])
    assert [m["minute"] for m in p.trip_log.hud_view(15)["recent_minutes"]] == [0]
    assert drive(0, [(0, 60)]).trip_log.hud_view(15)["recent_minutes"] == []


# ---------------------------------------------------------------- block 13: the HUD snapshot


def test_hud_snapshot_carries_the_trip_and_reads_the_same_after_a_reload():
    rt, _, _ = make()
    feed(rt, 90)
    first, again = rt.hud.to_json(), rt.hud.to_json()  # a HUD that reloads just reads it again
    trip = first["trip"]
    assert trip["drive_run_s"] == pytest.approx(90, abs=1) and len(trip["recent_minutes"]) == 2
    assert trip["score_l1"] < trip["score_l2"]  # the chart's colour bands come from thresholds.yaml
    assert again["trip"] == trip
    check_metadata_only(first)


def test_trend_window_comes_from_thresholds():
    rt, _, _ = make()
    rt._hud_cfg = type(rt._hud_cfg)(trend_minutes=1)
    feed(rt, 130)
    assert len(rt.hud.to_json()["trip"]["recent_minutes"]) == 1


def test_microsleep_alert_carries_how_long_the_eyes_were_closed():
    rt, rec, _ = make()
    feed(rt, 70, ear=lambda t: 0.06 if 60 <= t < 63 else 0.30)
    alert = rt.hud.to_json()["alerts"][0]
    assert alert["level"] == 3 and "microsleep" in alert["reasons"]
    assert alert["metrics"]["eyes_closed_s"] >= 1.0
    assert alert["metrics"]["turn_signal"] is None
    assert alert["event_id"] == [d for k, d in rec.records if k == "event"][0]["event_id"]


def test_off_road_alert_carries_how_long_the_driver_looked_away():
    rt, _, _ = make()
    feed(rt, 40, yaw=lambda t: 60.0 if 30 <= t < 36 else 0.0)
    alerts = [a for a in rt.hud.to_json()["alerts"] if "off_road" in a["reasons"]]
    assert alerts, "looking 60 degrees away for 6 s at 60 km/h should raise off_road"
    assert alerts[-1]["metrics"]["off_road_s"] >= 1.0
    assert alerts[-1]["metrics"]["turn_signal"] is None  # "không bật xi nhan"


# ---------------------------------------------------------------- not monitored: since, attempts, reported


def test_camera_lost_incident_names_its_event_and_clears_when_back():
    rt, rec, _ = make()
    feed(rt, 2)
    before = time.time()
    rt.camera(True)
    incident = rt.hud.to_json()["incident"]
    lost_event = [d for k, d in rec.records if k == "event" and d["reasons"] == ["camera_lost"]][0]
    assert incident["kind"] == "camera_lost" and incident["since"] >= before
    assert incident["event_id"] == lost_event["event_id"]
    assert incident["attempts"] is None and incident["reported"] is None  # set by the device loop only
    rt.hud.set_incident_attempts(3)
    rt.hud.set_incident_reported(True)
    assert rt.hud.to_json()["incident"]["attempts"] == 3 and rt.hud.to_json()["incident"]["reported"] is True
    rt.camera(False)
    assert rt.hud.to_json()["incident"] is None


def test_processing_error_incident_starts_with_agent_error_and_ends_with_a_good_frame():
    rt, rec, _ = make()
    t = feed(rt, 2)
    for i in range(round(1.5 * FPS)):
        rt.frame_failed(t + i / FPS, "ValueError")
    incident = rt.hud.to_json()["incident"]
    error_event = [d for k, d in rec.records if k == "event" and d["reasons"] == ["agent_error"]][0]
    assert incident["kind"] == "processing_error" and incident["event_id"] == error_event["event_id"]
    feed(rt, 0.2, t0=t + 2)
    assert rt.hud.to_json()["incident"] is None


def test_ending_one_incident_does_not_clear_the_other():
    rt, _, _ = make()
    feed(rt, 1)
    rt.camera(True)
    rt.hud.end_incident("processing_error")
    assert rt.hud.to_json()["incident"]["kind"] == "camera_lost"


def test_browser_state_carries_the_trip_and_an_incident_it_cannot_confirm():
    agent = WebAgent("web-an", "trip-web-1", scenario="highway_night")
    face_points = synthetic_face().ravel()
    for i in range(30):
        state = json.loads(agent.frame(i / FPS, i, W, H, face_points, 1, (0.05, 0.05), 12.0, 140.0))
    assert state["trip"]["recent_minutes"] and "drive_run_s" in state["trip"]
    agent.camera(True)
    incident = agent.hud.to_json()["incident"]
    assert incident["kind"] == "camera_lost" and incident["reported"] is None  # #/live: no publisher here


# ---------------------------------------------------------------- block 14: did the backend get it


def test_publisher_knows_which_events_the_backend_accepted(tmp_path):
    backend = FakeBackend()
    pub = make_publisher(str(tmp_path / "outbox.db"), backend, Clock())
    e = event(0)
    pub.publish(e)
    assert not pub.delivered(e["event_id"])  # queued only
    backend.down = True
    pub.flush_once()
    assert not pub.delivered(e["event_id"])  # offline: still in the outbox
    backend.down = False
    pub._next_attempt = 0.0
    while pub.flush_once():
        pass
    assert pub.delivered(e["event_id"]) and not pub.delivered("other")


def test_event_accepted_one_by_one_is_delivered_and_a_refused_one_is_not(tmp_path):
    backend = FakeBackend()
    backend.reject_seq = {1}
    pub = make_publisher(str(tmp_path / "outbox.db"), backend, Clock())
    ok, bad = event(0), event(1)
    pub.publish(ok)
    pub.publish(bad)
    pub.flush_once()
    assert pub.delivered(ok["event_id"]) and not pub.delivered(bad["event_id"])


# ---------------------------------------------------------------- block 1: reopen attempts


def test_reopen_attempts_count_while_lost_and_reset_on_frames():
    opened = []

    def factory(_src):
        cap = FlakyCamera(good=5 if not opened else 10**9)
        opened.append(cap)
        return cap

    config = CaptureConfig(video_realtime=False, max_consecutive_failures=3, reconnect_interval_s=0.05)
    src = FrameSource(0, config, capture_factory=factory)
    with src:
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline and not (src.reconnects and not src.lost):
            src.read(timeout=0.05)
        assert src.reconnects == 1 and not src.lost
        assert src.reopen_attempts == 0  # frames flow again


def test_reopen_attempts_grow_while_the_camera_stays_dead():
    class Dead(FakeCapture):
        def isOpened(self):  # noqa: N802
            return False

    caps = iter([FlakyCamera(good=2)])
    config = CaptureConfig(video_realtime=False, max_consecutive_failures=2, reconnect_interval_s=0.02)
    src = FrameSource(0, config, capture_factory=lambda _s: next(caps, Dead(0)))
    with src:
        time.sleep(0.3)
        assert src.lost and src.reopen_attempts >= 3
