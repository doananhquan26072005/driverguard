"""M80: the two "looking at the road" head poses (audit 08/10, A2 M1 and M2).

- Block 8: a baseline that is wrong by more than the off-road limit (the driver looked aside during
  the start-up calibration, the camera moved mid-trip) used to keep L2 "off road" up for the whole
  trip. A pose held outside the band, still, for `baseline.recalibrate_s` of driving is the road pose.
- Block 7: the usual head pose only learns while the vehicle is moving; a look at the screen at a
  short stop used to shift it for half a minute after driving off.

Fake sequences, the real config/thresholds.yaml, no video.
"""

import pytest

from backend.schemas import EventBatch
from edge_agent.analysis.distraction import DistractionAnalyzer, DistractionConfig
from edge_agent.analysis.drowsiness import DrowsinessAnalyzer, DrowsinessConfig
from edge_agent.config import load_thresholds
from edge_agent.context.can_sim import CanSimulator, scenario_from_dict
from edge_agent.decision.pipeline import DecisionPipeline
from edge_agent.io.publisher import batch_body
from edge_agent.perception.features import FrameFeatures
from tests.test_edge_agent.test_runtime import make

FPS = 30.0
RECAL_S = 60.0  # distraction.baseline.recalibrate_s in config/thresholds.yaml


def features(i, t, yaw=0.0, pitch=0.0, ear=0.30):
    return FrameFeatures(i, t, True, 1.0, ear=ear, mar=0.05, pitch=pitch, yaw=yaw, roll=0.0)


def drive(pose, seconds, speeds=((0, 60),), enrolled=None, fps=FPS, over=None):
    """The decision chain on pose(t) -> (yaw, pitch). Returns [(t, result)]."""
    th = load_thresholds()
    th["enrollment"] = {**th["enrollment"], "enabled": False}
    if over:
        th["distraction"] = {**th["distraction"], "baseline": {**th["distraction"]["baseline"], **over}}
    pipeline = DecisionPipeline(th)
    if enrolled is not None:
        pipeline.drowsiness.set_profile(0.30, 0.05, *enrolled)
        pipeline.distraction.set_road_pose(*enrolled)
    timeline = [{"t": t, "speed_kmh": v} for t, v in speeds] + [{"t": 100000, "speed_kmh": speeds[-1][1]}]
    can = CanSimulator(
        scenario_from_dict({"name": "t", "start_clock": "15:00", "initial_drive_time_s": 600, "timeline": timeline})
    )
    out = []
    for i in range(round(seconds * fps)):
        t = i / fps
        yaw, pitch = pose(t)
        out.append((t, pipeline.step(features(i, t, yaw, pitch), False, can.sample(t))))
    return out


def recalibrations(results):
    return [round(t, 1) for t, r in results if r.distraction.recalibrated]


def alerts(results, since=0.0):
    return [
        (round(t, 1), r.alert.new_alert.level, r.alert.new_alert.reasons)
        for t, r in results
        if r.alert.new_alert is not None and t >= since
    ]


def analyzer(**over):
    cfg = DistractionConfig.from_dict(load_thresholds()["distraction"])
    return DistractionAnalyzer(DistractionConfig(**{**cfg.__dict__, **over}))


def feed(a, t0, seconds, yaw=0.0, pitch=0.0, moving=True, gaze_down=False, fps=FPS):
    """Identical frames to block 8 alone. Returns (states, next t)."""
    states = []
    n = round(seconds * fps)
    for i in range(n):
        t = t0 + i / fps
        states.append(a.update(features(i, t, yaw, pitch), False, moving, gaze_down=gaze_down))
    return states, t0 + n / fps


# ---------------------------------------------------------------- block 8: recalibration


def test_a_start_up_calibration_on_a_look_aside_heals_itself():
    """Audit A2 M1: 40 deg aside for the first 6 s, then the road. Before: L2 on 99 % of the trip."""
    results = drive(lambda t: (40.0 if t < 6 else 0.0, 0.0), 300)
    fired = recalibrations(results)
    assert len(fired) == 1 and fired[0] == pytest.approx(6.0 + RECAL_S, abs=1.5)
    last = results[-1][1].distraction
    assert last.baseline_yaw == pytest.approx(0.0, abs=0.5) and not last.off_road
    assert all(r.risk.level == 0 for t, r in results if t > fired[0] + 4.0)  # past alert.fall_hold_s
    assert alerts(results, since=fired[0]) == []


def test_a_real_look_away_is_caught_again_after_the_recalibration():
    """Before: the level never changed, so a real 10 s look to the other side raised nothing new."""
    results = drive(lambda t: (40.0 if t < 6 else (-45.0 if 200 <= t < 210 else 0.0), 0.0), 240)
    late = alerts(results, since=200.0)
    assert [(lv, reasons) for _, lv, reasons in late] == [(2, ("off_road",))]
    assert late[0][0] == pytest.approx(202.5, abs=0.3)  # off_road_s + rise_confirm_s


def test_a_camera_that_moves_mid_trip_heals_itself_enrolled_or_not():
    for enrolled in (None, (0.0, 0.0)):
        results = drive(lambda t: (35.0 if t >= 120 else 0.0, 0.0), 300, enrolled=enrolled)
        fired = recalibrations(results)
        assert len(fired) == 1 and fired[0] == pytest.approx(120.0 + RECAL_S, abs=1.5)
        assert results[-1][1].distraction.baseline_yaw == pytest.approx(35.0, abs=0.5)
        assert not results[-1][1].distraction.off_road


def test_off_means_the_old_behaviour():
    results = drive(lambda t: (40.0 if t < 6 else 0.0, 0.0), 200, over={"recalibrate_s": 0})
    assert recalibrations(results) == []
    assert results[-1][1].distraction.off_road and results[-1][1].distraction.baseline_yaw == pytest.approx(40.0)


def test_a_look_back_at_the_road_starts_the_count_again():
    """A real look away is interrupted by looks at the road: never the road pose, however long in total."""
    a = analyzer(baseline_calibrate_s=0.0)
    t, states = 0.0, []
    for _ in range(10):  # 10 x (40 s away, 0.5 s back)
        s, t = feed(a, t, 40.0, yaw=45.0)
        states += s
        s, t = feed(a, t, 0.5, yaw=0.0)
        states += s
    assert not any(s.recalibrated for s in states)
    assert a.baseline_yaw == pytest.approx(0.0, abs=1.0)


def test_a_single_frame_inside_the_band_does_not_start_it_again():
    """on_road_confirm_s, as for the off-road timer: one noisy frame is not a look back."""
    a = analyzer(baseline_calibrate_s=0.0)
    _, t = feed(a, 0.0, 40.0, yaw=45.0)
    _, t = feed(a, t, 0.1, yaw=0.0)
    states, _ = feed(a, t, 25.0, yaw=45.0)
    assert sum(s.recalibrated for s in states) == 1


def test_a_head_that_moves_about_is_not_a_wrong_baseline():
    """Outside the band all the time but not still (35 <-> 60 deg every 2 s): range above spread_deg."""
    a = analyzer(baseline_calibrate_s=0.0)
    states = []
    for i in range(round(180 * FPS)):
        t = i / FPS
        states.append(a.update(features(i, t, 35.0 if int(t / 2) % 2 else 60.0), False, True))
    assert not any(s.recalibrated for s in states) and states[-1].off_road


def test_small_head_movement_around_the_held_pose_is_still_one_pose():
    a = analyzer(baseline_calibrate_s=0.0)
    states = []
    for i in range(round(70 * FPS)):
        t = i / FPS
        states.append(a.update(features(i, t, 40.0 + 3.0 * (-1) ** int(t), 2.0), False, True))
    assert sum(s.recalibrated for s in states) == 1
    assert a.baseline_yaw == pytest.approx(40.0, abs=3.5)


def test_a_stop_pauses_the_count_and_does_not_clear_it():
    """Driving time only: 40 s away, 60 s at a red light, then 20 s more of the same pose."""
    a = analyzer(baseline_calibrate_s=0.0)
    s1, t = feed(a, 0.0, 40.0, yaw=40.0)
    s2, t = feed(a, t, 60.0, yaw=40.0, moving=False)
    s3, t = feed(a, t, 19.0, yaw=40.0)
    assert not any(s.recalibrated for s in s1 + s2 + s3)
    s4, _ = feed(a, t, 3.0, yaw=40.0)
    assert sum(s.recalibrated for s in s4) == 1


def test_lowered_lids_with_a_bowed_head_never_become_the_road_pose():
    """Block 7's gaze_down (a phone on the lap): head down and still for minutes, not recalibrated."""
    a = analyzer(baseline_calibrate_s=0.0)
    states, _ = feed(a, 0.0, 180.0, pitch=25.0, gaze_down=True)
    assert not any(s.recalibrated for s in states)
    assert states[-1].off_road and a.baseline_pitch == pytest.approx(0.0)


@pytest.mark.parametrize("fps", [10.0, 15.0])
def test_it_takes_the_same_driving_time_at_a_low_frame_rate(fps):
    a = analyzer(baseline_calibrate_s=0.0)
    states, _ = feed(a, 0.0, 70.0, yaw=40.0, fps=fps)
    fired = [s.timestamp for s in states if s.recalibrated]
    assert len(fired) == 1 and fired[0] == pytest.approx(RECAL_S, abs=1.5)


def test_frames_far_apart_add_at_most_max_gap_s_each():
    """A loop that delivers a frame every 2 s has not watched the driver for 60 s after 60 s."""
    a = analyzer(baseline_calibrate_s=0.0)
    states, t = feed(a, 0.0, 100.0, yaw=40.0, fps=0.5)
    assert not any(s.recalibrated for s in states)  # 50 frames x max_gap_s 0.5 = 25 s seen
    states, _ = feed(a, t, 150.0, yaw=40.0, fps=0.5)
    assert sum(s.recalibrated for s in states) == 1


def test_thresholds_file_keeps_recalibration_far_above_the_alert_time():
    th = load_thresholds()
    cfg = DistractionConfig.from_dict(th["distraction"])
    assert cfg.baseline_recalibrate_s >= 10 * th["risk"]["distraction"]["off_road_s"]
    assert 0 < cfg.baseline_recalibrate_spread_deg < cfg.yaw_off_road_deg


def test_runtime_tells_the_backend_once():
    rt, rec, _ = make()
    for i in range(round(80 * FPS)):
        t = i / FPS
        rt.step(features(i, t, 40.0 if t < 6 else 0.0), False, t, clock=t)
    system = [d for k, d in rec.records if k == "event" and d["type"] == "system"]
    assert [e["reasons"] for e in system] == [["road_pose_recalibrated"]]
    EventBatch.model_validate(batch_body("cam-001", [{"kind": "event", "data": system[0]}]))


# ---------------------------------------------------------------- block 7: learns while moving only


def pitch_baseline(results, at):
    return min(results, key=lambda tr: abs(tr[0] - at))[1].drowsiness.pitch_baseline


@pytest.mark.parametrize("stop_s", [8.0, 30.0])
def test_a_look_at_the_screen_while_stopped_does_not_move_the_enrolled_pose(stop_s):
    """Audit A2 M2: enrolled road pitch 0, 12 deg down at the screen until the vehicle drives off.
    Before: the usual pitch read 12 from second 6 and, after an 8 s stop, for 19 s of driving."""
    speeds = ((0, 0), (stop_s - 0.05, 0), (stop_s, 60))
    results = drive(lambda t: (0.0, 12.0 if t < stop_s else 0.0), stop_s + 40, speeds, enrolled=(0.0, 0.0))
    for at in (4.0, 6.0, stop_s - 0.5, stop_s + 1, stop_s + 5, stop_s + 19, stop_s + 35):
        assert pitch_baseline(results, at) == pytest.approx(0.0, abs=0.1), at


def test_a_crawl_below_min_speed_does_not_teach_it_either():
    results = drive(lambda t: (0.0, 12.0 if t < 30 else 0.0), 60, ((0, 3), (29.95, 3), (30, 60)), enrolled=(0.0, 0.0))
    assert pitch_baseline(results, 29.0) == pytest.approx(0.0, abs=0.1)
    assert pitch_baseline(results, 40.0) == pytest.approx(0.0, abs=0.1)


def test_it_still_follows_the_camera_mount_while_driving():
    """The enrolled pose is where it starts, not a limit: 8 deg off for a minute of driving is learnt."""
    results = drive(lambda t: (0.0, 8.0), 60, enrolled=(0.0, 0.0))
    assert pitch_baseline(results, 3.0) == pytest.approx(0.0, abs=0.1)
    assert pitch_baseline(results, 55.0) == pytest.approx(8.0, abs=0.1)


def test_a_driver_who_is_not_enrolled_still_gets_a_first_pose_while_stopped():
    """Without any reference no eye state could be read at a standstill: the start-up samples are taken."""
    a = DrowsinessAnalyzer(DrowsinessConfig.from_dict(load_thresholds()["drowsiness"]))
    state = None
    for i in range(round(20 * FPS)):
        t = i / FPS
        state = a.update(features(i, t, pitch=12.0 if t < 6 else 0.0), moving=False)
    assert state.pitch_baseline == pytest.approx(12.0, abs=0.1)  # the first 5 s, nothing after
    assert state.eye_closed is False
    for i in range(round(20 * FPS), round(32 * FPS)):  # driving: the 5 s of start-up samples are outvoted
        state = a.update(features(i, i / FPS), moving=True)
    assert state.pitch_baseline == pytest.approx(0.0, abs=0.1)


def test_without_a_vehicle_context_it_learns_as_before():
    """Tools that feed block 7 alone (evaluation clips) do not say `moving`."""
    a = DrowsinessAnalyzer(DrowsinessConfig.from_dict(load_thresholds()["drowsiness"]))
    state = None
    for i in range(round(60 * FPS)):
        state = a.update(features(i, i / FPS, pitch=8.0))
    assert state.pitch_baseline == pytest.approx(8.0, abs=0.1)
