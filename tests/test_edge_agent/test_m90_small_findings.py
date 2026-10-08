"""M90: the small findings of the 08/10 audit (A2 L1-L3, A3 L2 / L3 / L6, A4 L2-L4, A1 L5).

- blink_rate is blinks per minute of eye data, and the blink rule waits for eye data, not for clock time.
- phone_ratio_2s reads 0 until its window holds enough detector results.
- A closure carried through a head drop ends once nothing has been in view for too long; the track
  of a head dip, the microsleep times and the summary's minutes no longer grow without limit.
- The trend is fitted when a minute closes, on the minutes' own numbers.
- drowsy_score reads 0 during a rest; a turn signal left on stops widening the yaw limit.
- The outbox is written by the sender thread, is its owner's only, and retries are spread out.
- The page's queue is capped, it does not need sqlite3, the quality numbers are the driver's, and a
  YOLO result is held against the face of its own frame.
- stop() does not release a camera whose reader is still inside read().

Fake numbers at 30 FPS, no video, no network.
"""

import json
import os
import stat
import subprocess
import sys
import threading
import time
from dataclasses import replace

import numpy as np
import pytest

from edge_agent.analysis.distraction import DistractionAnalyzer, DistractionConfig
from edge_agent.analysis.drowsiness import DrowsinessAnalyzer, DrowsinessConfig
from edge_agent.capture.frame_source import CaptureConfig, FrameSource
from edge_agent.config import PROJECT_ROOT, load_thresholds
from edge_agent.context.can_sim import CanSimulator, VehicleSignals, scenario_from_dict
from edge_agent.context.vehicle_context import ContextConfig, ContextTracker
from edge_agent.decision import trip_memory
from edge_agent.decision.pipeline import DecisionPipeline
from edge_agent.decision.risk_engine import RiskEngine
from edge_agent.decision.trip_memory import TripMemory, TripMemoryConfig, linear_slope
from edge_agent.io import publisher as publisher_module
from edge_agent.io.publisher import MetadataPublisher, Outbox, PublisherConfig, build_system_event
from edge_agent.perception.features import FrameFeatures
from edge_agent.perception.phone_detector import FaceBoxMemory
from edge_agent.web.bridge import WebAgent
from tests.test_edge_agent.test_decision import C0, D0, X0
from tests.test_edge_agent.test_web_bridge import H, W, synthetic_face

TH = load_thresholds()
FPS = 30
DT = 1.0 / FPS
OPEN, SHUT = 0.30, 0.08
DROWSY = DrowsinessConfig.from_dict(TH["drowsiness"])
DISTRACTION = DistractionConfig.from_dict(TH["distraction"])
CONTEXT = ContextConfig.from_dict(TH["context"])


def face(t, ear=OPEN, pitch=0.0):
    return FrameFeatures(round(t * FPS), t, True, 1.0, ear=ear, mar=0.05, pitch=pitch, yaw=0.0, roll=0.0)


def no_face(t):
    return FrameFeatures(round(t * FPS), t, False, 0.0, face_reliable=False)


def times(t0, seconds):
    return [t0 + i * DT for i in range(round(seconds * FPS))]


# ---------------------------------------------------------------- A2 L1: blink_rate


def blinking(t):
    """A 0.2 s blink every 4 s: 15 a minute."""
    return face(t, SHUT if t % 4.0 < 0.2 else OPEN)


def test_blink_rate_is_per_minute_of_eye_data_not_of_clock_time():
    seen_all, seen_half = DrowsinessAnalyzer(DROWSY), DrowsinessAnalyzer(DROWSY)
    for t in times(0.0, 180.0):
        whole = seen_all.update(blinking(t))
        visible = (t + 1.0) % 16.0 < 8.0  # in view 8 s (two blinks), gone 8 s; no blink is cut by an edge
        half = seen_half.update(blinking(t) if visible else no_face(t))
    assert whole.blink_rate == pytest.approx(15.0, abs=1.0)
    assert whole.blink_observed_s == pytest.approx(DROWSY.blink_window_s, abs=0.1)
    # Before: 8 a minute (the blinks of half a minute over a whole one).
    assert half.blink_rate == pytest.approx(15.0, abs=2.5)
    assert half.blink_observed_s == pytest.approx(DROWSY.blink_window_s / 2, abs=4.0)


def test_blink_rate_is_right_again_half_a_minute_after_the_scores_were_dropped():
    a = DrowsinessAnalyzer(DROWSY)
    for t in times(0.0, 120.0):
        a.update(blinking(t))
    a.forget_since(float("-inf"))  # enrollment done (M68)
    for t in times(120.0, 30.0):
        state = a.update(blinking(t))
    assert state.blink_observed_s == pytest.approx(30.0, abs=0.1)
    assert state.blink_rate == pytest.approx(15.0, abs=2.0)  # before: 8 (divided by a whole minute)


def test_the_blink_rule_waits_for_eye_data():
    engine = RiskEngine(replace(RiskEngine().config, blink_level=1))
    fast = replace(D0, blink_rate=40.0)
    assert engine.assess(replace(fast, blink_observed_s=engine.config.blink_min_observed_s), X0, C0).level == 1
    assert engine.assess(replace(fast, blink_observed_s=engine.config.blink_min_observed_s - 1), X0, C0).hits == ()


# ---------------------------------------------------------------- A2 L2: phone_ratio_2s


def phone_ratios(flags, moving=True):
    """flags: one phone flag per frame (None = no fresh detector result)."""
    a = DistractionAnalyzer(DISTRACTION)
    return [a.update(face(i * DT), flag, moving).phone_ratio_2s for i, flag in enumerate(flags)]


def test_one_detection_among_frames_without_a_result_is_not_a_phone():
    ratios = phone_ratios([None] * 30 + [True] + [None] * 30)
    assert max(ratios) == 0.0  # before: 1.0 for the two seconds the sample stayed in the window


def test_the_first_results_alone_do_not_decide():
    ratios = phone_ratios([True] * 90)
    need = round(DISTRACTION.phone_min_coverage_s * FPS)
    assert max(ratios[: need - 1]) == 0.0  # before: 1.0 from the first frame
    assert ratios[need + 1] == 1.0 and ratios[-1] == 1.0


def test_a_full_window_reads_as_before():
    flags = [i % 3 != 0 for i in range(150)]  # two frames in three with a phone
    assert phone_ratios(flags)[-1] == pytest.approx(2 / 3, abs=0.02)


# ---------------------------------------------------------------- A2 L3: no state without a limit


def drive(frames, speed=60.0, thresholds=None):
    th = thresholds or load_thresholds()
    th["enrollment"] = {**th["enrollment"], "enabled": False}
    p = DecisionPipeline(th)
    can = CanSimulator(scenario_from_dict({"start_clock": "12:00", "timeline": [{"t": 0, "speed_kmh": speed}]}))
    return p, [p.step(f, False, can.sample(f.timestamp)) for f in frames]


def asleep_then(rest):
    """Awake 20 s, eyes shut 1 s, head dropped 0.5 s, then `rest` (a function of t) for 60 s."""
    frames = [face(t) for t in times(0.0, 20.0)]
    frames += [face(t, SHUT) for t in times(20.0, 1.0)]
    frames += [face(t, SHUT, pitch=35.0) for t in times(21.0, 0.5)]
    return frames + [rest(t) for t in times(21.5, 60.0)]


def test_a_carried_closure_ends_when_nothing_has_been_in_view_for_too_long():
    lost_s = DROWSY.head_drop_carry_max_lost_s
    _, results = drive(asleep_then(no_face))
    by_t = {round(r.risk.t, 2): r for r in results}
    during = by_t[round(21.5 + lost_s - 1.0, 2)]
    assert during.drowsiness.head_drop and during.risk.level == 3 and not during.risk.unavailable
    after = by_t[round(21.5 + lost_s + 1.0, 2)]  # before: L3 for as long as the face stayed away
    assert not after.drowsiness.head_drop and after.drowsiness.closed_duration == 0.0
    assert after.risk.unavailable and after.risk.unavailable_reason == "no_face" and after.risk.level == 0
    assert any(r.presence.asking for r in results)  # "Bạn còn ở đó không?" runs again


def test_a_head_seen_down_keeps_the_carry_for_as_long_as_it_is_seen():
    _, results = drive(asleep_then(lambda t: face(t, SHUT, pitch=35.0)))
    last = results[-1]
    assert last.drowsiness.head_drop and last.risk.level == 3
    assert last.drowsiness.closed_duration > DROWSY.head_drop_carry_max_lost_s


def test_the_track_of_a_head_dip_stops_growing_once_it_cannot_be_a_nod():
    a = DrowsinessAnalyzer(DROWSY)
    for t in times(0.0, 10.0):
        a.update(face(t))
    longest, events = 0, []
    for t in times(10.0, 40.0):  # head held 18 deg down, eyes open, until the usual pose has followed
        events += a.update(face(t, pitch=18.0)).events
        longest = max(longest, len(a._nod._dip_track))
    assert longest <= DROWSY.nod_max_s * FPS + 2  # before: one sample per frame, 900 after 30 s
    assert events.count("bow") == 1 and "nod" not in events  # the dip still ends as before


# ---------------------------------------------------------------- A3 L2, L3, L6: trip memory, summary


def test_the_trend_is_fitted_when_a_minute_closes_not_on_every_frame(monkeypatch):
    calls = []
    real = trip_memory.linear_slope
    monkeypatch.setattr(trip_memory, "linear_slope", lambda *a: calls.append(1) or real(*a))
    memory = TripMemory()
    for i in range(5 * 60 * FPS + 1):
        state = memory.update(i * DT, 10.0 * (i * DT // 60))
    assert len(calls) == 5  # before: one fit per frame, 9001 of them
    assert state.minute_scores == (0.0, 10.0, 20.0, 30.0, 40.0)
    assert state.trend_15min == pytest.approx(10.0)


def test_a_skipped_minute_is_still_a_minute_on_the_time_axis():
    memory = TripMemory()
    for minute, score in ((0, 0.0), (1, 10.0), (11, 20.0), (12, 30.0)):  # minutes 2-10: a rest, not binned
        memory.update(minute * 60.0 + 1.0, score)
    state = memory.update(13 * 60.0 + 1.0, 0.0)
    assert state.minute_scores == (0.0, 10.0, 20.0, 30.0)
    assert linear_slope(state.minute_scores) == pytest.approx(10.0)  # before: 30 points in "3 minutes"
    assert state.trend_15min == pytest.approx(linear_slope((0.0, 10.0, 20.0, 30.0), (0, 1, 11, 12)))
    assert state.trend_15min < 5.0  # 30 points in 12 minutes, not in 3


def test_only_the_newest_microsleeps_are_kept_and_a_rest_still_takes_them_back():
    keep = TripMemoryConfig().microsleep_history
    memory = TripMemory()
    for i in range(keep * 5):
        state = memory.update(float(i), 0.0, ("microsleep",))
    assert len(memory._microsleeps) == keep and state.last_microsleep_t == keep * 5 - 1
    memory.forget_since(keep * 5 - 3)  # the vehicle stopped there
    assert memory.update(keep * 5.0, 0.0).last_microsleep_t == keep * 5 - 4


def test_the_summary_keeps_minutes_up_to_max_minutes():
    th = load_thresholds()
    th["trip_summary"] = {**th["trip_summary"], "max_minutes": 3}
    slow = 2  # frames per second: six minutes of them
    p, _ = drive([face(i / slow) for i in range(6 * 60 * slow)], thresholds=th)
    assert [m.minute for m in p.trip_log.minutes()] == [0, 1, 2, 3]  # before: one more for every minute


def test_drowsy_score_reads_zero_during_a_rest_and_not_at_a_red_light():
    tired = replace(D0, perclos_60s=0.5, yawn_count_10min=3)
    engine = RiskEngine()
    red_light = replace(C0, speed_kmh=0.0, moving=False, stationary=True, stationary_s=30.0)
    rest = replace(red_light, stationary_s=600.0, resting=True)
    assert engine.assess(tired, X0, red_light).drowsy_score > 0  # the stop may end in a second
    r = engine.assess(tired, X0, rest)  # before: 55 points on the HUD next to level 0
    assert r.drowsy_score == 0.0 and set(r.drowsy_terms) == {0.0} and r.level == 0


def turn_sides(signal_at, speed_at=lambda t: 60.0, seconds=80.0, step=0.5):
    tracker = ContextTracker(CONTEXT)
    out = {}
    for i in range(round(seconds / step)):
        t = i * step
        out[t] = tracker.update(VehicleSignals(t, speed_at(t), signal_at(t), t, 12.0)).turn_side
    return out


def test_a_turn_signal_left_on_stops_widening_the_yaw_limit():
    limit, grace = CONTEXT.turn_signal_max_s, CONTEXT.turn_signal_grace_s
    sides = turn_sides(lambda t: "left")
    assert sides[limit - 1.0] == "left"
    assert sides[limit + grace + 1.0] is None and sides[79.5] is None  # before: "left" for ever


def test_the_signal_counts_again_after_it_went_off_or_changed_side():
    limit = CONTEXT.turn_signal_max_s
    off_then_on = turn_sides(lambda t: None if limit + 10 <= t < limit + 12 else "left")
    assert off_then_on[limit + 9.0] is None and off_then_on[limit + 13.0] == "left"
    other_side = turn_sides(lambda t: "left" if t < limit + 10 else "right")
    assert other_side[limit + 9.0] is None and other_side[limit + 11.0] == "right"


def test_waiting_to_turn_is_not_counted():
    limit = CONTEXT.turn_signal_max_s
    sides = turn_sides(lambda t: "left", speed_at=lambda t: 0.0 if t < 60.0 else 20.0, seconds=100.0)
    assert sides[60.0 + limit - 1.0] == "left"  # a minute at the light, then the turn


# ---------------------------------------------------------------- A4 L2: the outbox


def event(reason="camera_lost"):
    return build_system_event(reason, "trip-1")


def wait_for(condition, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.01)
    return False


def test_the_loop_does_not_wait_for_the_disk(tmp_path, monkeypatch):
    slow_s = 0.3
    real = Outbox.put_many

    def slow_put(self, events, max_queue):
        time.sleep(slow_s)  # eMMC storage on a bad day
        return real(self, events, max_queue)

    monkeypatch.setattr(Outbox, "put_many", slow_put)
    sent = []
    cfg = PublisherConfig(outbox_path=str(tmp_path / "o.db"), flush_interval_s=3600)
    with MetadataPublisher("cam-001", lambda body: sent.append(body) or 200, cfg) as pub:
        started = time.monotonic()
        pub.publish(event())
        assert time.monotonic() - started < slow_s / 3  # before: the write was done right here
        assert pub.queued == 1  # counted while it is still in memory
        assert wait_for(lambda: pub._outbox.count() == 1)  # on disk at once, without waiting for a flush
        assert sent == []  # ... and not sent: nothing urgent, the interval has not passed
    assert [len(b["events"]) for b in sent if "events" in b] == [1]  # stop() sends what is left


def test_an_urgent_event_is_written_and_sent_at_once_by_the_thread(tmp_path):
    sent = []
    cfg = PublisherConfig(outbox_path=str(tmp_path / "o.db"), flush_interval_s=3600)
    with MetadataPublisher("cam-001", lambda body: sent.append(body) or 200, cfg) as pub:
        pub.publish(event("no_answer"))
        assert wait_for(lambda: len(sent) == 1) and pub.queued == 0


def test_records_handed_over_but_not_written_yet_are_not_lost_on_stop(tmp_path, monkeypatch):
    path = str(tmp_path / "o.db")
    pub = MetadataPublisher("cam-001", lambda body: 503, PublisherConfig(outbox_path=path)).start()
    monkeypatch.setattr(pub, "_persist", lambda: None)  # the thread never gets to write
    for _ in range(3):
        pub.publish(event())
    monkeypatch.undo()
    pub.stop()
    assert pub.queued == 3
    assert MetadataPublisher("cam-001", lambda body: 200, PublisherConfig(outbox_path=path)).queued == 3


def test_the_outbox_counts_without_a_query_per_record(tmp_path):
    path = str(tmp_path / "o.db")
    box = Outbox(path)
    assert box.put_many([{"n": i} for i in range(5)], max_queue=4) == 1 and box.count() == 4
    box.delete([i for i, _ in box.peek(2)])
    box.delete([999])  # not there: nothing is taken off the count
    assert box.count() == 2 and [rec["data"]["n"] for _, rec in box.peek(10)] == [3, 4]
    box.close()
    assert Outbox(path).count() == 2  # counted once when it is opened


@pytest.mark.skipif(os.name == "nt", reason="POSIX file modes")
def test_the_outbox_file_is_its_owners_only(tmp_path):
    path = tmp_path / "o.db"
    Outbox(str(path)).close()
    assert stat.S_IMODE(path.stat().st_mode) == publisher_module.OWNER_ONLY


def test_retries_are_spread_by_the_jitter(tmp_path):
    cfg = PublisherConfig(outbox_path=":memory:", backoff_initial_s=10.0)
    waits = []
    for share in (0.0, 0.5, 1.0):
        pub = MetadataPublisher("cam-001", lambda body: 503, cfg, clock=lambda: 0.0, jitter=lambda s=share: s)
        pub.publish(event())
        pub.flush_once()
        waits.append(pub._next_attempt)
    assert waits == pytest.approx([10.0, 10.0 * (1 + cfg.backoff_jitter / 2), 10.0 * (1 + cfg.backoff_jitter)])


# ---------------------------------------------------------------- A4 L3, L4, A1 L5: the page


def test_the_page_does_not_need_sqlite3():
    code = "import sys, edge_agent.web.bridge; sys.exit('sqlite3' in sys.modules)"
    done = subprocess.run([sys.executable, "-c", code], cwd=PROJECT_ROOT, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr  # before: publisher.py imported it for an outbox the page lacks


def test_the_pages_queue_is_capped_like_the_outbox():
    agent = WebAgent("web-an", "trip-web-1", scenario="highway_night")
    assert json.loads(agent.settings())["max_queue"] == TH["publisher"]["max_queue"]  # the page's own cap
    agent.publisher_cfg = replace(agent.publisher_cfg, max_queue=3)
    for i in range(5):
        agent._queue("sample", {"n": i})
    assert agent.dropped_records == 2
    assert [s["n"] for s in json.loads(agent.take_batch())["samples"]] == [2, 3, 4]  # the oldest went


def two_faces():
    driver = synthetic_face()
    passenger = synthetic_face()
    passenger[:, :2] = (passenger[:, :2] - passenger[1, :2]) * 0.6 + (120, 300)  # further back
    return np.stack([passenger, driver]).ravel()  # the driver is the second face


def seen_by_block_6(agent, monkeypatch):
    seen = []
    real = agent.runtime.step
    monkeypatch.setattr(agent.runtime, "step", lambda f, *a, **k: seen.append(f) or real(f, *a, **k))
    return seen


def test_brightness_and_sharpness_are_the_drivers_not_the_first_or_largest_faces(monkeypatch):
    agent = WebAgent("web-an", "trip-web-1", scenario="highway_night")
    seen = seen_by_block_6(agent, monkeypatch)
    blink = (0.05,) * 4
    agent.frame(0.0, 0, W, H, two_faces(), 2, blink, 12.0, [30.0, 140.0], None, 90.0, 40.0, [5.0, 250.0])
    assert seen[-1].face_brightness == 140.0 and seen[-1].sharpness == 250.0
    # Not measured (NaN from the page) is unknown, not a number.
    agent.frame(DT, 1, W, H, two_faces(), 2, blink, 12.0, [30.0, 140.0], None, 90.0, 40.0, [5.0, float("nan")])
    assert seen[-1].sharpness is None
    # One plain number, as an older page sends it, is taken as it is.
    agent.frame(2 * DT, 2, W, H, two_faces(), 2, blink, 12.0, 77.0, None, 90.0, 40.0, 9.0)
    assert seen[-1].face_brightness == 77.0 and seen[-1].sharpness == 9.0


def test_without_a_driver_the_frames_own_brightness_is_used(monkeypatch):
    agent = WebAgent("web-an", "trip-web-1", scenario="highway_night")
    seen = seen_by_block_6(agent, monkeypatch)
    state = json.loads(agent.frame(0.0, 0, W, H, None, 0, None, 12.0, 55.0, None, 90.0, 40.0, None))
    assert state["measures"]["face"] is False and "error" not in state
    assert seen[-1].face_brightness is None and seen[-1].sharpness is None


def test_a_detector_result_is_held_against_the_face_of_its_own_frame():
    memory = FaceBoxMemory(max_age_s=3.0, history_s=0.6)
    then, now = (100.0, 100.0, 200.0, 200.0), (300.0, 100.0, 400.0, 200.0)  # the head moved 200 px
    memory.update(then, 1.0)
    memory.update(then, 1.1)
    assert memory.update(now, 1.3) == now
    assert memory.at(1.15) == then and memory.at(1.3) == now  # before: `now` for a result of t = 1.15
    assert memory.at(0.0) == then  # older than anything kept: the oldest
    memory.update(None, 2.5)
    assert memory.at(2.5) == now  # a face lost is still remembered for max_age_s
    assert len(memory._history) == 1  # only history_s of it
    assert FaceBoxMemory(3.0).update(now, 0.0) == now and FaceBoxMemory(3.0).at(0.0) is None


# ---------------------------------------------------------------- A1 L5: stop() and a reader stuck in read()


class StuckCamera:
    """A capture whose read() does not return until the test lets it."""

    def __init__(self):
        self.go = threading.Event()
        self.released_while_reading = False
        self.released = threading.Event()
        self._reading = False

    def isOpened(self):  # noqa: N802 - OpenCV's name
        return True

    def set(self, *args):
        return True

    def get(self, prop):
        return 30.0

    def read(self):
        self._reading = True
        self.go.wait(10.0)
        self._reading = False
        return False, None

    def release(self):
        self.released_while_reading = self._reading
        self.released.set()


def test_stop_does_not_release_a_camera_that_is_still_being_read():
    camera = StuckCamera()
    source = FrameSource(0, CaptureConfig.from_dict(TH["capture"]), capture_factory=lambda s: camera).start()
    assert wait_for(lambda: camera._reading)
    source.stop()  # gives up waiting for the reader
    assert not camera.released.is_set()  # before: released under the running read()
    camera.go.set()
    assert camera.released.wait(3.0) and not camera.released_while_reading  # the reader lets go itself


def test_stop_releases_the_camera_itself_when_the_reader_has_finished():
    camera = StuckCamera()
    camera.go.set()  # read() returns at once
    cfg = replace(CaptureConfig.from_dict(TH["capture"]), max_consecutive_failures=1, reconnect_interval_s=0.0)
    source = FrameSource(0, cfg, capture_factory=lambda s: camera).start()
    assert wait_for(lambda: source.ended)
    source.stop()
    assert camera.released.is_set() and not camera.released_while_reading
