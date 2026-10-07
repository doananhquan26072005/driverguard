"""M44: eyes closed through the alarm (unresponsive), L3 that keeps coming back (repeated_l3) and the
presence question ("Bạn còn ở đó không?"). Fake number sequences, no video."""

import json

from edge_agent.config import ConfigError, consistency_errors, load_thresholds
from edge_agent.context.can_sim import CanSimulator, scenario_from_dict
from edge_agent.decision.alert_manager import AlertConfig, AlertManager
from edge_agent.decision.pipeline import DecisionPipeline
from edge_agent.decision.presence import PresenceCheck, PresenceConfig
from edge_agent.decision.risk_engine import RiskAssessment, RuleHit
from edge_agent.io.publisher import MetadataPublisher, PublisherConfig, build_system_event, is_urgent
from edge_agent.perception.features import FrameFeatures
from edge_agent.runtime import TripRuntime
from edge_agent.web.bridge import WebAgent
from tests.test_edge_agent.test_runtime import FakeSelector, Recorder
from tests.test_edge_agent.test_web_bridge import H, W, synthetic_face

FPS = 15
OPEN, SHUT = 0.30, 0.06


def face(t, ear=OPEN):
    return FrameFeatures(round(t * FPS), t, True, 1.0, ear=ear, mar=0.05, pitch=0.0, yaw=0.0, roll=0.0)


def gone(t, **q):
    return FrameFeatures(round(t * FPS), t, False, 0.0, face_reliable=False, **q)


def thresholds():
    th = load_thresholds()
    th["enrollment"] = {**th["enrollment"], "enabled": False}
    return th


def can(speed=60.0):
    return CanSimulator(scenario_from_dict({"start_clock": "12:00", "timeline": [{"t": 0, "speed_kmh": speed}]}))


def drive(make, seconds, pipeline=None, t0=0.0, taps=()):
    """make(t) -> FrameFeatures. taps: times the driver taps the presence question."""
    p = pipeline or DecisionPipeline(thresholds())
    vehicle, out, taps = can(), [], sorted(taps)
    for i in range(round(seconds * FPS)):
        t = t0 + i / FPS
        while taps and taps[0] <= t:
            p.presence_answer()
            taps.pop(0)
        out.append(p.step(make(t), False, vehicle.sample(t)))
    return out, p


def alerts(results):
    return [
        (round(r.alert.new_alert.t, 1), r.alert.new_alert.level, r.alert.new_alert.reasons)
        for r in results
        if r.alert.new_alert is not None
    ]


# ------------------------------------------------------------------ unresponsive
def test_eyes_closed_through_the_alarm_raise_a_second_l3_alert():
    out, _ = drive(lambda t: face(t, SHUT if 20 <= t < 28 else OPEN), 32)
    got = alerts(out)
    assert [(lv, rs[0]) for _, lv, rs in got] == [(3, "microsleep"), (3, "unresponsive")]
    assert 21.4 <= got[0][0] <= 21.7 and 25.9 <= got[1][0] <= 26.2  # 1.5 s, then 6 s of closed eyes
    assert got[1][2] == ("unresponsive", "microsleep")


def test_a_usual_microsleep_is_one_alert():
    out, _ = drive(lambda t: face(t, SHUT if 20 <= t < 23 else OPEN), 30)
    assert [rs for _, _, rs in alerts(out)] == [("microsleep",)]


def test_unresponsive_must_come_after_the_l3_rule():
    th = thresholds()
    th["risk"] = {**th["risk"], "unresponsive": {"closed_s": 1.0}}
    assert any("unresponsive" in e for e in consistency_errors(th))


# ------------------------------------------------------------------ repeated L3
def test_third_microsleep_within_the_window_is_marked_repeated():
    closed = lambda t: any(a <= t < a + 2.5 for a in (20, 60, 100, 140))  # noqa: E731
    out, _ = drive(lambda t: face(t, SHUT if closed(t) else OPEN), 150)
    assert [rs for _, _, rs in alerts(out)] == [
        ("microsleep",),
        ("microsleep",),
        ("microsleep", "repeated_l3"),
        ("microsleep", "repeated_l3"),
    ]
    assert all(lv == 3 for _, lv, _ in alerts(out))


def _l3(t, reasons=("microsleep",)):
    return RiskAssessment(t, 3, tuple(RuleHit(3, r, 2.0) for r in reasons), 25.0, 0.0, (0, 1, 0, 0, 0, 0))


def _l0(t):
    return RiskAssessment(t, 0, (), 0.0, 0.0, (0,) * 6)


def test_repeat_count_ignores_unresponsive_and_old_alerts_and_can_be_off():
    def run(cfg, script):
        m, got, t = AlertManager(cfg), [], 0.0
        for kind, seconds in script:
            for _ in range(round(seconds * 10)):
                t += 0.1
                r = {"l0": _l0, "l3": _l3, "un": lambda x: _l3(x, ("microsleep", "unresponsive"))}[kind](t)
                a = m.update(r).new_alert
                if a is not None:
                    got.append(a.reasons)
        return got

    one_long = [("l0", 5), ("l3", 5), ("un", 5), ("l0", 5), ("l3", 3), ("l0", 5)]
    assert run(AlertConfig(), one_long) == [("microsleep",), ("unresponsive", "microsleep"), ("microsleep",)]
    spaced = [("l0", 5), ("l3", 2), ("l0", 400), ("l3", 2), ("l0", 400), ("l3", 2), ("l0", 5)]  # 2 per 600 s
    assert run(AlertConfig(), spaced) == [("microsleep",)] * 3
    three = [("l0", 5), ("l3", 2), ("l0", 5), ("l3", 2), ("l0", 5), ("l3", 2), ("l0", 5)]
    assert run(AlertConfig(), three)[-1] == ("microsleep", "repeated_l3")
    assert run(AlertConfig(l3_repeat_count=0), three) == [("microsleep",)] * 3


def test_a_rest_starts_the_l3_count_again():
    m = AlertManager(AlertConfig())
    t = 0.0
    for _ in range(2):
        for r in (_l3, _l0):
            for _ in range(50):
                t += 0.1
                m.update(r(t))
    m.forget_repeats()
    got = None
    for _ in range(20):
        t += 0.1
        got = got or m.update(_l3(t)).new_alert
    assert got.reasons == ("microsleep",)


# ------------------------------------------------------------------ presence check (pure)
def test_presence_asks_then_reports_no_answer_once():
    p = PresenceCheck(PresenceConfig(ask_after_s=5, answer_s=10))
    events = [(t / 10, p.update(t / 10, lost=True)) for t in range(0, 300)]
    named = [(t, s.event) for t, s in events if s.event]
    assert named == [(5.0, "asked"), (15.0, "no_answer")]
    assert events[100][1].asking and 4.9 <= events[100][1].remaining_s <= 5.1
    assert events[-1][1].unanswered and not events[-1][1].asking


def test_presence_tap_answers_and_it_is_not_asked_again_until_the_face_is_back():
    p = PresenceCheck(PresenceConfig(ask_after_s=5, answer_s=10))
    for t in range(0, 80):
        p.update(t / 10, lost=True)
    assert p.update(8.0, lost=True, ack=True).event == "answered"
    later = [p.update(8 + t / 10, lost=True) for t in range(1, 400)]
    assert not any(s.asking or s.unanswered or s.event for s in later)
    p.update(50.0, lost=False)  # face seen again
    again = [p.update(50 + t / 10, lost=True).event for t in range(1, 80)]
    assert "asked" in again


def test_presence_face_back_ends_the_question_and_a_stray_tap_does_nothing():
    p = PresenceCheck(PresenceConfig(ask_after_s=5, answer_s=10))
    assert p.update(0.0, lost=True, ack=True).event is None  # nothing was asked
    for t in range(0, 70):
        p.update(t / 10, lost=True)
    s = p.update(7.0, lost=False)
    assert not s.asking and s.event is None
    assert PresenceCheck(PresenceConfig(enabled=False)).update(99.0, lost=True) == p.update(7.1, lost=False)


def test_a_tap_after_no_answer_clears_it():
    p = PresenceCheck(PresenceConfig(ask_after_s=1, answer_s=2))
    for t in range(0, 50):
        p.update(t / 10, lost=True)
    assert p.update(5.0, lost=True).unanswered
    assert p.update(5.1, lost=True, ack=True).event == "answered"
    assert not p.update(5.2, lost=True).unanswered


# ------------------------------------------------------------------ in the pipeline
def test_driver_out_of_view_is_asked_and_unanswered_goes_to_the_backend_at_once():
    rec = Recorder()
    rt = TripRuntime(thresholds(), "trip-1", can(), "t", FakeSelector(), emit=rec)
    asked_at = None
    for i in range(30 * FPS):
        t = i / FPS
        f = face(t) if t < 5 else gone(t, scene_brightness=100.0, scene_contrast=50.0)
        r = rt.step(f, False, t).result
        if r.presence.event == "asked":
            asked_at = t
            assert rt.hud.to_json()["presence"]["asking"] is True
    assert 12.9 <= asked_at <= 13.2  # lost at 5 s, unavailable at 8 s, asked 5 s later
    reasons = rec.reasons()
    assert reasons == [["monitoring_unavailable"], ["no_answer"]]
    assert is_urgent(next(d for k, d in rec.records if d.get("reasons") == ["no_answer"]))
    assert rt.hud.to_json()["presence"] == {"asking": False, "remaining_s": 0.0, "unanswered": True}


def test_tap_answers_the_question_in_the_pipeline():
    out, _ = drive(lambda t: face(t) if t < 5 else gone(t), 30, taps=(15.0,))
    events = [r.presence.event for r in out if r.presence.event]
    assert events == ["asked", "answered"]


def test_covered_camera_and_turned_away_are_not_asked():
    out, _ = drive(lambda t: face(t) if t < 5 else gone(t, scene_brightness=2.0, scene_contrast=1.0), 30)
    assert out[-1].risk.unavailable_reason == "camera_blocked"
    assert not any(r.presence.event for r in out)
    moving, _ = drive(gone, 30)
    assert any(r.presence.event == "asked" for r in moving)  # at 60 km/h, image unknown: asked
    p = DecisionPipeline(thresholds())
    still = [p.step(gone(i / FPS), False, can(0.0).sample(i / FPS)) for i in range(30 * FPS)]
    assert not any(r.presence.event for r in still)  # parked: never unavailable, never asked


# ------------------------------------------------------------------ sent at once
def test_urgent_events_are_l3_and_the_three_reasons():
    assert is_urgent({"level": 3, "reasons": ["microsleep"]})
    assert is_urgent(build_system_event("no_answer", "trip-1"))
    assert is_urgent({"level": 3, "reasons": ["microsleep", "repeated_l3"]})
    assert not is_urgent({"level": 2, "reasons": ["phone"]})
    assert not is_urgent(build_system_event("camera_lost", "trip-1"))


def test_publisher_wakes_for_an_urgent_event_only(tmp_path):
    cfg = PublisherConfig(outbox_path=str(tmp_path / "o.db"), flush_interval_s=3600)
    pub = MetadataPublisher("cam-001", lambda body: 200, cfg)
    try:
        pub.publish_record("event", build_system_event("camera_lost", "trip-1"))
        assert not pub._wake.is_set()
        pub.publish_record("event", build_system_event("no_answer", "trip-1"))
        assert pub._wake.is_set()
    finally:
        pub.stop(final_flush=False)


def test_browser_is_told_to_send_now_and_takes_the_tap():
    agent = WebAgent("web-an", "trip-web-1", scenario="highway_night")
    pts = synthetic_face().ravel()
    flushes = []
    for i in range(int(22 * FPS)):
        t = i / FPS
        p = pts if t < 3 else None
        state = json.loads(agent.frame(t, i, W, H, p, 1 if p is not None else 0, (0.05, 0.05), 12.0, 140.0))
        if state["flush"]:
            flushes.append(round(t))
    assert state["presence"]["unanswered"] is True and flushes  # no_answer was queued: send now
    assert agent.vehicle("presence_ok") == "ok"
    state = json.loads(agent.frame(22.1, 9999, W, H, None, 0, (0.05, 0.05), 12.0, 140.0))
    assert state["presence"] == {"asking": False, "remaining_s": 0.0, "unanswered": False}
    assert state["flush"] is False


def test_unknown_presence_key_stops_the_agent():
    th = thresholds()
    th["presence"] = {"ask_after": 5}
    try:
        DecisionPipeline(th)
    except ConfigError as e:
        assert "presence.ask_after" in str(e)
    else:
        raise AssertionError("an unknown presence key was accepted")
