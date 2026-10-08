"""M75: blocks 7-12 when frames come slower than 15 FPS, or unevenly. Measured only, nothing changed.

Every other timing test feeds frames 1 / 30 s apart. The target device is estimated at 11-14 FPS, and a
loop that shares its thread does not deliver frames evenly. Here the same thing happens in front of the
camera (a closure, a look away, a yawn, a nod, a phone) and is sampled by different loops: even at
30 / 15 / 12 / 10 FPS, uneven at 12 / 10 FPS (log-normal waits, eval.fps_study_jitter_cv), and a
stuttering one (three frames 1 / 30 s apart, then 0.3 s without one: 10 FPS on average). Each case is
tried at several moments against the frame grid, so a result does not hang on where the first frame fell.

What holds at every loop (asserted): a duration is never measured longer than it was, so no alert is
invented; what is clearly over a limit is alerted, late by at most two frame gaps; PERCLOS and the phone
ratio follow time, not the number of frames.
What a slow loop costs: a duration is measured short by up to two frame gaps, so an event that passes
its limit by less than that can be missed. Those cases state what is wanted and are marked xfail (strict)
at the loops where it was measured not to hold; a fix turns them red, and the mark comes off.

Fake sequences, the real config/thresholds.yaml, no video.
"""

import math

import numpy as np
import pytest

from edge_agent.config import load_thresholds
from edge_agent.context.can_sim import CanSimulator, scenario_from_dict
from edge_agent.decision.pipeline import DecisionPipeline
from edge_agent.perception.features import FrameFeatures

TH = load_thresholds()
OPEN, SHUT = 0.30, 0.05
WARM_S = 30.0  # eyes open, looking ahead: the baselines settle
PHASES = (0.0, 0.013, 0.031, 0.052, 0.077)  # the event starts this long after WARM_S: no lock to a frame grid
JITTER_CV = float(TH["eval"]["fps_study_jitter_cv"])
L3_S = float(TH["risk"]["microsleep_l3_s"])
OFF_ROAD_S = float(TH["risk"]["distraction"]["off_road_s"])
RISE_S = {int(k): float(v) for k, v in TH["alert"]["rise_confirm_s"].items()}


def even(fps):
    return lambda end: [k / fps for k in range(int(end * fps))]


def uneven(fps, seed):
    """Waits around 1 / fps, log-normal, as tools/seq_eval.py resample_trace draws them."""

    def times(end):
        sigma2 = math.log(1.0 + JITTER_CV**2)
        waits = np.random.default_rng(seed).lognormal(
            -math.log(fps) - sigma2 / 2.0, math.sqrt(sigma2), int(end * fps * 2)
        )
        t = np.concatenate(([0.0], np.cumsum(waits)))
        return [float(x) for x in t[t < end]]

    return times


def stutter(end, short=1 / 30, long=0.3, every=4):
    """Three frames close together, then a long wait: a loop that shares its thread with other work."""
    out, t = [], 0.0
    while t < end:
        out.append(t)
        t += long if len(out) % every == 0 else short
    return out


LOOPS = {
    "30 FPS": even(30),
    "15 FPS": even(15),
    "12 FPS": even(12),
    "10 FPS": even(10),
    "12 FPS uneven": uneven(12, 0),
    "10 FPS uneven": uneven(10, 0),
    "10 FPS uneven, other waits": uneven(10, 1),
    "stutter": stutter,
}
SLOW = [name for name in LOOPS if name != "30 FPS"]


def largest_gap(loop, around=(WARM_S - 1.0, WARM_S + 10.0)):
    t = [x for x in LOOPS[loop](around[1]) if x >= around[0]]
    return max(b - a for a, b in zip(t, t[1:], strict=False))


def drive(loop, signal, end, phone=None):
    """The decision chain at 60 km/h by day on signal(t) sampled by the loop. Returns (alerts, results)."""
    th = load_thresholds()
    th["enrollment"] = {**th["enrollment"], "enabled": False}
    pipeline = DecisionPipeline(th)
    timeline = [{"t": 0, "speed_kmh": 60}, {"t": 100000, "speed_kmh": 60}]
    can = CanSimulator(
        scenario_from_dict({"name": "t", "start_clock": "15:00", "initial_drive_time_s": 600, "timeline": timeline})
    )
    alerts, results = [], []
    for i, t in enumerate(LOOPS[loop](end)):
        s = {"ear": OPEN, "mar": 0.05, "yaw": 0.0, "pitch": 0.0, **signal(t)}
        f = FrameFeatures(i, t, True, 1.0, ear=s["ear"], mar=s["mar"], pitch=s["pitch"], yaw=s["yaw"], roll=0.0)
        r = pipeline.step(f, bool(phone(t)) if phone else False, can.sample(t))
        results.append(r)
        if r.alert.new_alert is not None:
            alerts.append((r.alert.new_alert.t, r.alert.new_alert.level, r.alert.new_alert.reasons))
    return alerts, results


def during(start, seconds, **signals):
    return lambda t: signals if start <= t < start + seconds else {}


def events(results, kind):
    return sum(e == kind for r in results for e in r.drowsiness.events)


def late_by(alerts, level, reason, due):
    """Seconds after `due` of the one alert of this level and reason; fails when there is none or more."""
    mine = [t for t, lv, reasons in alerts if lv == level and reason in reasons]
    assert len(mine) == 1, alerts
    return mine[0] - due


def known_gap(loop, *loops, reason):
    """The case is expected to hold at every loop; at `loops` it is known not to (measured, M75)."""
    return pytest.param(loop, marks=pytest.mark.xfail(strict=True, reason=reason)) if loop in loops else loop


# ---------------------------------------------------------------- nothing is invented


@pytest.mark.parametrize("loop", LOOPS)
def test_a_closure_under_the_limit_is_never_a_microsleep_alert(loop):
    """Block 7 times a closure from the first frame that shows it: never longer than it was."""
    shut_s = L3_S - 0.05
    for phase in PHASES:
        alerts, results = drive(loop, during(WARM_S + phase, shut_s, ear=SHUT), WARM_S + 5)
        assert alerts == []
        assert max(r.drowsiness.closed_duration for r in results) <= shut_s


@pytest.mark.parametrize("loop", LOOPS)
def test_a_look_away_under_the_limit_is_never_an_alert(loop):
    for phase in PHASES:
        alerts, _ = drive(loop, during(WARM_S + phase, OFF_ROAD_S - 0.05, yaw=45.0), WARM_S + 6)
        assert alerts == []


@pytest.mark.parametrize("loop", LOOPS)
def test_ordinary_blinks_stay_quiet_and_perclos_follows_time_not_frames(loop):
    """A 0.25 s blink every 3.7 s for 4 minutes: 6.8 % of the time closed, whatever the loop saw of it.
    The stuttering loop takes three frames in 0.1 s and none in the next 0.3 s; counted by frames its
    PERCLOS would be another number."""
    shut_s, every = 0.25, 3.7
    alerts, results = drive(loop, lambda t: {"ear": SHUT} if t > 1 and math.fmod(t, every) < shut_s else {}, 240)
    assert alerts == []
    assert events(results, "microsleep") == 0
    assert results[-1].drowsiness.perclos_60s == pytest.approx(shut_s / every, abs=0.02)
    assert max(r.risk.drowsy_score for r in results) < float(TH["risk"]["drowsy"]["l1"]) / 2


@pytest.mark.parametrize("loop", LOOPS)
def test_a_short_mouth_opening_is_never_a_yawn_and_a_long_one_is_one(loop):
    min_s = float(TH["drowsiness"]["yawn"]["min_s"])
    for phase in PHASES:
        _, short = drive(loop, during(WARM_S + phase, min_s - 0.2, mar=0.8), WARM_S + 5)
        _, long = drive(loop, during(WARM_S + phase, 2 * min_s, mar=0.8), WARM_S + 5)
        assert (events(short, "yawn"), events(long, "yawn")) == (0, 1)


# ---------------------------------------------------------------- what is clearly there is alerted, a little late


@pytest.mark.parametrize("loop", LOOPS)
def test_a_clear_microsleep_is_one_l3_at_most_two_frame_gaps_late(loop):
    gap = largest_gap(loop)
    for phase in PHASES:
        alerts, _ = drive(loop, during(WARM_S + phase, L3_S + 1.5, ear=SHUT), WARM_S + 6)
        late = late_by(alerts, 3, "microsleep", WARM_S + phase + L3_S)
        assert 0.0 <= late <= 2 * gap + 0.01


@pytest.mark.parametrize("loop", LOOPS)
def test_a_clear_look_away_is_one_l2_at_most_two_frame_gaps_late(loop):
    gap = largest_gap(loop)
    for phase in PHASES:
        alerts, _ = drive(loop, during(WARM_S + phase, OFF_ROAD_S + 2.0, yaw=45.0), WARM_S + 8)
        late = late_by(alerts, 2, "off_road", WARM_S + phase + OFF_ROAD_S + RISE_S[2])
        assert 0.0 <= late <= 2 * gap + 0.01


@pytest.mark.parametrize("loop", LOOPS)
def test_a_phone_held_up_is_one_l2_and_its_ratio_is_counted_by_frames(loop):
    """phone_ratio_2s is the share of the frames of the window, not of its time: uneven frames move the
    moment it passes the limit both ways (the stuttering loop alerts up to 0.1 s early). A phone seen for
    0.8 s of the 2 s (40 %) reads 36-48 %, still far from the limit."""
    gap = largest_gap(loop)
    ratio, window_s = float(TH["risk"]["distraction"]["phone_ratio"]), float(TH["distraction"]["phone_window_s"])
    for phase in PHASES:
        start = WARM_S + phase
        alerts, _ = drive(loop, lambda t: {}, WARM_S + 8, phone=lambda t, a=start: a <= t < a + 5.0)
        late = late_by(alerts, 2, "phone", start + ratio * window_s + RISE_S[2])
        assert -gap <= late <= 2 * gap + 0.01
        alerts, results = drive(loop, lambda t: {}, WARM_S + 4, phone=lambda t, a=start: a <= t < a + 0.8)
        assert alerts == []
        assert max(r.distraction.phone_ratio_2s for r in results) == pytest.approx(0.8 / window_s, abs=0.1)


# ---------------------------------------------------------------- what a slow loop costs


@pytest.mark.parametrize("loop", LOOPS)
def test_a_closure_is_timed_short_by_at_most_two_frame_gaps(loop):
    """The first frame that shows the eyes shut comes up to one gap after they shut, and the last one up to
    one gap before they open."""
    gap = largest_gap(loop)
    for phase in PHASES:
        _, results = drive(loop, during(WARM_S + phase, 3.0, ear=SHUT), WARM_S + 5)
        short = 3.0 - max(r.drowsiness.closed_duration for r in results)
        assert 0.0 <= short <= 2 * gap + 0.01


@pytest.mark.parametrize(
    "loop",
    [
        known_gap(
            loop,
            "10 FPS uneven",
            "10 FPS uneven, other waits",
            "stutter",
            reason="timed short by up to two frame gaps: missed in 4, 3 and 1 of 5 tries",
        )
        for loop in LOOPS
    ],
)
def test_a_closure_a_tenth_of_a_second_over_the_limit_is_an_l3(loop):
    """Every even loop down to 10 FPS still alerts it. An uneven one at 10 FPS mostly does not."""
    for phase in PHASES:
        alerts, _ = drive(loop, during(WARM_S + phase, L3_S + 0.1, ear=SHUT), WARM_S + 5)
        assert [(lv, reasons) for _, lv, reasons in alerts] == [(3, ("microsleep",))]


@pytest.mark.parametrize(
    "loop",
    [
        known_gap(
            loop,
            "10 FPS uneven",
            "10 FPS uneven, other waits",
            "stutter",
            reason="timed short by up to two frame gaps: no `microsleep` event in 5, 3 and 5 of 5 tries",
        )
        for loop in LOOPS
    ],
)
def test_a_closure_a_tenth_of_a_second_over_microsleep_min_s_is_a_microsleep_event(loop):
    """The event that gives 25 points of drowsy_score for 5 minutes (no alert by itself)."""
    shut_s = float(TH["drowsiness"]["microsleep_min_s"]) + 0.1
    for phase in PHASES:
        _, results = drive(loop, during(WARM_S + phase, shut_s, ear=SHUT), WARM_S + 5)
        assert events(results, "microsleep") == 1


def nod(start, drop_s=0.6, rise_s=0.2, depth=30.0):
    """The head sinks with the eyes shut, then jerks back up."""

    def signal(t):
        x = t - start
        if 0 <= x < drop_s:
            return {"pitch": depth * x / drop_s, "ear": SHUT}
        if drop_s <= x < drop_s + rise_s:
            return {"pitch": depth * (1 - (x - drop_s) / rise_s), "ear": SHUT}
        return {}

    return signal


@pytest.mark.parametrize(
    "loop",
    [
        known_gap(
            loop,
            "stutter",
            reason="the 0.3 s without a frame can fall on the way up: the first frame after it shows open "
            "eyes and counts 0.3 s as open, the closed share of the dip drops under "
            "nod.eyes_closed_min_frac and the nod is a `bow` (1 of 5 tries)",
        )
        for loop in LOOPS
    ],
)
def test_a_nod_with_the_eyes_shut_is_a_nod(loop):
    for phase in PHASES:
        _, results = drive(loop, nod(WARM_S + phase), WARM_S + 5)
        assert (events(results, "nod"), events(results, "bow")) == (1, 0)
