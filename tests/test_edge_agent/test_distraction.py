import pytest

from edge_agent.analysis.distraction import DistractionAnalyzer, DistractionConfig
from edge_agent.perception.features import FrameFeatures

FPS = 30
DT = 1.0 / FPS


def feats(t, yaw=0.0, pitch=0.0, face=True):
    if not face:
        return FrameFeatures(frame_id=int(t * FPS), timestamp=t, face_found=False, face_conf=0.0)
    return FrameFeatures(int(t * FPS), t, True, 1.0, ear=0.3, mar=0.0, pitch=pitch, yaw=yaw, roll=0.0)


def run(analyzer, t0, seconds, moving=True, phone=False, turn=None, **pose):
    """Feed `seconds` of identical frames starting at t0. Returns (last state, next t)."""
    state = None
    n = round(seconds * FPS)
    for i in range(n):
        state = analyzer.update(feats(t0 + i * DT, **pose), phone, moving, turn)
    return state, t0 + n * DT


def no_adapt(**kw):
    return DistractionAnalyzer(
        DistractionConfig(baseline_calibrate_s=0.0, baseline_recalibrate_s=0.0, baseline_adapt=False, **kw)
    )


def test_looking_forward_is_on_road():
    s, _ = run(no_adapt(), 0.0, 5.0, yaw=5.0, pitch=-3.0)
    assert s.active and not s.off_road
    assert s.off_road_duration == 0.0


def test_off_road_duration_accumulates():
    a = no_adapt()
    _, t = run(a, 0.0, 1.0)
    s, _ = run(a, t, 3.0, yaw=45.0)
    assert s.off_road
    assert s.off_road_duration == pytest.approx(3.0 - DT, abs=DT)


@pytest.mark.parametrize(("yaw", "pitch", "off"), [(-35, 0, True), (0, 25, True), (0, -30, True), (25, 15, False)])
def test_off_road_directions(yaw, pitch, off):
    s, _ = run(no_adapt(), 0.0, 1.0, yaw=yaw, pitch=pitch)
    assert s.off_road is off


def test_quick_glance_back_does_not_reset_timer():
    a = no_adapt(on_road_confirm_s=0.3)
    _, t = run(a, 0.0, 2.0, yaw=45.0)
    _, t = run(a, t, 0.1, yaw=0.0)  # 3 frames back on road: shorter than confirm time
    s, _ = run(a, t, 1.0, yaw=45.0)
    assert s.off_road_duration == pytest.approx(3.1 - DT, abs=DT)


def test_looking_back_long_enough_resets_timer():
    a = no_adapt(on_road_confirm_s=0.3)
    _, t = run(a, 0.0, 2.0, yaw=45.0)
    s, t = run(a, t, 0.5, yaw=0.0)
    assert not s.off_road and s.off_road_duration == 0.0
    s, _ = run(a, t, 1.0, yaw=45.0)
    assert s.off_road_duration == pytest.approx(1.0 - DT, abs=DT)


def test_single_noisy_frame_on_road_is_ignored():
    a = no_adapt()
    _, t = run(a, 0.0, 1.0, yaw=45.0)
    s = a.update(feats(t, yaw=0.0), False, True)
    assert s.off_road


def test_branch_disabled_when_stopped():
    a = no_adapt()
    _, t = run(a, 0.0, 3.0, yaw=45.0, phone=True)
    s, t = run(a, t, 1.0, moving=False, yaw=45.0, phone=True)
    assert not s.active
    assert s.off_road_duration == 0.0 and s.phone_ratio_2s == 0.0
    # Driving again: timers start from zero, not from before the stop.
    s, _ = run(a, t, 1.0, moving=True, yaw=45.0)
    assert s.active and s.off_road_duration == pytest.approx(1.0 - DT, abs=DT)


def test_face_lost_holds_previous_state():
    a = no_adapt()
    _, t = run(a, 0.0, 1.0, yaw=60.0)
    s, t = run(a, t, 1.0, face=False)  # turned so far the face is lost
    assert s.off_road and s.off_road_duration == pytest.approx(2.0 - DT, abs=DT)

    b = no_adapt()
    _, t = run(b, 0.0, 1.0, yaw=0.0)
    s, _ = run(b, t, 2.0, face=False)  # occlusion while looking forward
    assert not s.off_road


def test_phone_ratio_over_window():
    a = no_adapt(phone_window_s=2.0)
    _, t = run(a, 0.0, 1.0, phone=True)
    s, t = run(a, t, 1.0, phone=False)
    assert s.phone_ratio_2s == pytest.approx(0.5, abs=0.05)
    s, _ = run(a, t, 2.0, phone=False)  # phone samples slide out of the window
    assert s.phone_ratio_2s == 0.0


def test_phone_unknown_samples_are_not_counted():
    a = no_adapt()
    _, t = run(a, 0.0, 1.0, phone=True)
    s, _ = run(a, t, 0.5, phone=None)  # detector result stale
    assert s.phone_ratio_2s == 1.0


def test_baseline_learns_camera_offset():
    # Camera mounted to the side: looking at the road reads as yaw = 20 deg.
    a = DistractionAnalyzer(
        DistractionConfig(
            baseline_calibrate_s=0.0, baseline_recalibrate_s=0.0, baseline_tau_s=5.0, yaw_off_road_deg=30.0
        )
    )
    s, t = run(a, 0.0, 30.0, yaw=20.0)
    assert s.baseline_yaw == pytest.approx(20.0, abs=0.5)
    s, t = run(a, t, 1.0, yaw=45.0)  # only 25 deg from the road: on road
    assert not s.off_road
    s, _ = run(a, t, 1.0, yaw=60.0)  # 40 deg away: off road
    assert s.off_road


def test_baseline_ignores_off_road_samples_and_is_clamped():
    a = DistractionAnalyzer(
        DistractionConfig(
            baseline_calibrate_s=0.0, baseline_recalibrate_s=0.0, baseline_tau_s=1.0, baseline_max_deg=20.0
        )
    )
    s, t = run(a, 0.0, 20.0, yaw=60.0)  # long distraction must not become the new "road"
    assert s.baseline_yaw == 0.0 and s.off_road
    b = DistractionAnalyzer(
        DistractionConfig(
            baseline_calibrate_s=0.0,
            baseline_recalibrate_s=0.0,
            baseline_tau_s=1.0,
            baseline_max_deg=20.0,
            yaw_off_road_deg=40.0,
        )
    )
    s, _ = run(b, 0.0, 20.0, yaw=35.0)
    assert s.baseline_yaw == pytest.approx(20.0)


def test_config_from_yaml_dict():
    cfg = DistractionConfig.from_dict({"yaw_off_road_deg": 25, "baseline": {"adapt": False, "yaw_deg": 12.0}})
    assert cfg.yaw_off_road_deg == 25
    assert cfg.baseline_adapt is False and cfg.baseline_yaw_deg == 12.0
    assert DistractionAnalyzer(cfg).baseline_yaw == 12.0


def test_no_face_duration_while_moving():
    a = no_adapt()
    _, t = run(a, 0.0, 1.0)
    s, t = run(a, t, 3.0, face=False)
    assert s.no_face_duration == pytest.approx(3.0 - DT, abs=DT)
    s, t = run(a, t, DT)  # one frame with a face resets it
    assert s.no_face_duration == 0.0
    s, _ = run(a, t, 3.0, face=False, moving=False)  # stopped: branch off
    assert s.no_face_duration == 0.0


def calibrating(**kw):
    return DistractionAnalyzer(DistractionConfig(baseline_recalibrate_s=0.0, baseline_calibrate_s=5.0, **kw))


def test_camera_mounted_far_to_the_side_is_calibrated():
    # Camera 35 deg to the side: without calibration every frame is off road.
    s, _ = run(no_adapt(), 0.0, 10.0, yaw=35.0)
    assert s.off_road and s.off_road_duration > 9.0
    a = calibrating()
    s, t = run(a, 0.0, 10.0, yaw=35.0, pitch=8.0)
    assert not s.off_road and not s.calibrating
    assert (a.baseline_yaw, a.baseline_pitch) == pytest.approx((35.0, 8.0), abs=0.5)
    s, _ = run(a, t, 3.0, yaw=35.0 + 45.0)  # a real look away is still caught
    assert s.off_road and s.off_road_duration > 2.5


def test_no_off_road_while_calibrating_and_median_ignores_glances():
    a = calibrating(baseline_adapt=False)
    s, t = run(a, 0.0, 1.0, yaw=60.0)  # glance during calibration
    assert s.calibrating and not s.off_road
    s, t = run(a, t, 4.5, yaw=0.0)
    assert not s.calibrating and a.baseline_yaw == pytest.approx(0.0)


def test_calibration_waits_for_driving_and_is_clamped():
    a = calibrating(baseline_adapt=False)
    run(a, 0.0, 10.0, moving=False, yaw=70.0)  # parked: nothing learnt
    assert not a.calibrated
    run(a, 10.0, 6.0, yaw=70.0)
    assert a.calibrated and a.baseline_yaw == pytest.approx(45.0)


def test_adaptation_stays_around_calibrated_pose():
    a = calibrating(baseline_tau_s=1.0, baseline_max_deg=10.0)
    _, t = run(a, 0.0, 6.0, yaw=35.0)
    run(a, t, 30.0, yaw=35.0 + 25.0)  # 25 deg: on road (< 30), adapts but only by 10
    assert a.baseline_yaw == pytest.approx(45.0, abs=0.1)


def test_partial_face_holds_state_and_is_not_no_face():
    a = no_adapt()
    _, t = run(a, 0.0, 1.0, yaw=45.0)
    for i in range(round(2 * FPS)):  # face half out of frame, pose says "on road": not trusted
        ti = t + i * DT
        f = FrameFeatures(
            int(ti * FPS), ti, True, 0.5, face_reliable=False, ear=0.3, mar=0.0, pitch=0.0, yaw=0.0, roll=0.0
        )
        s = a.update(f, False, True)
    assert s.off_road and s.off_road_duration == pytest.approx(3.0 - DT, abs=DT)
    assert s.no_face_duration == 0.0


# ---------------------------------------------------------------- turn signal: wider on that side
# Unmirrored camera facing the driver (left_yaw_sign = +1): the driver's left is yaw > 0.


@pytest.mark.parametrize(
    ("turn", "yaw", "off"),
    [
        (None, 45.0, True),  # no signal: 30 deg either way
        (None, -45.0, True),
        ("left", 45.0, False),  # left signal: may look up to 60 deg left
        ("left", 59.0, False),
        ("left", 65.0, True),  # ... not further
        ("left", -45.0, True),  # looking right with the left signal on still counts
        ("right", -45.0, False),
        ("right", 45.0, True),
    ],
)
def test_turn_signal_widens_only_the_signalled_side(turn, yaw, off):
    s, _ = run(no_adapt(), 0.0, 3.0, turn=turn, yaw=yaw)
    assert s.off_road is off
    assert (s.off_road_duration > 2.5) is off


def test_turn_signal_does_not_widen_pitch():
    s, _ = run(no_adapt(), 0.0, 3.0, turn="left", yaw=20.0, pitch=30.0)  # left and down at the lap
    assert s.off_road


def test_left_yaw_sign_for_a_mirrored_camera():
    s, _ = run(no_adapt(left_yaw_sign=-1.0), 0.0, 1.0, turn="left", yaw=-45.0)
    assert not s.off_road
    s, _ = run(no_adapt(left_yaw_sign=-1.0), 0.0, 1.0, turn="left", yaw=45.0)
    assert s.off_road


def test_signal_off_back_to_normal_limit():
    a = no_adapt()
    s, t = run(a, 0.0, 2.0, turn="left", yaw=45.0)
    assert not s.off_road
    s, _ = run(a, t, 1.0, turn=None, yaw=45.0)  # still looking left after the grace period
    assert s.off_road and s.off_road_duration == pytest.approx(1.0 - DT, abs=0.05)


def test_baseline_does_not_learn_from_the_widened_band():
    a = DistractionAnalyzer(DistractionConfig(baseline_calibrate_s=0.0, baseline_recalibrate_s=0.0, baseline_tau_s=1.0))
    s, _ = run(a, 0.0, 5.0, turn="left", yaw=45.0)
    assert not s.off_road and s.baseline_yaw == 0.0


@pytest.mark.parametrize(("turn", "yaw", "alert"), [("left", 45.0, False), ("left", -45.0, True), (None, 45.0, True)])
def test_pipeline_turn_signal_from_the_vehicle(turn, yaw, alert):
    """Block 10's turn signal reaches block 8: 5 s looking 45 deg aside at 50 km/h, after calibration."""
    from edge_agent.config import load_thresholds
    from edge_agent.context.can_sim import VehicleSignals
    from edge_agent.decision.pipeline import DecisionPipeline

    p = DecisionPipeline(load_thresholds())
    reasons = set()
    for i in range(int(15 * FPS)):
        t = i * DT
        look = yaw if t >= 8.0 else 0.0
        f = FrameFeatures(i, t, True, 1.0, ear=0.3, mar=0.05, pitch=0.0, yaw=look, roll=0.0)
        r = p.step(f, False, VehicleSignals(t, 50.0, turn if t >= 7.0 else None, 0.0, 12.0))
        reasons.update(r.risk.reasons)
    assert ("off_road" in reasons) is alert


def test_looking_down_from_block_7_counts_as_off_road_and_never_moves_the_baseline():
    d = DistractionAnalyzer(DistractionConfig(baseline_recalibrate_s=0.0, baseline_calibrate_s=0.0))
    for i in range(30):  # 1 s on the road
        d.update(FrameFeatures(i, i / 30, True, 1.0, yaw=0.0, pitch=0.0), False, moving=True)
    s = None
    for i in range(30, 120):  # 3 s head bowed 12 deg (within the pitch limit), lids lowered
        s = d.update(FrameFeatures(i, i / 30, True, 1.0, yaw=0.0, pitch=12.0), False, moving=True, gaze_down=True)
    assert s.off_road and s.off_road_duration == pytest.approx(3.0, abs=0.1)
    assert d.baseline_pitch == 0.0
    s = d.update(FrameFeatures(120, 4.0, True, 1.0, yaw=0.0, pitch=12.0), False, moving=True)
    assert s.off_road  # back needs on_road_confirm_s
