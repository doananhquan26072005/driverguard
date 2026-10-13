"""M104: what the page needs to draw the driver's face on #/live (which face, the head's roll). Synthetic
landmarks, no camera, no picture."""

import json

import numpy as np

from edge_agent.web.bridge import WebAgent
from tests.test_edge_agent.test_m83_passenger_and_frozen_camera import seated
from tests.test_edge_agent.test_web_bridge import H, W, synthetic_face


def frame(agent: WebAgent, faces: list[np.ndarray]) -> dict:
    points = np.concatenate([f.ravel() for f in faces]) if faces else None
    n = len(faces)
    return json.loads(agent.frame(0.0, 0, W, H, points, n, [0.05] * (2 * n), 12.0, [140.0] * n if n else 140.0))


def test_the_page_is_told_which_of_its_faces_is_the_driver():
    agent = WebAgent("web-an", "trip-web-1", scenario="highway_night")
    passenger = seated(synthetic_face(), 500.0, scale=0.4)  # smaller: before enrollment the largest face drives
    driver = seated(synthetic_face(), 200.0, scale=0.7)
    measures = frame(agent, [passenger, driver])["measures"]
    assert measures["face"] and measures["driver"] == 1
    assert measures["roll"] is not None and abs(measures["roll"]) < 3  # the synthetic face is upright


def test_no_face_no_driver():
    measures = frame(WebAgent("web-an", "trip-web-1", scenario="highway_night"), [])["measures"]
    assert measures["driver"] is None and measures["roll"] is None
