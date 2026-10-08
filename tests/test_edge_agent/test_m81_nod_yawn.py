"""M81: nods and yawns (audit 08/10, A2 M3 and M4).

- The eyes "closed" in a head dip are firmly shut eyes, not lids lowered to look down.
- A yawn is counted once when the face is lost in the middle of it.
- MAR is read as facing the camera before a yawn is counted: a turned head narrows the mouth.

Fake numbers at 30 FPS, no video.
"""

import math

import pytest

from edge_agent.analysis.drowsiness import DrowsinessAnalyzer, DrowsinessConfig
from edge_agent.analysis.drowsiness.mouth import frontal_mar
from edge_agent.config import load_thresholds
from edge_agent.perception.features import FrameFeatures

FPS = 30
DT = 1.0 / FPS
OPEN = 0.30
SHUT = 0.08


def const(v):
    return lambda t: v


def run(seconds, analyzer=None, t0=0.0, **signal):
    """Fake frames through block 7. signal: ear, mar, pitch, yaw, blink, p_closed, face as f(t)."""
    a = analyzer or DrowsinessAnalyzer(DrowsinessConfig.from_dict(load_thresholds()["drowsiness"]))
    get = {"ear": const(OPEN), "mar": const(0.05), "pitch": const(0.0), "yaw": const(0.0), **signal}
    states = []
    for i in range(round(seconds * FPS)):
        t = t0 + i * DT
        if "face" in get and not get["face"](t):
            f = FrameFeatures(i, t, False, 0.0)
        else:
            p = get["p_closed"](t) if "p_closed" in get else None
            f = FrameFeatures(
                i,
                t,
                True,
                1.0,
                ear=get["ear"](t),
                mar=get["mar"](t),
                pitch=get["pitch"](t),
                yaw=get["yaw"](t),
                roll=0.0,
                eye_blink=get["blink"](t) if "blink" in get else None,
                p_closed=p,
                p_closed_source=None if p is None else "cnn",
            )
        states.append(a.update(f))
    return a, states


def count(states, name):
    return sum(name in s.events for s in states)


def cfg(**overrides):
    return DrowsinessConfig.from_dict({**load_thresholds()["drowsiness"], **overrides})


def look_down(start, length=1.0, depth=20.0):
    return lambda t: depth if start <= t < start + length else 0.0


def during(start, length, inside, outside):
    return lambda t: inside if start <= t < start + length else outside


# ---------------------------------------------------------------- nod: the eyes in a dip


@pytest.mark.parametrize("ratio", [0.9, 0.7, 0.6, 0.5])
def test_a_short_look_down_with_lowered_lids_is_a_bow(ratio):
    """The audit's case: 20 deg down for 1 s, eyes open, EAR at 0.9 .. 0.5 x the open-eye value."""
    _, s = run(25, pitch=look_down(20.0), ear=during(20.0, 1.0, ratio * OPEN, OPEN))
    assert count(s, "nod") == 0 and count(s, "bow") == 1


@pytest.mark.parametrize(("ratio", "nods"), [(0.9, 0), (0.7, 0), (0.6, 1), (0.5, 1)])
def test_with_the_plain_close_threshold_lowered_lids_were_a_nod(ratio, nods):
    a = DrowsinessAnalyzer(cfg(nod={**load_thresholds()["drowsiness"]["nod"], "eyes_deep": False}))
    _, s = run(25, analyzer=a, pitch=look_down(20.0), ear=during(20.0, 1.0, ratio * OPEN, OPEN))
    assert count(s, "nod") == nods


def test_two_looks_at_the_dashboard_do_not_fill_the_nod_term():
    pitch = lambda t: 20.0 if 20.0 <= t < 21.0 or 40.0 <= t < 41.0 else 0.0  # noqa: E731
    ear = lambda t: 0.5 * OPEN if 20.0 <= t < 21.0 or 40.0 <= t < 41.0 else OPEN  # noqa: E731
    _, s = run(45, pitch=pitch, ear=ear)
    assert s[-1].nod_count_5min == 0 and count(s, "bow") == 2


def test_a_dip_with_the_eyes_firmly_shut_is_still_a_nod():
    _, s = run(25, pitch=look_down(20.0), ear=during(20.0, 1.0, SHUT, OPEN))
    assert count(s, "nod") == 1 and s[-1].nod_count_5min == 1


def test_the_bowed_ear_limit_decides():
    """Bowed head: firmly shut is EAR <= microsleep_deep.bowed_ear_ratio (0.35) x the open-eye value."""
    _, s = run(25, pitch=look_down(20.0), ear=during(20.0, 1.0, 0.33 * OPEN, OPEN))
    assert count(s, "nod") == 1
    _, s = run(25, pitch=look_down(20.0), ear=during(20.0, 1.0, 0.40 * OPEN, OPEN))
    assert count(s, "nod") == 0


def test_the_eye_blink_vote_counts_in_a_dip():
    """EAR collapsed but MediaPipe's eyeBlink says the eyes are not shut (glare, a tilted head)."""
    ear = during(20.0, 1.0, SHUT, OPEN)
    _, s = run(25, pitch=look_down(20.0), ear=ear, blink=during(20.0, 1.0, 0.3, 0.05))
    assert count(s, "nod") == 0
    _, s = run(25, pitch=look_down(20.0), ear=ear, blink=during(20.0, 1.0, 0.7, 0.05))
    assert count(s, "nod") == 1


def test_block_5_frames_need_the_deep_score():
    """Eye CNN frames: closed from 0.6, firmly shut from microsleep_deep.cnn (0.8)."""
    _, s = run(25, pitch=look_down(20.0), p_closed=during(20.0, 1.0, 0.7, 0.05))
    assert count(s, "nod") == 0 and count(s, "bow") == 1
    _, s = run(25, pitch=look_down(20.0), p_closed=during(20.0, 1.0, 0.9, 0.05))
    assert count(s, "nod") == 1


def test_eyes_shut_for_a_third_of_the_dip_is_enough():
    """nod.eyes_closed_min_frac (0.3) is unchanged: the eyes need not stay shut for the whole dip."""
    _, s = run(25, pitch=look_down(20.0), ear=during(20.3, 0.4, SHUT, OPEN))
    assert count(s, "nod") == 1


# ---------------------------------------------------------------- yawn: counted once


def mouth(*spans, wide=0.8):
    return lambda t: wide if any(a <= t < b for a, b in spans) else 0.05


def seen(*lost):
    return lambda t: not any(a <= t < b for a, b in lost)


def test_a_yawn_with_the_face_lost_in_the_middle_is_one_yawn():
    """The audit's case: mouth open 2 s, face lost 0.6 s (a hand over it), open 2.4 s more."""
    _, s = run(12, mar=mouth((3.0, 8.0)), face=seen((5.0, 5.6)))
    assert count(s, "yawn") == 1 and s[-1].yawn_count_10min == 1


def test_the_yawning_flag_holds_behind_the_hand_and_ends_with_the_mouth_closed():
    _, s = run(12, mar=mouth((3.0, 8.0)), face=seen((5.0, 5.6)))
    at = lambda t: s[round(t * FPS)]  # noqa: E731
    assert at(4.8).yawning and at(5.5).yawning and at(7.0).yawning
    assert not at(8.2).yawning


def test_a_second_yawn_after_the_mouth_was_seen_closed_is_counted():
    _, s = run(20, mar=mouth((3.0, 7.0), (10.0, 14.0)), face=seen((5.0, 5.6)))
    assert count(s, "yawn") == 2


def test_an_opening_not_yet_counted_is_still_dropped_when_the_face_is_lost():
    """1 s open, face lost 0.6 s, 1 s open: neither part is a yawn on its own (yawn.min_s 1.5)."""
    _, s = run(10, mar=mouth((3.0, 5.6)), face=seen((4.0, 4.6)))
    assert count(s, "yawn") == 0


def test_a_counted_yawn_is_not_held_longer_than_a_yawn_lasts():
    """Face gone past microsleep_mask.max_open_s (8 s) after the mouth opened: what comes back is new."""
    _, s = run(20, mar=mouth((3.0, 16.0)), face=seen((5.0, 12.0)))
    assert not s[round(11.9 * FPS)].yawning
    assert count(s, "yawn") == 2  # 4.5 s and 13.5 s
    _, s = run(20, mar=mouth((3.0, 16.0)), face=seen((5.0, 9.0)))  # back within the 8 s: the same yawn
    assert count(s, "yawn") == 1


# ---------------------------------------------------------------- yawn: MAR and head yaw


def turned(mar, yaw):
    """What the camera measures for a mouth that reads `mar` facing it, with the head turned by yaw."""
    return mar / math.cos(math.radians(yaw))


def test_frontal_mar_undoes_the_turn():
    assert turned(0.37, 35.0) > 0.45  # the audit's numbers: 0.37 reads 0.452 at 35 deg
    for yaw in (-45.0, -20.0, 0.0, 20.0, 30.0, 35.0, 45.0):
        assert frontal_mar(turned(0.37, yaw), yaw) == pytest.approx(0.37)
    assert frontal_mar(0.5, None) == 0.5 and frontal_mar(None, 30.0) is None
    assert frontal_mar(0.5, 120.0) == pytest.approx(0.0)


@pytest.mark.parametrize("yaw", [35.0, -35.0, 45.0])
def test_a_half_open_mouth_with_the_head_turned_is_not_a_yawn(yaw):
    """Singing / a held "ah" at MAR 0.37: below the yawn threshold facing the camera, above it turned."""
    _, s = run(12, yaw=const(yaw), mar=mouth((3.0, 7.0), wide=turned(0.37, yaw)))
    assert count(s, "yawn") == 0
    off = DrowsinessAnalyzer(cfg(yawn={**load_thresholds()["drowsiness"]["yawn"], "yaw_correct": False}))
    _, s = run(12, analyzer=off, yaw=const(yaw), mar=mouth((3.0, 7.0), wide=turned(0.37, yaw)))
    assert count(s, "yawn") == 1


@pytest.mark.parametrize("yaw", [0.0, 20.0, 35.0])
def test_a_real_yawn_with_the_head_turned_is_still_a_yawn(yaw):
    _, s = run(12, yaw=const(yaw), mar=mouth((3.0, 7.0), wide=turned(0.8, yaw)))
    assert count(s, "yawn") == 1


def test_the_turn_is_measured_to_the_camera_not_to_the_usual_pose():
    """Head turned 35 deg from the first frame (camera off to the side): the usual pose is 35 deg,
    the mouth is still narrowed by cos(35)."""
    _, s = run(30, yaw=const(35.0), mar=mouth((20.0, 24.0), wide=turned(0.37, 35.0)))
    assert count(s, "yawn") == 0


def test_the_mask_keeps_the_measured_mar():
    """The yawn / talking mask is not corrected: it hides closed-eye time, a wider mask is the safe side."""
    _, s = run(12, yaw=const(35.0), mar=mouth((3.0, 7.0), wide=turned(0.37, 35.0)))
    assert s[round(5.0 * FPS)].closure_masked and not s[round(5.0 * FPS)].yawning


# ---------------------------------------------------------------- config


def test_the_two_switches_come_from_thresholds_yaml_and_match_the_defaults():
    d = load_thresholds()["drowsiness"]
    assert d["nod"]["eyes_deep"] is True and d["yawn"]["yaw_correct"] is True
    c, default = DrowsinessConfig.from_dict(d), DrowsinessConfig()
    assert c.nod_eyes_deep is default.nod_eyes_deep is True
    assert c.yawn_yaw_correct is default.yawn_yaw_correct is True
