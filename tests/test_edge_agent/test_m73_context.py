"""M73: the context around the drowsiness score (audit 08/10, A3 H1 and H4).

- "Long drive" is judged on the driving since the last rest or driver change (block 10
  `drive_run_s`), the counter the HUD shows. Before, it read the source's total driving time, which
  never goes back: after two hours the factor stayed on through every rest and for every driver.
- Driving off after a stop of context.short_stop_forget_s or more (a red light) drops what the
  drowsiness side gathered during the stop, as after a rest. Before, eyes closed at a light became
  an alert on the first second of driving.
- Replays can run at another hour and with driving already done (eval.replay_clock_hour,
  eval.replay_drive_time_s).
Fake sequences, the real config/thresholds.yaml, no video.
"""

import pytest

from edge_agent.config import load_thresholds
from edge_agent.context.can_sim import CanSimulator, scenario_from_dict
from edge_agent.context.vehicle_context import ContextConfig, ContextTracker
from edge_agent.decision.pipeline import DecisionPipeline
from edge_agent.perception.features import FrameFeatures
from tools.seq_eval import replay_vehicle, set_threshold

FPS = 30.0
OPEN, SHUT = 0.30, 0.05
TH = load_thresholds()
LONG_S = TH["context"]["long_drive_s"]
REST_S = TH["context"]["rest_after_s"]
FORGET_S = TH["context"]["short_stop_forget_s"]
L1 = TH["risk"]["drowsy"]["l1"]


def can(timeline, clock="12:00", driven=0.0):
    return CanSimulator(
        scenario_from_dict(
            {
                "start_clock": clock,
                "initial_drive_time_s": driven,
                "timeline": [{"t": t, "speed_kmh": v} for t, v in timeline],
            }
        )
    )


def stop_and_go(stop_at, stop_s, speed=50.0):
    return [(0, speed), (stop_at, speed), (stop_at + 0.1, 0), (stop_at + stop_s, 0), (stop_at + stop_s + 0.1, speed)]


def run(seconds, vehicle, ear=lambda t: OPEN, thresholds=None, on_frame=None):
    """The decision chain on a face looking at the road. Returns (pipeline, results)."""
    th = thresholds or load_thresholds()
    th["enrollment"] = {**th["enrollment"], "enabled": False}
    p = DecisionPipeline(th)
    results = []
    for i in range(round(seconds * FPS)):
        t = i / FPS
        if on_frame is not None:
            on_frame(p, t)
        f = FrameFeatures(i, t, True, 1.0, ear=ear(t), mar=0.05, pitch=0.0, yaw=0.0, roll=0.0)
        results.append(p.step(f, False, vehicle.sample(t)))
    return p, results


def at(results, t):
    return results[round(t * FPS)]


def alerts(results, since=0.0):
    return [
        (round(r.alert.new_alert.t, 1), r.alert.new_alert.level)
        for r in results
        if r.alert.new_alert and r.risk.t >= since
    ]


def closed_between(a, b):
    return lambda t: SHUT if a <= t < b else OPEN


# ---------------------------------------------------------------- block 10: long drive


def test_long_drive_ends_with_a_rest_and_starts_counting_again():
    tracker = ContextTracker(ContextConfig.from_dict(TH["context"]))
    stop = 200.0
    vehicle = can(stop_and_go(stop, REST_S + 60), driven=LONG_S - 100)
    ctx = {t: tracker.update(vehicle.sample(float(t))) for t in range(0, 600)}
    assert not ctx[50].long_drive and ctx[50].drive_run_s == pytest.approx(LONG_S - 50, abs=2)
    assert ctx[150].long_drive  # two hours without a rest
    assert ctx[int(stop + REST_S - 5)].long_drive  # a stop that is not a rest yet changes nothing
    assert not ctx[int(stop + REST_S + 5)].long_drive and ctx[int(stop + REST_S + 5)].drive_run_s == 0
    after = ctx[599]
    assert not after.long_drive and after.drive_run_s == pytest.approx(599 - stop - REST_S - 60, abs=3)
    assert after.drive_time_s > LONG_S  # the source's total goes on, the rule no longer reads it


def test_a_red_light_does_not_reset_the_long_drive():
    tracker = ContextTracker(ContextConfig.from_dict(TH["context"]))
    vehicle = can(stop_and_go(50.0, REST_S / 2), driven=LONG_S)
    ctx = [tracker.update(vehicle.sample(float(t))) for t in range(0, 200)]
    assert all(c.long_drive for c in ctx)
    assert any(c.long_stop for c in ctx) and not any(c.resting for c in ctx)


def test_a_new_driver_is_not_on_a_long_drive_and_the_hud_shows_the_same_counter():
    vehicle = can([(0, 60)], clock="02:00", driven=LONG_S + 100)

    def change(p, t):
        if round(t * FPS) == round(20 * FPS):
            p.change_driver()

    p, results = run(40, vehicle, on_frame=change)
    assert at(results, 19).context.long_drive and at(results, 19).context.night
    assert p.trip_log.hud_view(15)["drive_run_s"] == pytest.approx(20, abs=1)
    for t in (20, 30, 39):
        r = at(results, t)
        assert not r.context.long_drive and r.context.drive_run_s == pytest.approx(t - 20, abs=1)


def test_the_long_drive_factor_is_off_after_a_rest():
    """The same 1.1 s closure by night: scored with both factors before the rest, with one after it."""
    stop = 60.0
    go = stop + REST_S + 30
    vehicle = can(stop_and_go(stop, REST_S + 30), clock="02:00", driven=LONG_S)
    _, results = run(go + 60, vehicle, ear=lambda t: SHUT if 30 <= t < 31.1 or go + 30 <= t < go + 31.1 else OPEN)
    risk = TH["risk"]["drowsy"]
    one = risk["weight_microsleep"] * risk["night_factor"]
    assert at(results, 33).risk.drowsy_score == pytest.approx(one * risk["long_drive_factor"], abs=0.5)
    assert at(results, go + 33).risk.drowsy_score == pytest.approx(one, abs=0.5)


# ---------------------------------------------------------------- pipeline: a stop that is not a rest


def test_eyes_closed_at_a_red_light_are_not_an_alert_when_driving_off():
    stop, stop_s = 60.0, 60.0
    go = stop + stop_s
    _, results = run(go + 60, can(stop_and_go(stop, stop_s)), ear=closed_between(stop + 20, stop + 45))
    assert at(results, go - 1).risk.drowsy_score >= L1 and at(results, go - 1).risk.level == 0  # scored, capped (M30)
    assert alerts(results) == []
    assert at(results, go + 2).risk.drowsy_score == 0
    assert at(results, go + 2).trip.last_microsleep_t is None


def test_before_m73_the_same_stop_raised_an_alert_as_the_vehicle_rolled():
    th = load_thresholds()
    set_threshold(th, f"context.short_stop_forget_s={REST_S}")  # only rests are forgotten
    stop, stop_s = 60.0, 60.0
    go = stop + stop_s
    _, results = run(go + 60, can(stop_and_go(stop, stop_s)), ear=closed_between(stop + 20, stop + 45), thresholds=th)
    assert [level for _, level in alerts(results, since=go)][:1] == [1]


def test_a_stop_shorter_than_the_limit_keeps_its_evidence():
    stop, stop_s = 60.0, FORGET_S - 2
    go = stop + stop_s
    _, results = run(go + 30, can(stop_and_go(stop, stop_s)), ear=closed_between(stop + 2, stop + 5))
    after = at(results, go + 2)
    assert after.trip.last_microsleep_t is not None
    assert after.risk.drowsy_score >= TH["risk"]["drowsy"]["weight_microsleep"]


def test_what_was_gathered_before_the_stop_stays():
    stop, stop_s = 60.0, 30.0
    go = stop + stop_s
    _, results = run(go + 30, can(stop_and_go(stop, stop_s)), ear=closed_between(30, 31.2))
    assert at(results, go + 2).trip.last_microsleep_t == pytest.approx(31.0, abs=0.3)


def test_eyes_still_closed_when_the_vehicle_rolls_are_a_microsleep():
    stop, stop_s = 60.0, 30.0
    go = stop + stop_s
    _, results = run(go + 20, can(stop_and_go(stop, stop_s)), ear=closed_between(stop + 10, go + 10))
    l3 = [t for t, level in alerts(results, since=go) if level == 3]
    assert l3 and l3[0] - go <= TH["risk"]["microsleep_l3_s"] + 1.0


def test_only_a_rest_restarts_the_repeated_l1_count():
    calls = []

    def spy(p, t):
        if t == 0:
            p.alerts.forget_repeats = lambda: calls.append(t)

    run(120, can(stop_and_go(30.0, 30.0)), on_frame=spy)
    assert calls == []
    run(REST_S + 100, can(stop_and_go(30.0, REST_S + 30)), on_frame=spy)
    assert len(calls) == 1


# ---------------------------------------------------------------- eval tools: hour and driving time


def test_replays_run_at_noon_with_no_driving_unless_told_otherwise():
    s = replay_vehicle(load_thresholds()).sample(0.0)
    assert s.clock_hour == pytest.approx(12.0) and s.drive_time_s == 0 and s.speed_kmh == 60
    th = load_thresholds()
    set_threshold(th, "eval.replay_clock_hour=2")
    set_threshold(th, f"eval.replay_drive_time_s={LONG_S}")
    ctx = ContextTracker(ContextConfig.from_dict(th["context"])).update(replay_vehicle(th).sample(0.0))
    assert ctx.night and ctx.long_drive
