"""M96: a loop under 2 FPS is not "monitoring, alerts may be late" but not monitoring (decision 11A of
09/10 on what M71 left open).

Blocks 7, 8 and 12 take two frames more than max_gap_s (0.5 s) apart for a hole: a running closure, look
away or confirmation starts again. When every frame comes that late nothing can be timed: eyes shut for
ten seconds raise no alert. Before, the HUD showed the driver panel with a "slow" chip and the backend
got `monitoring`. Now, after hud.low_fps_s of it, the HUD shows "monitoring paused" with the reason
`slow_loop`, the backend gets monitoring_unavailable, and the heartbeat says `unavailable`.
Fake landmark sequences through the page's agent, no browser, no video.
"""

import json

import pytest

from backend.schemas import EventIn
from edge_agent.config import load_thresholds
from edge_agent.web.bridge import WebAgent
from tests.test_edge_agent.test_web_bridge import H, W, events_of, synthetic_face

TH = load_thresholds()
MAX_GAP_S = min(TH["drowsiness"]["max_gap_s"], TH["distraction"]["max_gap_s"], TH["alert"]["max_gap_s"])
WAIT_S = float(TH["hud"]["low_fps_s"])
OPEN, SHUT = synthetic_face(), synthetic_face(ear=0.05)


def loop(agent, seconds, fps, t0=0.0, points=OPEN, blink=(0.05, 0.05)):
    """Frames every 1 / fps seconds. Returns (state after the last one, time of the next frame)."""
    state, n = None, round(seconds * fps)
    for i in range(n):
        t = t0 + i / fps
        state = agent.frame(t, round(t * 30), W, H, None if points is None else points.ravel(), 1, blink, 12.0, 140.0)
    return json.loads(state), t0 + n / fps


@pytest.fixture
def driving():
    agent = WebAgent("web-an", "trip-m96", scenario="highway_night")
    _, t = loop(agent, 12, 30)  # baselines settle
    events_of(agent)
    return agent, t


def reasons(agent):
    return [(e["reasons"][0], (e.get("metrics") or {}).get("cause")) for e in events_of(agent)]


def test_the_limit_is_the_blocks_own_gap():
    assert MAX_GAP_S == 0.5 and WAIT_S == 5.0
    assert WebAgent("web-an", "trip-m96", scenario="highway_night").runtime.decisions.max_gap_s == MAX_GAP_S


def test_under_two_fps_nothing_is_timed_and_the_driver_is_told(driving):
    agent, t = driving
    state, t = loop(agent, WAIT_S - 1, 1.5, t0=t)
    assert not state["unavailable"]  # not yet: a few slow frames are not a loop that cannot keep up
    state, t = loop(agent, 4, 1.5, t0=t)
    assert state["unavailable"] and state["unavailable_reason"] == "slow_loop"
    assert ("monitoring_unavailable", "slow_loop") in reasons(agent)
    assert json.loads(agent.take_heartbeat())["heartbeat"]["state"] == "unavailable"
    # what the state is there for: eyes shut for ten seconds, and block 7 cannot see a closure
    state, t = loop(agent, 10, 1.5, t0=t, points=SHUT, blink=(0.9, 0.9))
    assert state["level"] == 0 and state["unavailable"]
    assert [e for e in events_of(agent) if e.get("level")] == []  # no alert; the low_fps note may come


def test_one_frame_in_time_ends_it(driving):
    agent, t = driving
    _, t = loop(agent, WAIT_S + 3, 1.5, t0=t)
    events_of(agent)
    state, t = loop(agent, 1, 30, t0=t)
    assert not state["unavailable"] and state.get("unavailable_reason") is None
    assert reasons(agent)[0] == ("monitoring_restored", None)
    state, _ = loop(agent, 2.5, 30, t0=t, points=SHUT, blink=(0.9, 0.9))
    assert state["level"] == 3


def test_three_fps_is_slow_but_monitored(driving):
    agent, t = driving
    state, t = loop(agent, 20, 3, t0=t)
    assert state["low_fps"] and not state["unavailable"]
    assert all(r != "monitoring_unavailable" for r, _ in reasons(agent))
    state, _ = loop(agent, 3, 3, t0=t, points=SHUT, blink=(0.9, 0.9))
    assert state["level"] == 3  # late by a frame or two, but alerted


def test_a_single_hole_is_not_a_slow_loop(driving):
    agent, t = driving
    state, _ = loop(agent, 10, 30, t0=t + 20.0)  # the loop stood still for 20 s, then runs
    assert not state["unavailable"]
    assert all(c != "slow_loop" for _, c in reasons(agent))


def test_no_face_on_a_slow_loop_is_one_unavailable_not_two(driving):
    agent, t = driving
    _, t = loop(agent, WAIT_S + 3, 1.5, t0=t)
    state, t = loop(agent, 10, 1.5, t0=t, points=None)
    assert state["unavailable"] and state["unavailable_reason"] == "slow_loop"
    assert [r for r, _ in reasons(agent)].count("monitoring_unavailable") == 1


def test_the_backend_takes_the_new_cause(driving):
    agent, t = driving
    loop(agent, WAIT_S + 3, 1.5, t0=t)
    event = next(e for e in events_of(agent) if e["reasons"] == ["monitoring_unavailable"])
    assert EventIn.model_validate(event).metrics.cause == "slow_loop"
