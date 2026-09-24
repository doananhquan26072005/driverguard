import pytest

from edge_agent.analysis.distraction import DistractionAnalyzer, DistractionConfig
from edge_agent.perception.features import FrameFeatures

FPS = 30
DT = 1.0 / FPS


def feats(t, yaw=0.0, pitch=0.0, face=True):
    if not face:
        return FrameFeatures(frame_id=int(t * FPS), timestamp=t, face_found=False, face_conf=0.0)
    return FrameFeatures(int(t * FPS), t, True, 1.0, ear=0.3, mar=0.0, pitch=pitch, yaw=yaw, roll=0.0)


def run(analyzer, t0, seconds, speed=50.0, phone=False, **pose):
    """Feed `seconds` of identical frames starting at t0. Returns (last state, next t)."""
    state = None
    n = round(seconds * FPS)
    for i in range(n):
        state = analyzer.update(feats(t0 + i * DT, **pose), phone, speed)
    return state, t0 + n * DT


def no_adapt(**kw):
    return DistractionAnalyzer(DistractionConfig(baseline_adapt=False, **kw))


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
    s = a.update(feats(t, yaw=0.0), False, 50.0)
    assert s.off_road


def test_branch_disabled_when_stopped():
    a = no_adapt(min_speed_kmh=5.0)
    _, t = run(a, 0.0, 3.0, yaw=45.0, phone=True)
    s, t = run(a, t, 1.0, speed=0.0, yaw=45.0, phone=True)
    assert not s.active
    assert s.off_road_duration == 0.0 and s.phone_ratio_2s == 0.0
    # Driving again: timers start from zero, not from before the stop.
    s, _ = run(a, t, 1.0, speed=30.0, yaw=45.0)
    assert s.active and s.off_road_duration == pytest.approx(1.0 - DT, abs=DT)


def test_unknown_speed_follows_config():
    s, _ = run(no_adapt(assume_moving_when_speed_unknown=True), 0.0, 1.0, speed=None, yaw=45.0)
    assert s.active and s.off_road
    s, _ = run(no_adapt(assume_moving_when_speed_unknown=False), 0.0, 1.0, speed=None, yaw=45.0)
    assert not s.active


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
    a = DistractionAnalyzer(DistractionConfig(baseline_tau_s=5.0, yaw_off_road_deg=30.0))
    s, t = run(a, 0.0, 30.0, yaw=20.0)
    assert s.baseline_yaw == pytest.approx(20.0, abs=0.5)
    s, t = run(a, t, 1.0, yaw=45.0)  # only 25 deg from the road: on road
    assert not s.off_road
    s, _ = run(a, t, 1.0, yaw=60.0)  # 40 deg away: off road
    assert s.off_road


def test_baseline_ignores_off_road_samples_and_is_clamped():
    a = DistractionAnalyzer(DistractionConfig(baseline_tau_s=1.0, baseline_max_deg=20.0))
    s, t = run(a, 0.0, 20.0, yaw=60.0)  # long distraction must not become the new "road"
    assert s.baseline_yaw == 0.0 and s.off_road
    b = DistractionAnalyzer(DistractionConfig(baseline_tau_s=1.0, baseline_max_deg=20.0, yaw_off_road_deg=40.0))
    s, _ = run(b, 0.0, 20.0, yaw=35.0)
    assert s.baseline_yaw == pytest.approx(20.0)


def test_config_from_yaml_dict():
    cfg = DistractionConfig.from_dict({"min_speed_kmh": 8, "baseline": {"adapt": False, "yaw_deg": 12.0}})
    assert cfg.min_speed_kmh == 8
    assert cfg.baseline_adapt is False and cfg.baseline_yaw_deg == 12.0
    assert DistractionAnalyzer(cfg).baseline_yaw == 12.0
