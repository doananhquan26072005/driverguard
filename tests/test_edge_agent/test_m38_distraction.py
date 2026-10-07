"""M38 - block 8 additions: many short glances (measured only), call / text (recorded only), and a
face lost right after a large head turn (off road goes on instead of "monitoring unavailable").

Fake sequences of head angles, phone boxes and face boxes; no video.
"""

from datetime import UTC, datetime, timedelta

import pytest

from edge_agent.analysis.distraction import DistractionAnalyzer, DistractionConfig
from edge_agent.config import load_thresholds
from edge_agent.context.can_sim import CanSimulator, scenario_from_dict
from edge_agent.decision.pipeline import DecisionPipeline
from edge_agent.io.publisher import build_event, build_sample
from edge_agent.perception.features import FrameFeatures
from edge_agent.perception.phone_detector import PhoneDetection, PhoneDetectorConfig, phone_kind, phone_near_face

FPS = 30
DT = 1.0 / FPS
FACE = (200.0, 100.0, 300.0, 220.0)  # x1, y1, x2, y2: 100 wide, 120 high


def feats(t, yaw=0.0, pitch=0.0, face=True):
    if not face:
        return FrameFeatures(frame_id=round(t * FPS), timestamp=t, face_found=False, face_conf=0.0)
    return FrameFeatures(round(t * FPS), t, True, 1.0, ear=0.3, mar=0.05, pitch=pitch, yaw=yaw, roll=0.0)


def analyzer(**kw):
    return DistractionAnalyzer(DistractionConfig(baseline_adapt=False, **kw))


def run(a, t0, seconds, moving=True, phone=False, turn=None, kind=None, **pose):
    state = None
    n = round(seconds * FPS)
    for i in range(n):
        state = a.update(feats(t0 + i * DT, **pose), phone, moving, turn, phone_kind=kind)
    return state, t0 + n * DT


def glance_cycles(a, t, cycles, away_s=1.5, back_s=0.5, turn=None, yaw=45.0):
    worst = 0.0
    for _ in range(cycles):
        s, t = run(a, t, away_s, yaw=yaw, turn=turn)
        worst = max(worst, s.off_road_duration)
        s, t = run(a, t, back_s, turn=turn)
    return s, t, worst


def phone_at(cx, cy, score=0.8, size=40.0):
    return PhoneDetection((cx - size / 2, cy - size / 2, cx + size / 2, cy + size / 2), score)


# ---------------------------------------------------------------- many short glances (measured only)


def test_repeated_short_glances_raise_the_ratio_but_never_the_continuous_timer():
    a = analyzer()
    _, t = run(a, 0.0, 5.0)
    s, _, worst = glance_cycles(a, t, 10)
    assert worst < 2.0  # the continuous rule (risk.distraction.off_road_s) is never reached
    assert s.off_road_ratio == pytest.approx(0.8, abs=0.1)  # away 1.5 s + the 0.3 s it takes to confirm the return
    assert s.glance_count >= 10


def test_one_look_at_the_mirror_stays_low():
    a = analyzer()
    _, t = run(a, 0.0, 15.0)
    _, t = run(a, t, 1.0, yaw=45.0)
    s, _ = run(a, t, 10.0)
    assert s.glance_count == 1
    assert s.off_road_ratio < 0.1


def test_ratio_waits_for_enough_driving_in_the_window():
    a = analyzer(glance_min_coverage_s=10.0)
    s, t = run(a, 0.0, 3.0, yaw=45.0)
    assert s.off_road and s.off_road_ratio == 0.0 and s.glance_count == 1
    s, _ = run(a, t, 8.0, yaw=45.0)
    assert s.off_road_ratio == pytest.approx(1.0, abs=0.01)


def test_old_glances_leave_the_window():
    a = analyzer(glance_window_s=30.0)
    _, t = run(a, 0.0, 5.0)
    _, t, _ = glance_cycles(a, t, 5)
    s, _ = run(a, t, 31.0)
    assert s.glance_count == 0 and s.off_road_ratio == 0.0


def test_looking_to_the_signalled_side_is_not_a_glance():
    a = analyzer()
    _, t = run(a, 0.0, 5.0)
    s, t, _ = glance_cycles(a, t, 5, turn="left", yaw=45.0)  # left = yaw > 0 (left_yaw_sign 1)
    assert s.glance_count == 0 and s.off_road_ratio == 0.0
    s, _, _ = glance_cycles(a, t, 5, turn="left", yaw=-45.0)  # the other side still counts
    assert s.glance_count == 5 and s.off_road_ratio > 0.2


def test_a_stop_clears_the_window():
    a = analyzer()
    _, t = run(a, 0.0, 5.0)
    _, t, _ = glance_cycles(a, t, 5)
    s, t = run(a, t, 1.0, moving=False)  # red light
    assert s.off_road_ratio == 0.0 and s.glance_count == 0
    s, _ = run(a, t, 12.0)
    assert s.off_road_ratio == 0.0 and s.glance_count == 0


def test_a_stall_between_frames_adds_no_time():
    a = analyzer(glance_max_gap_s=0.5)
    _, t = run(a, 0.0, 12.0)
    a.update(feats(t + 20.0, yaw=45.0), False, True)  # 20 s without a frame, then off road
    s, _ = run(a, t + 20.0 + DT, 1.0)
    assert s.off_road_ratio < 0.2


# ---------------------------------------------------------------- call / text (recorded only)


@pytest.mark.parametrize(
    ("cx", "cy", "kind"),
    [
        (330.0, 160.0, "call"),  # beside the face, at ear height (image right)
        (170.0, 150.0, "call"),  # the other ear
        (250.0, 300.0, "text"),  # below the chin, in front of the chest
        (330.0, 300.0, "text"),  # below the chin and to the side: still below
        (250.0, 160.0, "unknown"),  # in front of the face
        (250.0, 600.0, None),  # outside the driver zone (lap / passenger)
    ],
)
def test_phone_kind_from_where_the_box_sits(cx, cy, kind):
    cfg = PhoneDetectorConfig()
    dets = (phone_at(cx, cy),)
    assert phone_kind(dets, FACE, cfg) == kind
    assert phone_near_face(dets, FACE, cfg) is (kind is not None)


def test_phone_kind_without_a_face_or_a_phone():
    cfg = PhoneDetectorConfig()
    assert phone_kind((phone_at(330.0, 160.0),), None, cfg) is None
    assert phone_kind((), FACE, cfg) is None


def test_phone_kind_takes_the_best_scored_phone_in_the_zone():
    cfg = PhoneDetectorConfig()
    dets = (phone_at(250.0, 300.0, score=0.9), phone_at(330.0, 160.0, score=0.5))  # sorted by score, as YOLO gives
    assert phone_kind(dets, FACE, cfg) == "text"
    passenger = (phone_at(900.0, 300.0, score=0.95), phone_at(330.0, 160.0, score=0.5))
    assert phone_kind(passenger, FACE, cfg) == "call"


def test_kind_of_the_window_is_the_most_frequent_one():
    a = analyzer()
    _, t = run(a, 0.0, 1.0)
    s, t = run(a, t, 1.2, phone=True, kind="text")
    assert s.phone_kind == "text"
    s, t = run(a, t, 0.5, phone=True, kind="call")  # a few frames at the ear do not flip it
    assert s.phone_kind == "text"
    s, t = run(a, t, 2.0, phone=True, kind="call")
    assert s.phone_kind == "call"
    s, _ = run(a, t, 2.5)  # phone gone
    assert s.phone_kind is None and s.phone_ratio_2s == 0.0


def test_kind_is_unknown_when_none_is_given_or_on_a_tie():
    a = analyzer()
    s, t = run(a, 0.0, 1.0, phone=True)  # callers older than M38
    assert s.phone_kind == "unknown"
    b = analyzer()
    _, t = run(b, 0.0, 1.0, phone=True, kind="call")
    s, _ = run(b, t, 1.0, phone=True, kind="text")
    assert s.phone_kind == "unknown"


# ---------------------------------------------------------------- the whole chain (blocks 7-12)


def pipeline_run(seconds, frame_at, phone_at_t=None, kind_at=None, turn=None, **overrides):
    """Decision chain at 60 km/h. frame_at(t) -> dict(yaw=..., face=...). Returns (alerts, results, pipeline)."""
    th = load_thresholds()
    th["enrollment"] = {**th["enrollment"], "enabled": False}
    for section, values in overrides.items():
        th[section] = {**th[section], **values}
    pipeline = DecisionPipeline(th)
    timeline = [{"t": 0, "speed_kmh": 60}]
    if turn is not None:
        timeline += [{"t": turn[0], "speed_kmh": 60, "turn_signal": "left"}]
        timeline += [{"t": turn[1], "speed_kmh": 60, "turn_signal": "off"}]
    timeline.append({"t": 100000, "speed_kmh": 60})
    can = CanSimulator(scenario_from_dict({"name": "t", "start_clock": "15:00", "timeline": timeline}))
    alerts, results = [], []
    for i in range(round(seconds * FPS)):
        t = i / FPS
        phone = phone_at_t(t) if phone_at_t else False
        r = pipeline.step(feats(t, **frame_at(t)), phone, can.sample(t), kind_at(t) if kind_at else None)
        results.append(r)
        if r.alert.new_alert is not None:
            alerts.append((round(r.alert.new_alert.t, 1), r.alert.new_alert.level, r.alert.new_alert.reasons))
    return alerts, results, pipeline


def at(results, t):
    return results[round(t * FPS)]


def turn_then_lost(turn_at=8.0, lost_from=9.0, lost_to=19.0, yaw=60.0):
    def frame(t):
        if lost_from <= t < lost_to:
            return {"face": False}
        if turn_at <= t < lost_from:
            return {"yaw": (t - turn_at) / (lost_from - turn_at) * yaw}
        return {}

    return frame


def test_before_m38_a_driver_looking_behind_became_unavailable_after_one_alert():
    """The behaviour docs/improvements.md described, pinned with the rule switched off."""
    alerts, results, _ = pipeline_run(25, turn_then_lost(), distraction={"turned_away": {"yaw_deg": 0}})
    assert [(lv, rs) for _, lv, rs in alerts] == [(2, ("off_road",))]
    assert at(results, 13.0).risk.unavailable and at(results, 13.0).risk.level == 0
    assert at(results, 16.0).alert.active_level == 0  # silent while the driver still looks behind


def test_looking_behind_stays_off_road_instead_of_unavailable():
    alerts, results, pipeline = pipeline_run(25, turn_then_lost())
    assert [(lv, rs) for _, lv, rs in alerts] == [(2, ("off_road",))]  # no extra alert
    for t in (12.5, 15.0, 18.5):
        r = at(results, t)
        assert r.distraction.turned_away and not r.risk.unavailable
        assert r.risk.reasons == ("off_road",) and r.alert.active_level == 2
    assert not at(results, 20.0).distraction.turned_away  # the face is back
    assert at(results, 20.0).risk.level == 0
    s = pipeline.trip_log.summary("trip-t", datetime.now(UTC), datetime.now(UTC) + timedelta(seconds=25))
    assert s.turned_away_s == pytest.approx(10.0, abs=0.2)
    assert s.unavailable_s == 0.0


def test_looking_behind_for_too_long_becomes_unavailable():
    _, results, pipeline = pipeline_run(40, turn_then_lost(lost_to=35.0))
    assert at(results, 18.5).distraction.turned_away
    late = at(results, 19.5)  # 10 s (distraction.turned_away.max_s) after the face was lost
    assert not late.distraction.turned_away and late.risk.unavailable and late.risk.level == 0
    s = pipeline.trip_log.summary("trip-t", datetime.now(UTC), datetime.now(UTC) + timedelta(seconds=40))
    assert s.turned_away_s == pytest.approx(10.0, abs=0.2)
    assert s.unavailable_s == pytest.approx(16.0, abs=0.3)


def test_face_lost_while_looking_ahead_is_unavailable_as_before():
    alerts, results, _ = pipeline_run(20, lambda t: {"face": False} if 9.0 <= t < 16.0 else {})
    assert alerts == []
    assert not at(results, 11.0).distraction.turned_away
    assert at(results, 12.5).risk.unavailable


def test_a_small_head_turn_before_the_face_is_lost_is_not_looking_behind():
    """Off road (35 deg) but below turned_away.yaw_deg (45): the old behaviour."""
    _, results, _ = pipeline_run(25, turn_then_lost(yaw=35.0))
    assert not at(results, 12.5).distraction.turned_away
    assert at(results, 12.5).risk.unavailable


def test_turning_to_the_signalled_side_is_not_looking_behind():
    """Left signal: 50 deg to the left is inside the widened limit (30 + 30), so not off road."""
    _, results, _ = pipeline_run(25, turn_then_lost(yaw=50.0), turn=(7.0, 20.0))
    assert not at(results, 10.0).distraction.off_road
    assert not at(results, 12.5).distraction.turned_away
    assert at(results, 12.5).risk.unavailable


def test_a_stale_head_turn_does_not_count():
    """Turned far, then a partly visible face (pose not trusted) for longer than pose_age_s, then lost."""
    pose_age = DistractionConfig().turned_away_pose_age_s
    a = analyzer()
    _, t = run(a, 0.0, 8.0)
    _, t = run(a, t, 1.0, yaw=60.0)
    n = round((pose_age + 0.5) * FPS)
    for i in range(n):  # face found, not reliable
        a.update(FrameFeatures(0, t + i * DT, True, 0.5, face_reliable=False, yaw=60.0, pitch=0.0), False, True)
    s, _ = run(a, t + n * DT, 1.0, face=False)
    assert not s.turned_away
    b = analyzer()
    _, t = run(b, 0.0, 8.0)
    _, t = run(b, t, 1.0, yaw=60.0)
    s, _ = run(b, t, 1.0, face=False)  # lost at once: counts
    assert s.turned_away


def test_short_glances_reach_the_summary_without_an_alert():
    def frame(t):
        return {"yaw": 45.0} if t >= 10.0 and (t - 10.0) % 2.0 < 1.5 else {}

    alerts, results, pipeline = pipeline_run(40, frame)
    assert alerts == []  # measured only: no rule reads off_road_ratio
    assert results[-1].distraction.off_road_ratio > 0.6
    assert max(r.risk.distraction_score for r in results) < 100.0
    s = pipeline.trip_log.summary("trip-t", datetime.now(UTC), datetime.now(UTC) + timedelta(seconds=40))
    assert s.glances == 15 and s.off_road_ratio_max > 0.6


def test_unavailable_clears_the_glance_window():
    def frame(t):
        if 30.0 <= t < 36.0:
            return {"face": False}
        return {"yaw": 45.0} if 10.0 <= t < 30.0 and (t - 10.0) % 2.0 < 1.5 else {}

    _, results, _ = pipeline_run(40, frame)
    assert at(results, 29.9).distraction.glance_count > 5
    assert at(results, 34.0).risk.unavailable
    assert at(results, 37.0).distraction.glance_count == 0 and at(results, 37.0).distraction.off_road_ratio == 0.0


def test_phone_alert_carries_the_kind_and_the_summary_splits_the_time():
    alerts, results, pipeline = pipeline_run(
        30,
        lambda t: {},
        phone_at_t=lambda t: 5.0 <= t < 11.0 or 15.0 <= t < 19.0,
        kind_at=lambda t: "call" if t < 12.0 else "text",
    )
    assert [(lv, rs) for _, lv, rs in alerts] == [(2, ("phone",))]  # second one: same reason within the cooldown
    r = next(r for r in results if r.alert.new_alert is not None)
    event = build_event(r.alert.new_alert, r, "trip-t")
    assert event["reasons"] == ["phone"] and event["level"] == 2  # reason and level unchanged
    assert event["metrics"]["phone_kind"] == "call"
    s = pipeline.trip_log.summary("trip-t", datetime.now(UTC), datetime.now(UTC) + timedelta(seconds=30))
    assert s.phone_call_s == pytest.approx(6.0, abs=1.5) and s.phone_text_s == pytest.approx(4.0, abs=1.5)
    assert s.phone_call_s + s.phone_text_s <= s.phone_s + 0.1


# ---------------------------------------------------------------- metadata


def test_sample_without_the_ratio_is_unchanged():
    assert "off_road_ratio" not in build_sample(10.0, None, 0, "trip-t")
