"""Blocks 9, 11, 12: risk engine rule table, trip memory trend, alert manager."""

from dataclasses import replace

import pytest

from edge_agent.analysis.distraction import DistractionState
from edge_agent.analysis.drowsiness import DrowsinessState
from edge_agent.context.vehicle_context import VehicleContext
from edge_agent.decision.alert_manager import AlertConfig, AlertManager
from edge_agent.decision.risk_engine import RiskAssessment, RiskConfig, RiskEngine, RuleHit
from edge_agent.decision.trip_memory import TripMemory, TripMemoryConfig, linear_slope

D0 = DrowsinessState(
    timestamp=100.0,
    eye_closed=False,
    closed_duration=0.0,
    microsleep=False,
    perclos_60s=0.0,
    perclos_coverage_s=60.0,
    perclos_ready=True,
    blink_rate=15.0,
    yawning=False,
    yawn_count_10min=0,
    nod_count_5min=0,
    ear_open_baseline=0.3,
    ear_closed_threshold=0.195,
)
X0 = DistractionState(100.0, True, False, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
C0 = VehicleContext(100.0, 50.0, True, False, False, False, False, 1000.0, 15.0)
ENGINE = RiskEngine()


def assess(d=D0, x=X0, c=C0, trip=None, engine=ENGINE):
    return engine.assess(d, x, c, trip)


# ---------------------------------------------------------------- risk engine (rule table)


def test_alert_driver_is_l0():
    r = assess()
    assert r.level == 0 and r.drowsy_score == 0 and r.distraction_score == 0 and r.reasons == ()


@pytest.mark.parametrize(("closed", "level"), [(1.4, 0), (1.5, 3), (3.0, 3)])
def test_microsleep_is_l3_at_1_5_s(closed, level):
    r = assess(d=replace(D0, closed_duration=closed))
    assert r.level == level
    if level:
        assert r.reasons == ("microsleep",)


def test_drowsy_score_formula():
    # PERCLOS 12.5 % -> term 0.5 (ramp 5..20 %), 2 yawns -> 2/3, 1 nod -> 1/2, no microsleep
    d = replace(D0, perclos_60s=0.125, yawn_count_10min=2, nod_count_5min=1)
    r = assess(d=d)
    assert r.drowsy_terms == pytest.approx((0.5, 0.0, 2 / 3, 0.5, 0.0, 0.0))
    assert r.drowsy_score == pytest.approx(40 * 0.5 + 15 * 2 / 3 + 20 * 0.5)  # 40 -> L1
    assert r.level == 1 and r.reasons == ("drowsy_score",)


def test_drowsy_score_l2_and_capped():
    d = replace(D0, perclos_60s=0.3, yawn_count_10min=5, nod_count_5min=3)
    r = assess(d=d)
    assert r.drowsy_score == pytest.approx(75)  # 40 + 15 + 20
    assert r.level == 2
    r = assess(d=d, c=replace(C0, night=True, long_drive=True))
    assert r.drowsy_score == 100.0  # 75 * 1.44 capped


def test_perclos_needs_coverage():
    r = assess(d=replace(D0, perclos_60s=0.3, perclos_coverage_s=10.0, perclos_ready=False))
    assert r.drowsy_terms[0] == 0.0 and r.level == 0


def test_recent_microsleep_adds_score_from_trip_memory():
    trip = TripMemory().update(0.0, 0.0, ("microsleep",))
    r = assess(trip=trip)
    assert r.drowsy_terms[1] == 1.0 and r.drowsy_score == 25
    later = replace(D0, timestamp=400.0)
    assert assess(d=later, trip=trip).drowsy_terms[1] == 0.0  # older than 5 min


def test_night_factor_needs_evidence():
    r = assess(c=replace(C0, night=True, long_drive=True))
    assert r.drowsy_score == 0 and r.level == 0  # multipliers never create an alert alone


@pytest.mark.parametrize(
    ("off_road", "high_speed", "level"),
    [(1.9, False, 0), (2.0, False, 2), (1.5, True, 2), (1.4, True, 0)],
)
def test_off_road_threshold_depends_on_speed(off_road, high_speed, level):
    r = assess(x=replace(X0, off_road=True, off_road_duration=off_road), c=replace(C0, high_speed=high_speed))
    assert r.level == level


def test_turn_signal_no_longer_switches_off_road_off():
    """Block 8 widens the yaw limit towards the signalled side; an off-road it still reports counts."""
    r = assess(x=replace(X0, off_road=True, off_road_duration=5.0), c=replace(C0, turning=True, turn_side="left"))
    assert r.level == 2 and "off_road" in r.reasons


@pytest.mark.parametrize(("ratio", "level"), [(0.59, 0), (0.6, 2)])
def test_phone_ratio_60_percent_is_l2(ratio, level):
    assert assess(x=replace(X0, phone_ratio_2s=ratio)).level == level


@pytest.mark.parametrize(("no_face", "unavailable"), [(2.9, False), (3.0, True)])
def test_no_face_3s_while_moving_is_unavailable_not_an_alert(no_face, unavailable):
    """PRD FR-6: without a face nothing can be judged, so no alert, the driver is just not monitored."""
    r = assess(x=replace(X0, no_face_duration=no_face))
    assert r.unavailable is unavailable
    assert r.level == 0 and r.reasons == ()


def test_unavailable_mutes_every_rule():
    # off road held from before the face was lost, a high drowsy score: nothing fires while unavailable
    x = replace(X0, no_face_duration=4.0, off_road=True, off_road_duration=6.0)
    d = replace(D0, perclos_60s=0.5, perclos_ready=True, yawn_count_10min=3, nod_count_5min=2)
    r = assess(d=d, x=x)
    assert r.unavailable and r.level == 0 and r.hits == () and r.distraction_score == 0.0


def test_not_unavailable_when_parked():
    parked = replace(C0, speed_kmh=0.0, moving=False, stationary=True)
    assert not assess(x=replace(X0, no_face_duration=10.0), c=parked).unavailable


def test_unavailable_in_a_crawl_below_min_speed():
    """M72: 1-5 km/h is not moving (distraction off) but not standing still either: a lost face is told."""
    crawl = replace(C0, speed_kmh=3.0, moving=False)
    r = assess(x=replace(X0, active=False, no_face_duration=10.0), c=crawl)
    assert r.unavailable and r.unavailable_reason == "no_face" and r.level == 0
    unknown = replace(C0, speed_kmh=None, moving=False)  # no speed, assume_moving off: as before
    assert not assess(x=replace(X0, no_face_duration=10.0), c=unknown).unavailable


def test_closure_carried_through_a_head_drop_stays_monitored():
    """Eyes closed, then the head fell out of view: that is a microsleep, the L3 alarm goes on."""
    d = replace(D0, closed_duration=4.0, microsleep=True, head_drop=True, eye_closed=None)
    r = assess(d=d, x=replace(X0, no_face_duration=3.5))
    assert not r.unavailable and r.level == 3 and r.reasons == ("microsleep",)


def test_distraction_silent_when_stopped():
    x = replace(X0, active=False, off_road_duration=0.0, phone_ratio_2s=0.0)
    r = assess(x=x, c=replace(C0, speed_kmh=0.0, moving=False))
    assert r.level == 0 and r.distraction_score == 0


STILL = {"speed_kmh": 0.0, "moving": False, "stationary": True}


@pytest.mark.parametrize(
    ("ctx", "level"),
    [
        ({}, 3),  # driving
        ({"speed_kmh": 3.0, "moving": False}, 3),  # crawling in a jam is not a stop
        ({**STILL, "stationary_s": 30.0}, 0),  # red light: no alert at 0 km/h (M30)
        ({**STILL, "stationary_s": 200.0, "resting": True}, 0),  # parked for a rest
    ],
)
def test_microsleep_level_while_standing_still(ctx, level):
    r = assess(d=replace(D0, closed_duration=2.0), c=replace(C0, **ctx))
    assert r.level == level
    assert r.reasons == (("microsleep",) if level else ())
    if not level:
        assert r.hits == ()


def test_stationary_cap_from_config():
    d = replace(D0, closed_duration=2.0)
    red_light = replace(C0, **STILL, stationary_s=30.0)
    assert assess(d=d, c=red_light, engine=RiskEngine(RiskConfig(drowsy_stationary_max_level=3))).level == 3
    assert assess(d=d, c=red_light, engine=RiskEngine(RiskConfig(drowsy_stationary_max_level=0))).hits == ()


def test_highest_rule_wins_and_all_hits_kept():
    d = replace(D0, closed_duration=2.0, perclos_60s=0.2)
    x = replace(X0, phone_ratio_2s=0.9)
    r = assess(d=d, x=x)
    assert r.level == 3
    assert {h.reason for h in r.hits} == {"microsleep", "drowsy_score", "phone"}
    assert r.reasons == ("microsleep",)


def test_blink_rate_is_a_note_by_default():
    trip = TripMemory().update(0.0, 0.0)
    trip = replace(trip, elapsed_s=120.0)
    r = assess(d=replace(D0, blink_rate=40.0), trip=trip)
    assert r.level == 0 and any(h.reason == "blink_rate" for h in r.hits)
    strict = RiskEngine(RiskConfig(blink_level=1))
    assert assess(d=replace(D0, blink_rate=40.0), trip=trip, engine=strict).level == 1


def test_rising_trend_is_early_warning():
    mem = TripMemory(TripMemoryConfig(bin_s=60))
    trip = None
    for minute in range(8):  # drowsy_score climbs 5 points per minute: 0, 5, ..., 35
        for s in range(0, 60, 5):
            trip = mem.update(minute * 60 + s, minute * 5.0)
    trip = mem.update(8 * 60, 35.0)
    assert trip.trend_15min == pytest.approx(5.0)
    r = assess(d=replace(D0, timestamp=480.0), trip=trip)
    assert r.level == 1 and r.reasons == ("trend",)


# ---------------------------------------------------------------- trip memory


def test_trip_memory_bins_and_window():
    mem = TripMemory(TripMemoryConfig(bin_s=60, trend_window_bins=15))
    state = None
    for minute in range(20):
        for s in range(0, 60, 10):
            state = mem.update(minute * 60 + s, float(minute))
    assert len(state.minute_scores) == 15
    assert state.minute_scores[0] == 4.0 and state.minute_scores[-1] == 18.0
    assert state.trend_15min == pytest.approx(1.0)


def test_linear_slope():
    assert linear_slope([]) is None and linear_slope([3.0]) is None
    assert linear_slope([1.0, 1.0, 1.0]) == pytest.approx(0.0)
    assert linear_slope([10.0, 8.0, 6.0]) == pytest.approx(-2.0)


def test_trip_memory_forgets_a_rest():
    mem = TripMemory(TripMemoryConfig(bin_s=60))
    for t in range(180):  # 3 minutes of driving, one microsleep
        mem.update(float(t), 10.0, ("microsleep",) if t == 100 else ())
    for t in range(180, 300):  # stopped, not a rest yet: still binned
        mem.update(float(t), 80.0, ("microsleep",) if t == 200 else ())
    for t in range(300, 600):  # the stop became a rest: not binned
        mem.update(float(t), 90.0, ("microsleep",) if t == 400 else (), observed=False)
    mem.forget_since(180.0)  # driving off: drop everything since the vehicle stopped
    state = mem.update(600.0, 5.0)
    assert state.minute_scores == (10.0, 10.0, 10.0)
    assert state.last_microsleep_t == 100.0


def test_trip_memory_counts_alerts():
    mem = TripMemory()
    mem.record_alert(2)
    mem.record_alert(2)
    assert mem.update(0.0, 0.0).alerts_by_level == (0, 0, 2, 0)


# ---------------------------------------------------------------- alert manager


def risk(t, level):
    hits = (RuleHit(level, "x", 1.0),) if level > 0 else ()
    return RiskAssessment(t, level, hits, 0.0, 0.0, (0, 0, 0, 0))


def run(manager, levels, t0=0.0, dt=0.1):
    """Feed a list of levels, one per dt. Returns list of AlertOutput."""
    return [manager.update(risk(t0 + i * dt, lv)) for i, lv in enumerate(levels)]


CFG = AlertConfig(rise_confirm_s={1: 1.0, 2: 0.5, 3: 0.0}, fall_hold_s=3.0, cooldown_s={1: 120, 2: 30, 3: 10})


def emitted(outputs):
    return [(round(o.t, 1), o.new_alert.level) for o in outputs if o.new_alert is not None]


def test_level_must_hold_before_alert():
    m = AlertManager(CFG)
    out = run(m, [2] * 4 + [0] * 20)  # 0.3 s of L2: below the 0.5 s confirmation
    assert emitted(out) == [] and m.active_level == 0
    out = run(AlertManager(CFG), [2] * 10)
    assert emitted(out) == [(0.5, 2)]


def test_l3_is_immediate():
    out = run(AlertManager(CFG), [0, 0, 3])
    assert emitted(out) == [(0.2, 3)]


def test_flicker_does_not_repeat_alerts():
    m = AlertManager(CFG)
    out = run(m, ([2] * 6 + [0] * 2) * 10)  # L2 with 0.2 s gaps for 8 s
    assert emitted(out) == [(0.5, 2)]
    assert all(o.active_level == 2 for o in out[5:])  # fall hold keeps it up


def test_level_drops_after_fall_hold():
    m = AlertManager(CFG)
    out = run(m, [2] * 10 + [0] * 40)
    drop = next(o.t for o in out[10:] if o.active_level == 0)
    assert drop == pytest.approx(1.0 + 3.0, abs=0.11)


def test_cooldown_suppresses_same_level():
    m = AlertManager(CFG)
    out = run(m, [2] * 10 + [0] * 40 + [2] * 10)  # second L2 episode after 5 s
    assert emitted(out) == [(0.5, 2)]
    assert out[-1].active_level == 2 and any(o.suppressed for o in out)
    out = run(m, [0] * 40 + [2] * 10, t0=40.0)  # after the 30 s cooldown
    assert emitted(out) == [(44.5, 2)]


def test_escalation_bypasses_lower_cooldown():
    m = AlertManager(CFG)
    out = run(m, [1] * 15 + [2] * 10 + [3])
    assert emitted(out) == [(1.0, 1), (2.0, 2), (2.5, 3)]


def test_alert_config_from_yaml_dict():
    cfg = AlertConfig.from_dict({"rise_confirm_s": {"2": 0.8}, "cooldown_s": {3: 5}})
    assert cfg.rise_confirm_s[2] == 0.8 and cfg.rise_confirm_s[1] == 1.0
    assert cfg.cooldown_s[3] == 5.0


def risk_reasons(t, level, reasons):
    hits = tuple(RuleHit(level, x, 1.0) for x in reasons)
    return RiskAssessment(t, level, hits, 0.0, 0.0, (0, 0, 0, 0))


def run_reasons(manager, steps, t0=0.0, dt=0.1):
    """steps: list of (level, reasons), one per dt."""
    return [manager.update(risk_reasons(t0 + i * dt, lv, rs)) for i, (lv, rs) in enumerate(steps)]


def emitted_reasons(outputs):
    return [(round(o.t, 1), o.new_alert.level, o.new_alert.reasons) for o in outputs if o.new_alert is not None]


def test_new_reason_at_same_level_is_a_new_alert():
    m = AlertManager(CFG)
    steps = [(2, ("off_road",))] * 20 + [(2, ("off_road", "phone"))] * 10
    out = run_reasons(m, steps)
    # phone joins at 2.0 s, holds the 0.5 s L2 confirmation, new reason listed first
    assert emitted_reasons(out) == [(0.5, 2, ("off_road",)), (2.5, 2, ("phone", "off_road"))]


def test_new_reason_must_hold_before_alert():
    m = AlertManager(CFG)
    steps = [(2, ("off_road",))] * 20 + [(2, ("off_road", "phone"))] * 3 + [(2, ("off_road",))] * 10
    assert emitted_reasons(run_reasons(m, steps)) == [(0.5, 2, ("off_road",))]


def test_reason_switch_at_same_level_is_alerted():
    m = AlertManager(CFG)
    steps = [(2, ("off_road",))] * 20 + [(2, ("phone",))] * 10
    assert emitted_reasons(run_reasons(m, steps)) == [(0.5, 2, ("off_road",)), (2.5, 2, ("phone",))]


def test_cooldown_is_per_reason():
    m = AlertManager(CFG)
    # off_road alert, back to L0, off_road again within 30 s: suppressed; phone: emitted.
    steps = [(2, ("off_road",))] * 10 + [(0, ())] * 40 + [(2, ("off_road",))] * 10
    out = run_reasons(m, steps)
    assert emitted_reasons(out) == [(0.5, 2, ("off_road",))] and any(o.suppressed for o in out)
    steps = [(0, ())] * 40 + [(2, ("phone",))] * 10
    assert emitted_reasons(run_reasons(m, steps, t0=6.0)) == [(10.5, 2, ("phone",))]


def test_dropping_a_level_is_not_a_new_alert():
    # phone was alerted at L2, a microsleep came on top, the level drops back to L2 phone: no second sound
    m = AlertManager(CFG)
    steps = [(2, ("phone",))] * 10 + [(3, ("microsleep",))] * 5 + [(2, ("phone",))] * 60
    assert emitted_reasons(run_reasons(m, steps)) == [(0.5, 2, ("phone",)), (1.0, 3, ("microsleep",))]
    assert m.active_level == 2


def test_flickering_reason_is_not_re_alerted():
    # phone drops out for one frame every 2 s for 60 s: one phone alert, then the one reminder of the
    # level when the 30 s cooldown has passed (M74), not an alert per flicker.
    m = AlertManager(CFG)
    steps = [(2, ("off_road",))] * 10
    for _ in range(30):
        steps += [(2, ("off_road", "phone"))] * 19 + [(2, ("off_road",))]
    assert emitted_reasons(run_reasons(m, steps)) == [
        (0.5, 2, ("off_road",)),
        (1.5, 2, ("phone", "off_road")),
        (32.0, 2, ("off_road", "phone")),
    ]
    out = run_reasons(AlertManager(replace(CFG, remind=False)), steps)
    assert emitted_reasons(out) == [(0.5, 2, ("off_road",)), (1.5, 2, ("phone", "off_road"))]


def test_reason_gone_longer_than_fall_hold_is_new_again():
    # phone gone 4 s (> fall_hold_s 3 s), back after its 30 s cooldown: a new alert.
    m = AlertManager(CFG)
    steps = [(2, ("off_road", "phone"))] * 10 + [(2, ("off_road",))] * 350 + [(2, ("off_road", "phone"))] * 10
    out = emitted_reasons(run_reasons(m, steps))
    assert out[0] == (0.5, 2, ("off_road", "phone"))
    assert out[-1][2][0] == "phone" and out[-1][0] == pytest.approx(36.5, abs=0.11)


# ---------------------------------------------------------------- repeated L1 -> L2 (M32)


def l1_episode(manager, t0, reasons=("drowsy_score",), hold_s=6.0):
    """L1 for 2 s from t0, then nothing for hold_s (longer than fall_hold_s)."""
    steps = [(1, reasons)] * 20 + [(0, ())] * round(hold_s * 10)
    return run_reasons(manager, steps, t0=t0)


def test_third_l1_of_the_same_reason_within_the_window_goes_out_as_l2():
    m = AlertManager(CFG)
    assert emitted_reasons(l1_episode(m, 0.0)) == [(1.0, 1, ("drowsy_score",))]
    assert emitted_reasons(l1_episode(m, 130.0)) == [(131.0, 1, ("drowsy_score",))]
    out = l1_episode(m, 260.0)
    assert emitted_reasons(out) == [(261.0, 2, ("drowsy_score", "repeated_l1"))]
    assert out[10].active_level == 2 and out[10].active_reasons == ("drowsy_score", "repeated_l1")


def test_escalated_alert_falls_back_to_l1_without_a_new_alert():
    m = AlertManager(CFG)
    l1_episode(m, 0.0)
    l1_episode(m, 130.0)
    out = run_reasons(m, [(1, ("drowsy_score",))] * 100, t0=260.0)  # the L1 cause goes on for 10 s
    assert emitted_reasons(out) == [(261.0, 2, ("drowsy_score", "repeated_l1"))]
    assert out[30].active_level == 2  # held for fall_hold_s
    assert out[-1].active_level == 1 and out[-1].active_reasons == ("drowsy_score",)


def test_l1_alerts_spread_wider_than_the_window_stay_l1():
    m = AlertManager(CFG)
    levels = [a[1] for t0 in (0.0, 400.0, 800.0, 1200.0) for a in emitted_reasons(l1_episode(m, t0))]
    assert levels == [1, 1, 1, 1]


def test_l1_alerts_of_different_reasons_do_not_add_up():
    m = AlertManager(CFG)
    out = [
        emitted_reasons(l1_episode(m, t0, (reason,)))
        for t0, reason in ((0.0, "drowsy_score"), (10.0, "trend"), (130.0, "drowsy_score"), (140.0, "trend"))
    ]
    assert [a[0][1] for a in out] == [1, 1, 1, 1]


def test_l1_alert_held_back_by_cooldown_does_not_count():
    m = AlertManager(CFG)
    for t0 in (0.0, 10.0, 20.0, 30.0):  # one alert, three held back
        l1_episode(m, t0)
    assert emitted_reasons(l1_episode(m, 130.0)) == [(131.0, 1, ("drowsy_score",))]


def test_repeat_escalation_can_be_switched_off():
    m = AlertManager(replace(CFG, l1_repeat_count=0))
    levels = [a[1] for t0 in (0.0, 130.0, 260.0, 390.0) for a in emitted_reasons(l1_episode(m, t0))]
    assert levels == [1, 1, 1, 1]


def test_a_rest_restarts_the_repeat_count():
    m = AlertManager(CFG)
    l1_episode(m, 0.0)
    l1_episode(m, 130.0)
    m.forget_repeats()
    assert emitted_reasons(l1_episode(m, 260.0)) == [(261.0, 1, ("drowsy_score",))]


def test_real_l2_of_the_same_reason_right_after_the_escalation_is_not_a_second_sound():
    m = AlertManager(CFG)
    l1_episode(m, 0.0)
    l1_episode(m, 130.0)
    out = run_reasons(m, [(1, ("drowsy_score",))] * 20 + [(2, ("drowsy_score",))] * 50, t0=260.0)
    assert emitted_reasons(out) == [(261.0, 2, ("drowsy_score", "repeated_l1"))]


def test_repeat_thresholds_come_from_the_yaml():
    from edge_agent.config import load_thresholds

    cfg = AlertConfig.from_dict(load_thresholds()["alert"])
    assert (cfg.l1_repeat_count, cfg.l1_repeat_window_s) == (3, 600.0)
