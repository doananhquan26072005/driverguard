import pytest

from edge_agent.config import PROJECT_ROOT
from edge_agent.context.can_sim import CanSimulator, VehicleSignals, load_scenario, parse_clock, scenario_from_dict
from edge_agent.context.vehicle_context import ContextConfig, ContextTracker, in_hours

SCENARIO = {
    "name": "test",
    "start_clock": "23:30",
    "initial_drive_time_s": 100,
    "timeline": [
        {"t": 0, "speed_kmh": 0},
        {"t": 10, "speed_kmh": 100},
        {"t": 20, "speed_kmh": 100, "turn_signal": "left"},
        {"t": 25, "speed_kmh": 100, "turn_signal": "off"},
        {"t": 30, "speed_kmh": 0},
    ],
}


def test_speed_is_interpolated_and_held():
    can = CanSimulator(scenario_from_dict(SCENARIO))
    assert can.speed_at(-1) == 0
    assert can.speed_at(5) == pytest.approx(50)
    assert can.speed_at(15) == 100
    assert can.speed_at(27.5) == pytest.approx(50)
    assert can.speed_at(99) == 0


def test_turn_signal_holds_until_changed():
    can = CanSimulator(scenario_from_dict(SCENARIO))
    assert can.turn_signal_at(19) is None
    assert can.turn_signal_at(20) == "left"
    assert can.turn_signal_at(24.9) == "left"
    assert can.turn_signal_at(25) is None


def test_loop_wraps_time():
    can = CanSimulator(scenario_from_dict({**SCENARIO, "loop": True}))
    assert can.speed_at(35) == pytest.approx(50)  # 35 % 30 = 5


def test_drive_time_only_counts_moving_time():
    can = CanSimulator(scenario_from_dict(SCENARIO), moving_kmh=5)
    s = None
    for i in range(0, 401):
        s = can.sample(i * 0.1)
    # moving from ~0.5 s to ~29.5 s -> ~29 s + 100 s initial
    assert s.drive_time_s == pytest.approx(129, abs=0.5)


def test_clock_wraps_midnight():
    can = CanSimulator(scenario_from_dict(SCENARIO))
    assert can.sample(0).clock_hour == pytest.approx(23.5)
    assert can.sample(3600).clock_hour == pytest.approx(0.5)
    assert parse_clock("02:30") == 9000


def test_empty_scenario_rejected():
    with pytest.raises(ValueError):
        scenario_from_dict({"timeline": []})


@pytest.mark.parametrize("name", ["city_day", "highway_night", "parked"])
def test_bundled_scenarios_load(name):
    sc = load_scenario(PROJECT_ROOT / "config" / "scenarios" / f"{name}.yaml")
    assert sc.name == name and sc.keyframes


@pytest.mark.parametrize(
    ("hour", "windows", "expected"),
    [
        (2.0, ((0, 5),), True),
        (5.0, ((0, 5),), False),
        (23.0, ((22, 5),), True),
        (4.0, ((22, 5),), True),
        (12, ((22, 5),), False),
    ],
)
def test_in_hours(hour, windows, expected):
    assert in_hours(hour, windows) is expected


def test_context_flags_and_turn_grace():
    tracker = ContextTracker(ContextConfig(high_speed_kmh=80, long_drive_s=120, turn_signal_grace_s=2.0))
    can = CanSimulator(scenario_from_dict(SCENARIO))
    ctx = {round(t, 1): tracker.update(can.sample(t)) for t in [i * 0.5 for i in range(0, 61)]}
    assert not ctx[0.0].moving and ctx[15.0].moving and ctx[15.0].high_speed
    assert not ctx[0.0].night  # 23:30 is outside the default 00-05 window
    assert ContextTracker(ContextConfig(night_hours=((22, 5),))).update(can.sample(30.5)).night
    assert ctx[22.0].turning
    assert ctx[26.5].turning  # 1.5 s after the blinker stopped: still in grace
    assert not ctx[27.5].turning
    assert ctx[29.0].long_drive  # 100 s initial + ~20 s moving >= 120 s


def signals(speed_kmh, t=1.0):
    from edge_agent.context.can_sim import VehicleSignals

    return VehicleSignals(t=t, speed_kmh=speed_kmh, turn_signal=None, drive_time_s=0.0, clock_hour=12.0)


def test_unknown_speed_does_not_crash_and_follows_config():
    ctx = ContextTracker(ContextConfig()).update(signals(None))
    assert ctx.moving and not ctx.high_speed and ctx.speed_kmh is None
    ctx = ContextTracker(ContextConfig(assume_moving_when_speed_unknown=False)).update(signals(None))
    assert not ctx.moving


def test_pipeline_runs_without_speed_signal():
    """Real CAN may drop the speed: the whole chain must keep working, distraction still on."""
    from edge_agent.decision.pipeline import DecisionPipeline
    from edge_agent.perception.features import FrameFeatures

    pipe = DecisionPipeline()
    r = None
    for i in range(90):
        t = i / 30
        f = FrameFeatures(i, t, True, 1.0, ear=0.3, mar=0.0, pitch=0.0, yaw=0.0, roll=0.0)
        r = pipe.step(f, False, signals(None, t))
    assert r.context.moving and r.distraction.active


def test_one_min_speed_for_risk_engine_and_distraction():
    """context.min_speed_kmh alone decides 'moving' for block 8 and block 9."""
    from edge_agent.decision.pipeline import DecisionPipeline
    from edge_agent.perception.features import FrameFeatures

    pipe = DecisionPipeline({"context": {"min_speed_kmh": 20}})
    f = FrameFeatures(0, 0.0, True, 1.0, ear=0.3, mar=0.0, pitch=0.0, yaw=0.0, roll=0.0)
    r = pipe.step(f, False, signals(10.0))
    assert not r.context.moving and not r.distraction.active


def at_speed(t, speed):
    return VehicleSignals(t=t, speed_kmh=speed, turn_signal=None, drive_time_s=0.0, clock_hour=12.0)


def test_standing_still_becomes_a_rest():
    tracker = ContextTracker(ContextConfig(rest_after_s=120))
    assert not tracker.update(at_speed(0.0, 50.0)).stationary
    c = tracker.update(at_speed(10.0, 0.0))
    assert c.stationary and c.stationary_s == 0.0 and not c.resting
    assert not tracker.update(at_speed(129.9, 0.0)).resting  # a long red light
    c = tracker.update(at_speed(130.0, 0.0))
    assert c.resting and c.stationary_s == pytest.approx(120.0)
    c = tracker.update(at_speed(131.0, 20.0))  # drives off
    assert not c.stationary and c.stationary_s == 0.0 and not c.resting


def test_crawling_in_a_jam_or_unknown_speed_is_never_a_rest():
    tracker = ContextTracker()
    for t in range(600):  # 10 min at 3 km/h: not moving (distraction off), but not standing still
        c = tracker.update(at_speed(float(t), 3.0))
    assert not c.moving and not c.stationary and not c.resting
    c = ContextTracker().update(at_speed(0.0, None))
    assert c.moving and not c.stationary
