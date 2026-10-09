"""M93: three shares that were counted in frames are shares of time (decision 7A of 09/10 on what M75
measured; audit 08/10, X4).

- distraction.phone_ratio_2s: time of the window with a phone, not results with a phone.
- drowsiness.microsleep_deep.min_frac: time of the closure firmly shut, not frames.
- drowsiness.nod.eyes_closed_min_frac: the first frame after a long wait no longer carries the wait.
A frame stands for half the wait before it and half the wait after it (`TimeShare`). At an even frame
rate that is exactly the share of frames: nothing changes there (the trace regression is not re-pinned).
Durations are not padded: a closure is still timed from the first frame that shows it (decided 09/10).
Fake sequences, the real config/thresholds.yaml, no video.
"""

import random

import pytest

from edge_agent.analysis.drowsiness import DrowsinessAnalyzer, DrowsinessConfig
from edge_agent.analysis.drowsiness.common import TimeShare
from edge_agent.config import load_thresholds
from edge_agent.perception.features import FrameFeatures
from tests.test_edge_agent import test_m75_low_fps as m75

TH = load_thresholds()
PHONE_RATIO = float(TH["risk"]["distraction"]["phone_ratio"])
WINDOW_S = float(TH["distraction"]["phone_window_s"])
DEEP = TH["drowsiness"]["microsleep_deep"]
OPEN = 0.30


# ---------------------------------------------------------------- TimeShare


@pytest.mark.parametrize("seed", range(5))
def test_at_an_even_rate_the_share_of_time_is_the_share_of_frames(seed):
    rng, share, on, read = random.Random(seed), TimeShare(), 0, 0
    for _ in range(200):
        reading = rng.choice([True, False, None])  # None: a frame that was not read
        share.step(1 / 30, reading)
        if reading is not None:
            read, on = read + 1, on + reading
            assert share.share == pytest.approx(on / read)


def test_half_the_frames_is_half_the_time_despite_float_waits():
    """Found on UTA-RLDD while measuring: waits taken from timestamps (k / 30) differ in their last
    bits, 18 of 36 summed to 0.49999999 and a closure at exactly min_frac stopped counting as deep."""
    share, last = TimeShare(), 0.0
    for k in range(1, 37):
        t = k / 30
        share.step(t - last, k % 2 == 0)
        last = t
    assert share.share == 0.5 and share.at_least(0.5)


def test_the_frame_after_a_long_wait_does_not_carry_the_wait():
    share = TimeShare()
    for _ in range(9):
        share.step(0.1, True)  # 0.9 s read as "yes"
    share.step(0.5, False)  # then nothing for 0.5 s, and a "no"
    # by frames: 9 of 10. By the wait before each frame (PERCLOS-style): 0.9 of 1.4 s = 64 %.
    # Half the long wait belongs to the last "yes", and the "no" stands for the wait it has.
    assert share.share == pytest.approx((8 * 0.1 + 0.3) / (8 * 0.1 + 0.3 + 0.5))


def test_a_burst_counts_for_the_time_it_spans():
    share = TimeShare()
    for _ in range(10):
        share.step(0.2, False)  # 2 s at 5 FPS
    for _ in range(10):
        share.step(0.01, True)  # 10 frames in 0.1 s
    share.step(0.2, False)
    assert 0.5 > 10 / 21 > 0.45  # by frames: nearly half
    assert share.share == pytest.approx(0.2 / 2.3, abs=0.01)


def test_one_frame_is_its_own_reading_and_none_is_nothing():
    share = TimeShare()
    assert share.share == 0.0 and not share.at_least(0.0)
    share.step(0.0, True)
    assert share.share == 1.0 and share.at_least(0.5)
    share.reset()
    share.step(0.0, False)
    assert share.share == 0.0 and share.at_least(0.0) and not share.at_least(0.5)


# ---------------------------------------------------------------- phone ratio (block 8)


BURST_S = 0.7


def bursts(end, slow=0.2, fast=1 / 30, burst_at=m75.WARM_S + 1.0, burst_s=BURST_S):
    """5 FPS, but 30 FPS for `burst_s` from `burst_at`: the loop caught up for a moment."""
    out, t = [], 0.0
    while t < end:
        out.append(t)
        t += fast if burst_at <= t < burst_at + burst_s else slow
    return out


def test_a_phone_seen_for_a_third_of_the_window_is_no_alert_however_many_frames_show_it(monkeypatch):
    """A phone in view for 0.7 s, exactly while the loop runs fast: over two thirds of the window's frames
    show it (over the 60 % line of the `phone` rule, which is where the ratio stood before M93), a third
    of its time."""
    monkeypatch.setitem(m75.LOOPS, "bursts", bursts)
    start = m75.WARM_S + 1.0
    alerts, results = m75.drive("bursts", lambda t: {}, m75.WARM_S + 6, phone=lambda t: start <= t < start + BURST_S)
    window = [r for r in results if start + BURST_S - WINDOW_S < r.risk.t <= start + BURST_S]
    by_frames = sum(start <= r.risk.t < start + BURST_S for r in window) / len(window)
    assert by_frames > PHONE_RATIO + 0.05
    assert alerts == []
    assert max(r.distraction.phone_ratio_2s for r in results) == pytest.approx(BURST_S / WINDOW_S, abs=0.06)


def test_a_phone_held_up_is_still_alerted_on_that_loop(monkeypatch):
    monkeypatch.setitem(m75.LOOPS, "bursts", bursts)
    start = m75.WARM_S + 0.5
    alerts, _ = m75.drive("bursts", lambda t: {}, m75.WARM_S + 8, phone=lambda t: start <= t < start + 5.0)
    assert [(level, reasons) for _, level, reasons in alerts] == [(2, ("phone",))]


# ---------------------------------------------------------------- deep closure (block 7)


def closure(times, narrowed_until, shut_until, start):
    """Eyes narrowed (closed, not firmly shut) from `start`, then firmly shut. Returns closed_duration per frame."""
    cfg = DrowsinessConfig.from_dict(TH["drowsiness"])
    narrowed = OPEN * (DEEP["ear_ratio"] + TH["drowsiness"]["eye"]["close_ratio"]) / 2  # between the two lines
    analyzer, out = DrowsinessAnalyzer(cfg), {}
    for i, t in enumerate(times):
        ear = OPEN
        if start <= t < narrowed_until:
            ear = narrowed
        elif narrowed_until <= t < shut_until:
            ear = 0.05
        f = FrameFeatures(i, t, True, 1.0, ear=ear, mar=0.05, pitch=0.0, yaw=0.0, roll=0.0)
        out[t] = analyzer.update(f).closed_duration
    return out


def test_narrowed_frames_in_a_burst_do_not_outvote_the_time_the_eyes_were_shut():
    """Lids narrowed for 0.2 s while the loop runs at 30 FPS (7 frames), then firmly shut for 1 s at 5 FPS
    (5 frames). By frames the closure is 5 / 12 deep, under min_frac, and only the shut stretch counted
    (1.0 s at its last frame); by time it is 5 / 6 deep and is timed from where it began."""
    warm = [k / 30 for k in range(30 * 30)]
    start = 30.0
    fast = [start + k / 30 for k in range(7)]  # 30.000 .. 30.200: narrowed
    slow = [start + 0.4 + 0.2 * k for k in range(6)]  # 30.4 .. 31.4: shut
    got = closure(warm + fast + slow, narrowed_until=start + 0.3, shut_until=start + 1.5, start=start)
    last_shut = slow[-1]
    assert 5 / 12 < DEEP["min_frac"]
    assert got[last_shut] == pytest.approx(last_shut - start)  # from the first narrowed frame
    assert got[last_shut] - (last_shut - slow[0]) == pytest.approx(0.4)  # the stretch alone was 0.4 s shorter


def test_at_an_even_rate_mostly_narrowed_is_still_not_deep():
    times = [k / 30 for k in range(30 * 32)]
    got = closure(times, narrowed_until=30.8, shut_until=31.2, start=30.0)  # 0.8 s narrowed, 0.4 s shut
    at = max(t for t in got if t < 31.2)
    assert got[at] == pytest.approx(at - 30.8, abs=0.04)  # only the firmly shut stretch (M76)


# ---------------------------------------------------------------- nod (block 7), on top of test_m75


@pytest.mark.parametrize("phase", [k * 0.02 for k in range(20)])
def test_a_nod_on_the_stuttering_loop_is_a_nod_wherever_the_long_wait_falls(phase):
    _, results = m75.drive("stutter", m75.nod(m75.WARM_S + phase), m75.WARM_S + 5)
    assert (m75.events(results, "nod"), m75.events(results, "bow")) == (1, 0)


def test_a_look_down_with_the_eyes_open_is_still_a_bow_on_every_loop():
    def look_down(start):
        nod = m75.nod(start)
        return lambda t: {k: v for k, v in nod(t).items() if k != "ear"}

    for loop in m75.LOOPS:
        for phase in m75.PHASES:
            _, results = m75.drive(loop, look_down(m75.WARM_S + phase), m75.WARM_S + 5)
            assert m75.events(results, "nod") == 0, loop
