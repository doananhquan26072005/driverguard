"""M95: a device that never gets a speed reading is not "parked" for the whole trip (audit 08/10,
finding 1; decision 8A of 09/10).

Before: without the driving simulator the vehicle source answered 0 km/h for good, block 10 called it
standing still, and from M30 standing still means no alert at all, no "monitoring paused" either: eyes
shut for 10 s, no sound. Now, once the camera has watched a driver for context.vehicle_signal_wait_s
without any reading, the speed is unknown: monitored as moving, and the driver / backend are told, as
for a signal lost while driving (M26). Time on the enrollment screens does not count: enrollment needs a
parked vehicle.
Fake landmark sequences through the page's agent (edge_agent/web/bridge.py), no browser, no video.
"""

import pytest

from edge_agent.config import load_thresholds
from edge_agent.context.can_sim import ExternalVehicle
from edge_agent.web.bridge import WebAgent
from tests.test_edge_agent.test_web_bridge import events_of, run, synthetic_face

WAIT_S = float(load_thresholds()["context"]["vehicle_signal_wait_s"])
OPEN, SHUT = synthetic_face(), synthetic_face(ear=0.05)


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


def watch(vehicle, seconds, t0=0.0, watching=True, fps=30.0):
    for i in range(1, int(seconds * fps) + 1):
        vehicle.observe(t0 + i / fps, watching)
    return t0 + seconds


# ---------------------------------------------------------------- the vehicle source


def test_the_wait_comes_from_the_yaml():
    assert WAIT_S == 30.0
    agent = WebAgent("web-an", "trip-m95")
    assert agent.external is not None and agent.external.wait_s == WAIT_S


def test_never_a_reading_turns_into_speed_unknown_after_the_wait():
    v = ExternalVehicle(clock=FakeClock(), wait_s=WAIT_S)
    v.observe(0.0, True)
    t = watch(v, WAIT_S - 1.0)
    assert not v.never_received and not v.link_lost and v.sample(t).speed_kmh == 0.0  # still "parked"
    t = watch(v, 1.5, t0=t)
    assert v.never_received and v.link_lost and v.signal_lost and not v.connected
    assert v.sample(t).speed_kmh is None  # unknown: block 10 takes it for moving


def test_only_time_with_a_driver_in_view_counts_and_a_hole_counts_little():
    v = ExternalVehicle(clock=FakeClock(), wait_s=WAIT_S, stale_s=1.0)
    v.observe(0.0, True)
    t = watch(v, 3 * WAIT_S, watching=False)  # nobody in view (or the enrollment screens)
    assert not v.never_received
    v.observe(t + 600.0, True)  # ten minutes without a frame: one stale_s, not ten minutes
    assert not v.never_received
    watch(v, WAIT_S, t0=t + 600.0)
    assert v.never_received


def test_a_first_reading_ends_it_and_parked_is_parked_again():
    clock = FakeClock()
    v = ExternalVehicle(clock=clock, wait_s=WAIT_S)
    v.observe(0.0, True)
    t = watch(v, WAIT_S + 1.0)
    assert v.never_received
    v.update(0.0, None)
    assert not v.never_received and v.connected and not v.link_lost and v.sample(t).speed_kmh == 0.0
    clock.t += 5.0  # ... and when that link goes quiet while parked, it is the M26 case: parked
    assert v.link_lost and not v.signal_lost and v.sample(t + 5.0).speed_kmh == 0.0


def test_a_wait_of_zero_is_the_behaviour_before_m95():
    v = ExternalVehicle(clock=FakeClock())  # wait_s 0
    v.observe(0.0, True)
    t = watch(v, 10 * WAIT_S)
    assert not v.never_received and not v.link_lost and v.sample(t).speed_kmh == 0.0


# ---------------------------------------------------------------- through the page's agent


@pytest.fixture
def later():
    """The page with no driving simulator, the driver answered "Để sau" on the consent screen."""
    agent = WebAgent("web-an", "trip-m95")
    state, t, f = run(agent, 1, points=OPEN)
    assert state["enrollment"]["status"] == "consent" and not state["vehicle"]["driving"]
    assert agent.vehicle("enroll_later") == "ok"
    return agent, t, f


def test_before_the_wait_the_page_is_parked_and_silent(later):
    agent, t, f = later
    _, t, f = run(agent, 12, t0=t, frame0=f, points=OPEN)
    state, _, _ = run(agent, 10, t0=t, frame0=f, points=SHUT, blink=(0.9, 0.9))  # 23 s in view so far
    assert state["level"] == 0 and not state["vehicle"]["driving"] and not state["vehicle"]["signal_lost"]
    assert [e for e in events_of(agent) if e.get("level")] == []


def test_after_the_wait_the_driver_is_told_and_eyes_shut_is_l3(later):
    agent, t, f = later
    state, t, f = run(agent, WAIT_S + 2, t0=t, frame0=f, points=OPEN)
    v = state["vehicle"]
    assert v["signal_lost"] and v["never_received"] and v["driving"] and v["speed_kmh"] is None
    assert not v["connected"]
    assert [e["reasons"] for e in events_of(agent)] == [["vehicle_signal_lost"]]
    state, _, _ = run(agent, 2.5, t0=t, frame0=f, points=SHUT, blink=(0.9, 0.9))
    assert state["level"] == 3 and "microsleep" in state["reasons"]
    assert [e["reasons"] for e in events_of(agent)] == [["microsleep"]]


def test_after_the_wait_a_covered_camera_is_monitoring_paused(later):
    agent, t, f = later
    _, t, f = run(agent, WAIT_S + 2, t0=t, frame0=f, points=OPEN)
    events_of(agent)
    state, _, _ = run(agent, 5, t0=t, frame0=f, points=None)
    assert state["unavailable"]
    assert [e["reasons"] for e in events_of(agent)] == [["monitoring_unavailable"]]


def test_the_first_reading_brings_the_vehicle_back(later):
    agent, t, f = later
    _, t, f = run(agent, WAIT_S + 2, t0=t, frame0=f, points=OPEN)
    events_of(agent)
    agent.vehicle_signal(0.0, None)
    state, _, _ = run(agent, 0.5, t0=t, frame0=f, points=OPEN)
    v = state["vehicle"]
    assert v["connected"] and not v["signal_lost"] and not v["never_received"] and not v["driving"]
    assert [e["reasons"] for e in events_of(agent)] == [["vehicle_signal_restored"]]


def test_the_consent_screen_and_the_enrollment_steps_do_not_count():
    agent = WebAgent("web-an", "trip-m95")
    state, t, f = run(agent, 2 * WAIT_S, points=OPEN)  # the consent screen is up, nobody answers
    assert state["enrollment"]["status"] == "consent"
    assert not state["vehicle"]["signal_lost"] and not state["vehicle"]["driving"]
    assert agent.vehicle("enroll_start") == "ok"
    state, t, f = run(agent, 1, t0=t, frame0=f, points=OPEN)
    assert state["enrollment"]["status"] not in ("consent", "later", "done", "failed", "off")
    assert not state["vehicle"]["signal_lost"]  # enrolling: still parked, the steps can go on


def test_nobody_in_view_does_not_count(later):
    agent, t, f = later
    state, _, _ = run(agent, 2 * WAIT_S, t0=t, frame0=f, points=None)
    assert not state["vehicle"]["signal_lost"] and not state["vehicle"]["driving"]
    assert not state["unavailable"]  # parked: an empty seat is not "monitoring paused"


def test_a_scripted_scenario_is_not_touched():
    agent = WebAgent("web-an", "trip-m95", scenario="parked")
    state, _, _ = run(agent, WAIT_S + 5, points=OPEN)
    assert not state["vehicle"]["signal_lost"] and not state["vehicle"]["driving"]
