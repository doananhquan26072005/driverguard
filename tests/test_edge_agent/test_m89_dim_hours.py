"""M89: the hours in which the HUD is dimmed are the screen's own (hud.dim_hours), apart from the
hours of the night factor on the drowsy score (context.night_hours). Until M89 one window did both
(audit 08/10, X6 and A4 M9). Fake numbers only: no video, no model."""

import copy
import json

import pytest

from edge_agent.config import load_thresholds
from edge_agent.context.can_sim import CanSimulator, scenario_from_dict
from edge_agent.decision.pipeline import DecisionPipeline
from edge_agent.hud.server import HudConfig, HudState, hud_display
from edge_agent.perception.features import FrameFeatures
from edge_agent.web.bridge import WebAgent

TH = load_thresholds()
FPS = 30


def with_hours(night=None, dim=None):
    th = copy.deepcopy(TH)
    if night is not None:
        th["context"]["night_hours"] = night
    if dim is not None:
        th["hud"]["dim_hours"] = dim
    return th


def drive(clock, thresholds=TH, seconds=70.0):
    """A drive at 60 km/h starting at `clock` with one 1.1 s eye closure and the score it peaks at:
    (HUD state after the last frame, highest drowsy_score)."""
    pipeline = DecisionPipeline(thresholds)
    can = CanSimulator(scenario_from_dict({"start_clock": clock, "timeline": [{"t": 0, "speed_kmh": 60}]}))
    hud = HudState(HudConfig.from_dict(thresholds["hud"]), hud_display(thresholds))
    peak = 0.0
    for i in range(int(seconds * FPS)):
        t = i / FPS
        ear = 0.05 if 40.0 <= t < 41.1 else 0.30
        r = pipeline.step(
            FrameFeatures(i, t, True, 1.0, ear=ear, mar=0.05, pitch=0.0, yaw=0.0, roll=0.0), False, can.sample(t)
        )
        peak = max(peak, r.risk.drowsy_score)
    hud.update(r, fps=FPS)
    return hud.to_json(), peak


@pytest.mark.parametrize(
    ("clock", "night", "dim"),
    [
        ("12:00", False, False),
        ("17:30", False, False),
        ("18:30", False, True),  # dark outside: the screen dims, the score is the day's
        ("23:00", False, True),
        ("02:00", True, True),
        ("05:30", False, True),  # the night factor is over, the sun is not up
        ("06:30", False, False),
    ],
)
def test_the_screen_and_the_score_each_have_their_hours(clock, night, dim):
    state, _ = drive(clock, seconds=1.0)
    assert (state["night"], state["dim"]) == (night, dim)


def test_an_evening_drive_is_dimmed_and_scored_like_the_day():
    """What X6 asked for: dusk to midnight is dark for the eyes without raising the score."""
    _, noon = drive("12:00")
    evening_state, evening = drive("20:00")
    _, small_hours = drive("02:00")
    assert noon > 0
    assert evening == noon and evening_state["dim"] is True and evening_state["night"] is False
    assert small_hours == pytest.approx(noon * TH["risk"]["drowsy"]["night_factor"])


def test_moving_the_screen_hours_does_not_touch_the_score():
    state, score = drive("20:00", with_hours(dim=[[21, 4]]))
    assert state["dim"] is False and score == drive("20:00")[1]
    state, score = drive("02:00", with_hours(dim=[]))  # [] = never dimmed
    assert state["dim"] is False and state["night"] is True and score == drive("02:00")[1]


def test_moving_the_score_hours_does_not_touch_the_screen():
    """Before M89 widening the night window to the evening was the only way to dim at 20:00."""
    state, score = drive("20:00", with_hours(night=[[19, 5]]))
    assert state["night"] is True and state["dim"] is True
    assert score == pytest.approx(drive("20:00")[1] * TH["risk"]["drowsy"]["night_factor"])
    state, _ = drive("02:00", with_hours(night=[]))
    assert state["night"] is False and state["dim"] is True


def test_the_page_agent_sends_the_same_flag():
    agent = WebAgent("web-an", "trip-1")
    assert "dim" not in json.loads(agent.hud_state())  # nothing decided yet: the screen is not dimmed
    assert agent.hud.config.dim_hours == HudConfig.from_dict(TH["hud"]).dim_hours == ((18.0, 6.0),)
    agent = WebAgent("web-an", "trip-2", scenario="highway_night")  # a scripted drive in the small hours
    state = json.loads(agent.frame(0.0, 0, 640, 480, None, 1, (0.05, 0.05), 12.0, 140.0))  # no face: context still runs
    assert state["dim"] is True and state["night"] is True
