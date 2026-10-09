"""M92: drowsy_score is not reminded, and night with a long drive multiply the score by no more
than risk.drowsy.context_factor_cap (decisions of 09/10 on what M73 and M74 left open).

- alert.remind_skip_reasons: a reason in it is one alert per episode, exactly as with remind off;
  the other reasons keep the reminder of M74.
- risk.drowsy.context_factor_cap 1.2: the larger of the two factors, not 1.2 x 1.2.
Fake sequences, the real config/thresholds.yaml, no video.
"""

from dataclasses import replace

import pytest

from edge_agent.config import load_thresholds
from edge_agent.decision.alert_manager import AlertConfig, AlertManager
from edge_agent.decision.risk_engine import RiskAssessment, RiskConfig, RuleHit
from tests.test_edge_agent import test_m73_context as m73

TH = load_thresholds()
ALERTS = AlertConfig.from_dict(TH["alert"])
REMIND_ALL = replace(ALERTS, remind_skip_reasons=())  # M74
REMIND_OFF = replace(ALERTS, remind=False)  # before M74
DROWSY = TH["risk"]["drowsy"]
DT = 0.1


def play(cfg, script):
    """script: (level, reasons, seconds) one after the other, a frame every DT. Returns the alerts
    as (time, level, reasons)."""
    m, got, i = AlertManager(cfg), [], 0
    for level, reasons, seconds in script:
        for _ in range(round(seconds / DT)):
            t = i * DT
            hits = tuple(RuleHit(level, x, 1.0) for x in reasons)
            a = m.update(RiskAssessment(t, level, hits, 0.0, 0.0, (0, 0, 0, 0))).new_alert
            if a is not None:
                got.append((round(t, 1), a.level, a.reasons))
            i += 1
    return got


# ---------------------------------------------------------------- no reminder for drowsy_score


def test_the_yaml_skips_drowsy_score_only():
    assert ALERTS.remind is True
    assert ALERTS.remind_skip_reasons == ("drowsy_score",)
    assert AlertConfig().remind_skip_reasons == ALERTS.remind_skip_reasons  # default = YAML


@pytest.mark.parametrize("level", [1, 2])
def test_steady_drowsy_score_is_one_alert(level):
    script = [(level, ("drowsy_score",), 1800)]
    got = play(ALERTS, script)
    assert [a[1:] for a in got] == [(level, ("drowsy_score",))]
    assert got == play(REMIND_OFF, script)
    assert len(play(REMIND_ALL, script)) > 10  # M74: a sound every cooldown


def test_look_away_and_phone_are_still_reminded():
    for reason in ("off_road", "phone"):
        script = [(2, (reason,), 100)]
        assert play(ALERTS, script) == play(REMIND_ALL, script)
        assert len(play(ALERTS, script)) == 4


def test_drowsy_score_alone_follows_remind_off_on_any_sequence():
    # in and out of L1 / L2, inside and outside the cooldowns
    script = [(1, ("drowsy_score",), 20), (0, (), 50), (1, ("drowsy_score",), 200), (2, ("drowsy_score",), 90)] * 4
    assert play(ALERTS, script) == play(REMIND_OFF, script)


def test_drowsy_score_coming_back_again_and_again_still_escalates():
    # the audit's sequence (L1 for 20 s, nothing for 110 s): every episode is a new alert
    got = play(ALERTS, [(1, ("drowsy_score",), 20), (0, (), 110)] * 18)
    assert [a[1] for a in got] == [1, 1, 2] * 6


def test_reminder_of_another_reason_carries_drowsy_score_but_is_not_caused_by_it():
    script = [(2, ("drowsy_score", "phone"), 100)]
    got = play(ALERTS, script)
    assert len(got) == 4 and all(a[2][0] == "phone" for a in got[1:])  # the reminded reason first
    assert got == play(replace(ALERTS, remind_skip_reasons=("drowsy_score", "trend")), script)


def test_drowsy_l1_that_began_under_a_look_away_has_no_alert_of_its_own():
    # what M74 gave every reason (audit A3 M3) is given up for a reason that is not reminded
    script = [(2, ("off_road",), 6), (1, ("drowsy_score",), 600)]
    assert [a[1:] for a in play(ALERTS, script)] == [(2, ("off_road",))]
    assert play(ALERTS, script) == play(REMIND_OFF, script)
    assert len(play(REMIND_ALL, script)) > 3


def test_phone_that_began_under_a_microsleep_is_still_alerted_when_the_level_drops():
    script = [(3, ("microsleep",), 4), (2, ("phone", "drowsy_score"), 20)]
    got = play(ALERTS, script)
    assert [a[1:] for a in got] == [(3, ("microsleep",)), (2, ("phone", "drowsy_score"))]


def test_drowsy_score_falling_from_l2_to_l1_is_not_a_new_alert():
    script = [(2, ("drowsy_score",), 200), (1, ("drowsy_score",), 200)]
    assert [a[1] for a in play(ALERTS, script)] == [2]


@pytest.mark.parametrize("seed", range(5))
def test_drowsy_score_under_other_levels_follows_remind_off(seed):
    """Whatever comes above it and for how long, a reason that is not reminded sounds exactly when it
    did with remind off. The other reasons are left out of the comparison: they are reminded."""
    import random

    rng = random.Random(seed)
    script = []
    for _ in range(40):
        level, reasons = rng.choice([(0, ()), (1, ("drowsy_score",)), (2, ("drowsy_score",)), (3, ("microsleep",))])
        script.append((level, reasons, rng.choice([2, 10, 40, 150])))
    assert play(ALERTS, script) == play(REMIND_OFF, script)


def test_empty_skip_list_is_m74():
    script = [(1, ("drowsy_score",), 1800)]
    assert [a[1] for a in play(REMIND_ALL, script)][:6] == [1, 1, 2, 1, 1, 2]


# ---------------------------------------------------------------- context factor cap


def score(night, long_drive, cap=None):
    """The drowsy score two seconds after a 1.1 s closure (the microsleep weight) in a context."""
    th = load_thresholds()
    if cap is not None:
        th["risk"]["drowsy"]["context_factor_cap"] = cap
    vehicle = m73.can([(0, 60)], clock="02:00" if night else "12:00", driven=m73.LONG_S if long_drive else 0.0)
    r = m73.at(m73.run(40, vehicle, ear=m73.closed_between(30, 31.1), thresholds=th)[1], 33)
    assert (r.context.night, r.context.long_drive) == (night, long_drive)
    return r.risk.drowsy_score


def test_night_and_long_drive_together_are_the_larger_factor_not_the_product():
    cfg = RiskConfig.from_dict(TH["risk"])
    assert cfg.drowsy_context_factor_cap == DROWSY["context_factor_cap"] == 1.2
    assert RiskConfig().drowsy_context_factor_cap == cfg.drowsy_context_factor_cap  # default = YAML
    base = score(False, False)
    assert base == pytest.approx(DROWSY["weight_microsleep"])
    assert score(True, False) == pytest.approx(base * DROWSY["night_factor"])
    assert score(False, True) == pytest.approx(base * DROWSY["long_drive_factor"])
    assert score(True, True) == pytest.approx(base * 1.2)


def test_a_cap_of_the_product_is_the_behaviour_before_m92():
    assert score(True, True, cap=1.44) == pytest.approx(DROWSY["weight_microsleep"] * 1.44)
    assert score(True, False, cap=1.44) == pytest.approx(DROWSY["weight_microsleep"] * 1.2)


def test_one_closure_and_one_yawn_by_night_after_two_hours_is_no_alert():
    """The audit's sequence (top 10, finding 6): 1.1 s closed and a yawn at 60 km/h, 02:00, two hours
    driven. Stacked factors: 43.2, L1 for four minutes. Capped: 36, no alert."""

    def run(cap):
        th = load_thresholds()
        th["risk"]["drowsy"]["context_factor_cap"] = cap
        vehicle = m73.can([(0, 60)], clock="02:00", driven=m73.LONG_S)
        th["enrollment"] = {**th["enrollment"], "enabled": False}
        p, results = m73.DecisionPipeline(th), []
        for i in range(round(120 * m73.FPS)):
            t = i / m73.FPS
            f = m73.FrameFeatures(
                i, t, True, 1.0,
                ear=m73.SHUT if 30 <= t < 31.1 else m73.OPEN,
                mar=0.9 if 50 <= t < 54 else 0.05,
                pitch=0.0, yaw=0.0, roll=0.0,
            )  # fmt: skip
            results.append(p.step(f, False, vehicle.sample(t)))
        return max(r.risk.drowsy_score for r in results), m73.alerts(results)

    top, alerts = run(DROWSY["context_factor_cap"])
    assert top == pytest.approx(36.0, abs=0.5) and alerts == []
    top, alerts = run(1.44)
    assert top == pytest.approx(43.2, abs=0.5) and [level for _, level in alerts] == [1]
