"""M74: block 12 no longer loses alerts to its own cooldown (audit 08/10, A3 H2, H3, M2, M3).

- Reminder: a reason still there at the active level once its cooldown has passed is alerted again.
  Before, an episode that began inside the cooldown never made a sound however long it lasted, and
  a level that stayed up was one alert for the whole stretch.
- Repeated L1: reminders count, and after the L2 "repeated_l1" the count starts again. Before,
  every L1 alert after the third went out as L2 until the vehicle rested.
- A reason that began under a higher level gets its own alert when that level drops.
- "Bạn còn ở đó không?" is not asked again and again when the face flickers.
Fake sequences, the real config/thresholds.yaml, no video.
"""

from dataclasses import replace

import pytest

from edge_agent.config import load_thresholds
from edge_agent.decision.alert_manager import AlertConfig, AlertManager
from edge_agent.decision.presence import PresenceCheck, PresenceConfig
from edge_agent.decision.risk_engine import RiskAssessment, RuleHit

TH = load_thresholds()
ALERTS = AlertConfig.from_dict(TH["alert"])
BEFORE = replace(ALERTS, remind=False)
L1_COOLDOWN, L2_COOLDOWN = ALERTS.cooldown_s[1], ALERTS.cooldown_s[2]
L1_CONFIRM, L2_CONFIRM = ALERTS.rise_confirm_s[1], ALERTS.rise_confirm_s[2]
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


def levels(alerts):
    return [a[1] for a in alerts]


# ---------------------------------------------------------------- reminder after the cooldown (H3)


def test_long_look_away_that_began_inside_the_cooldown_is_alerted_when_it_ends():
    script = [(2, ("off_road",), 3), (0, (), 5), (2, ("off_road",), 40)]
    got = play(ALERTS, script)
    assert [a[1:] for a in got] == [(2, ("off_road",))] * 2
    assert got[0][0] == pytest.approx(L2_CONFIRM, abs=0.11)
    assert got[1][0] == pytest.approx(got[0][0] + L2_COOLDOWN + L2_CONFIRM, abs=0.21)
    assert len(play(BEFORE, script)) == 1  # before M74: 40 s looking away without a sound


def test_level_that_stays_up_is_reminded_every_cooldown():
    got = play(ALERTS, [(2, ("phone",), 100)])
    assert levels(got) == [2, 2, 2, 2]
    gaps = [b[0] - a[0] for a, b in zip(got, got[1:], strict=False)]
    assert all(g == pytest.approx(L2_COOLDOWN + L2_CONFIRM, abs=0.21) for g in gaps)
    assert len(play(BEFORE, [(2, ("phone",), 100)])) == 1


def test_no_reminder_before_the_cooldown_has_passed():
    assert len(play(ALERTS, [(2, ("phone",), L2_COOLDOWN - 1)])) == 1
    assert len(play(ALERTS, [(1, ("drowsy_score",), L1_COOLDOWN - 1)])) == 1


def test_reminder_needs_the_reason_to_hold():
    # L2 for 29 s, gone; one stray L2 frame while the level is still held, after the cooldown: no sound
    script = [(2, ("phone",), 29), (0, (), 2), (2, ("phone",), DT), (0, (), 10)]
    assert len(play(ALERTS, script)) == 1


def test_one_reminder_covers_every_reason_of_the_frame():
    script = [(2, ("off_road",), 10), (2, ("off_road", "phone"), 50)]
    got = play(ALERTS, script)
    # off_road at 0.5 s, phone joins at 10.5 s; from then one alert per cooldown for both, not two
    assert [a[2] for a in got] == [("off_road",), ("phone", "off_road"), ("off_road", "phone")]
    assert got[2][0] == pytest.approx(got[1][0] + L2_COOLDOWN + L2_CONFIRM, abs=0.21)


def test_level_without_a_cooldown_is_not_reminded():
    assert ALERTS.cooldown_s[3] == 0
    assert play(ALERTS, [(3, ("microsleep",), 60)]) == [(0.0, 3, ("microsleep",))]


def test_l3_reminder_does_not_count_as_another_microsleep():
    cfg = replace(ALERTS, cooldown_s={**ALERTS.cooldown_s, 3: 10.0})
    got = play(cfg, [(3, ("microsleep",), 45)])
    assert len(got) == 5 and all(a[2] == ("microsleep",) for a in got)  # never repeated_l3


def test_frame_gap_restarts_the_confirmation_of_a_reminder():
    # the reminder is due and one frame into its confirmation when the loop stands still for 5 s
    m, got = AlertManager(ALERTS), []
    times = [i * DT for i in range(round((L2_COOLDOWN + L2_CONFIRM) / DT) + 2)]
    times += [times[-1] + 5.0 + i * DT for i in range(10)]
    for t in times:
        a = m.update(RiskAssessment(t, 2, (RuleHit(2, "phone", 1.0),), 0.0, 0.0, (0, 0, 0, 0))).new_alert
        if a is not None:
            got.append(round(t, 1))
    resumed = times[-10]
    assert len(got) == 2 and got[1] == pytest.approx(resumed + L2_CONFIRM, abs=0.11)


# ---------------------------------------------------------------- repeated L1 (H2)


def test_steady_l1_is_reminded_and_every_third_alert_is_l2():
    got = play(ALERTS, [(1, ("drowsy_score",), 1800)])
    assert levels(got)[:9] == [1, 1, 2, 1, 1, 2, 1, 1, 2]
    assert all(("repeated_l1" in a[2]) == (a[1] == 2) for a in got)
    assert got[1][0] - got[0][0] == pytest.approx(L1_COOLDOWN + L1_CONFIRM, abs=0.21)
    assert play(BEFORE, [(1, ("drowsy_score",), 1800)]) == [got[0]]  # before M74: one chime in 30 min


def test_score_crossing_the_line_again_and_again_is_not_l2_every_time():
    # the audit's sequence: L1 for 20 s, nothing for 110 s, for 40 min. Before M74: L1, L1, then 16 L2
    got = play(ALERTS, [(1, ("drowsy_score",), 20), (0, (), 110)] * 18)
    assert levels(got) == [1, 1, 2] * 6


def test_count_starts_again_only_for_the_reason_that_escalated():
    m = AlertManager(ALERTS)
    m._l1_emits = {"drowsy_score": [0.0, 130.0], "trend": [200.0]}
    assert m._repeated(260.0, ("drowsy_score",))
    assert m._l1_emits == {"drowsy_score": [], "trend": [200.0]}


def test_a_rest_still_restarts_the_count():
    m, got = AlertManager(ALERTS), []
    for i in range(round(400 / DT)):
        t = i * DT
        if abs(t - 200.0) < DT / 2:
            m.forget_repeats()  # the pipeline calls this when the driver rested
        a = m.update(RiskAssessment(t, 1, (RuleHit(1, "drowsy_score", 1.0),), 0.0, 0.0, (0, 0, 0, 0))).new_alert
        if a is not None:
            got.append(a.level)
    assert got == [1, 1, 1, 1]  # without the rest the third would have been L2


# ---------------------------------------------------------------- a reason under a higher level (M3)


def test_phone_that_began_under_a_microsleep_is_alerted_when_the_level_drops():
    script = [(3, ("microsleep",), 4), (2, ("phone",), 56)]
    got = play(ALERTS, script)
    assert got[0] == (0.0, 3, ("microsleep",))
    assert got[1][1:] == (2, ("phone",))
    assert got[1][0] == pytest.approx(4 + ALERTS.fall_hold_s + L2_CONFIRM, abs=0.21)
    assert play(BEFORE, script) == [got[0]]  # before M74: 56 s on the phone without a sound


def test_drowsy_l1_that_began_under_a_look_away_is_alerted_and_counted():
    script = [(2, ("off_road",), 6), (1, ("drowsy_score",), 600)]
    got = play(ALERTS, script)
    assert got[0][1:] == (2, ("off_road",))
    assert got[1][1:] == (1, ("drowsy_score",))
    assert got[1][0] == pytest.approx(6 + ALERTS.fall_hold_s + L1_CONFIRM, abs=0.21)
    assert levels(got)[1:4] == [1, 1, 2]


def test_reason_alerted_before_the_higher_level_is_not_alerted_again_on_the_way_down():
    script = [(2, ("phone",), 5), (3, ("microsleep",), 4), (2, ("phone",), 10)]
    assert levels(play(ALERTS, script)) == [2, 3]


# ---------------------------------------------------------------- presence question (M2)

PRESENCE = PresenceConfig.from_dict(TH["presence"])


def presence_events(cfg, seconds, face_at, tap=False):
    """Face lost all along but for the frames `face_at(i)`; the driver taps as soon as asked."""
    p, got, asking = PresenceCheck(cfg), [], False
    for i in range(round(seconds / DT)):
        s = p.update(i * DT, lost=not face_at(i), ack=tap and asking)
        asking = s.asking
        if s.event:
            got.append(s.event)
    return got


def test_face_flickering_every_12_s_is_asked_once():
    def glimpse(i):
        return i > 0 and i % 120 == 0  # one frame with a face every 12 s

    assert presence_events(PRESENCE, 120, glimpse) == ["asked", "no_answer"]
    assert presence_events(PRESENCE, 120, glimpse, tap=True) == ["asked", "answered"]
    before = replace(PRESENCE, back_s=0.0, reask_after_s=0.0)
    assert presence_events(before, 120, glimpse).count("asked") == 10


def test_face_back_long_enough_ends_the_loss():
    def back_for_2_s(i):
        return 200 <= i < 220

    # asked at 5 s, no answer at 15 s; back at 20 s for 2 s (> back_s); lost again: a new question
    assert presence_events(PRESENCE, 40, back_for_2_s) == ["asked", "no_answer", "asked", "no_answer"]


def test_no_new_question_soon_after_a_tap():
    def back_for_2_s_every_20_s(i):
        return i % 200 >= 180

    got = presence_events(PRESENCE, 100, back_for_2_s_every_20_s, tap=True)
    # asked at 5 s and tapped; the losses at 20 s and 40 s fall inside reask_after_s; the one at 60 s
    # is asked once the wait has passed
    assert got == ["asked", "answered", "asked", "answered"]
    always = replace(PRESENCE, reask_after_s=0.0)
    assert presence_events(always, 100, back_for_2_s_every_20_s, tap=True).count("asked") == 5


def test_face_seen_before_any_question_resets_at_once():
    def glimpse_every_4_s(i):
        return i % 40 == 0

    assert presence_events(PRESENCE, 60, glimpse_every_4_s) == []  # never lost for ask_after_s


def test_new_keys_come_from_the_yaml():
    assert ALERTS.remind is True
    assert (PRESENCE.back_s, PRESENCE.reask_after_s) == (1.0, 60.0)
