"""Block 8 - gaze-down angle (head pitch + iris), measured only: fake sequences of pitch and iris_y.

No alert reads it; these tests pin what is measured and that the rest of block 8 is untouched.
"""

from dataclasses import replace

import numpy as np
import pytest

from edge_agent.analysis.distraction import DistractionAnalyzer, DistractionConfig
from edge_agent.config import load_thresholds
from edge_agent.perception.features import IRIS, FrameFeatures, iris_offsets

FPS = 30
DT = 1.0 / FPS
USUAL = -0.07  # iris_y of this driver when looking at the road


def feats(t, pitch=0.0, iris=USUAL, yaw=0.0):
    f = FrameFeatures(round(t * FPS), t, True, 1.0, ear=0.3, mar=0.05, pitch=pitch, yaw=yaw, roll=0.0)
    return replace(f, iris_y=iris)


def run(a, t0, seconds, shut=False, moving=True, **kw):
    states = []
    for i in range(round(seconds * FPS)):
        states.append(a.update(feats(t0 + i * DT, **kw), None, moving, eyes_shut=shut))
    return states, t0 + round(seconds * FPS) * DT


def calibrated(**kw):
    a = DistractionAnalyzer(
        DistractionConfig(baseline_calibrate_s=0.0, baseline_recalibrate_s=0.0, baseline_adapt=False, **kw)
    )
    states, t = run(a, 0.0, 6.0)  # gaze_calibrate_s of looking at the road
    assert states[0].gaze_down_deg is None and states[-1].gaze_down_deg == pytest.approx(0.0, abs=1e-6)
    return a, t


def test_eyes_down_with_a_still_head_is_measured_but_never_off_road():
    a, t = calibrated()
    states, _ = run(a, t, 3.0, iris=USUAL + 0.13)  # the eyes drop, the head does not move
    assert states[-1].gaze_down_deg == pytest.approx(13.0, abs=0.01)
    assert states[-1].gaze_down_duration == pytest.approx(3.0, abs=2 * DT)
    assert not any(s.off_road for s in states)  # measured only: the off-road rule does not read it


def test_head_and_eyes_add_up():
    a, t = calibrated()
    below, t = run(a, t, 1.0, pitch=5.0, iris=USUAL + 0.05)  # 5 deg + 5 deg: under the 12 deg limit
    assert below[-1].gaze_down_deg == pytest.approx(10.0, abs=0.01) and below[-1].gaze_down_duration == 0.0
    over, _ = run(a, t, 1.0, pitch=8.0, iris=USUAL + 0.05)
    assert over[-1].gaze_down_deg == pytest.approx(13.0, abs=0.01) and over[-1].gaze_down_duration > 0.9


def test_a_look_back_at_the_road_ends_it_and_a_blink_does_not():
    a, t = calibrated()
    _, t = run(a, t, 1.0, iris=USUAL + 0.15)
    _, t = run(a, t, 0.2, iris=USUAL + 0.15, shut=True)  # a blink: no iris to see, bridged
    states, t = run(a, t, 1.0, iris=USUAL + 0.15)
    assert states[-1].gaze_down_duration == pytest.approx(2.2, abs=2 * DT)
    states, _ = run(a, t, 1.0)  # back on the road for longer than on_road_confirm_s
    assert states[-1].gaze_down_duration == 0.0


def test_shut_eyes_are_not_a_look_down():
    a, t = calibrated()
    states, _ = run(a, t, 4.0, iris=USUAL + 0.15, shut=True)  # closed lids: the iris landmark is a guess
    assert all(s.gaze_down_deg is None and s.gaze_down_duration == 0.0 for s in states)


def test_usual_iris_follows_the_road_but_not_a_look_down():
    a = DistractionAnalyzer(DistractionConfig(baseline_calibrate_s=0.0, baseline_recalibrate_s=0.0))
    _, t = run(a, 0.0, 6.0)
    _, t = run(a, t, 60.0, iris=USUAL + 0.03)  # the driver settles a little lower: on road, learnt
    assert a.baseline_iris == pytest.approx(USUAL + 0.03, abs=0.01)
    _, t = run(a, t, 60.0, iris=USUAL + 0.20)  # a long look down must not become the usual value
    assert a.baseline_iris == pytest.approx(USUAL + 0.03, abs=0.01)


def test_off_and_missing_iris_measure_nothing():
    a = DistractionAnalyzer(DistractionConfig(baseline_calibrate_s=0.0, baseline_recalibrate_s=0.0, gaze_down_deg=0.0))
    states, _ = run(a, 0.0, 8.0, iris=USUAL + 0.3)
    assert all(s.gaze_down_deg is None and s.gaze_down_duration == 0.0 for s in states)
    b, t = calibrated()
    states, _ = run(b, t, 2.0, iris=None)  # 468-point model, or no blendshape model on this build
    assert all(s.gaze_down_deg is None for s in states)


def test_stopping_the_vehicle_clears_the_look_but_keeps_the_usual_value():
    a, t = calibrated()
    _, t = run(a, t, 3.0, iris=USUAL + 0.15)
    states, t = run(a, t, 1.0, moving=False)
    assert states[-1].gaze_down_duration == 0.0 and a.baseline_iris == pytest.approx(USUAL)
    states, _ = run(a, t, 1.0, iris=USUAL + 0.15)
    assert states[-1].gaze_down_duration == pytest.approx(1.0, abs=2 * DT)


def test_feature_extractor_gives_the_mean_iris_offset_of_both_eyes():
    points = np.zeros((478, 3))
    for side, (iris, outer, inner) in IRIS.items():
        x0 = 100.0 if side == "l" else 300.0
        points[outer, :2], points[inner, :2] = (x0, 200.0), (x0 + 40.0, 200.0)
        points[iris, :2] = (x0 + 20.0, 204.0)  # 4 px below a 40 px wide eye
    off = iris_offsets(points)
    assert off["iris_y_l"] == pytest.approx(0.1) and off["iris_y_r"] == pytest.approx(0.1)
    assert iris_offsets(points[:468]) == {}  # no iris landmarks


def test_thresholds_file_has_the_gaze_keys_and_no_rule_reads_them():
    cfg = DistractionConfig.from_dict(load_thresholds()["distraction"])
    assert cfg.gaze_iris_gain > 0 and cfg.gaze_down_deg > 0 and cfg.gaze_calibrate_s > 0
    risk = load_thresholds()["risk"]
    assert "gaze" not in str(risk)  # measured only: the risk engine has no gaze rule


def test_enrolled_road_iris_replaces_the_start_up_calibration():
    # The first seconds of driving are spent looking down: learnt as "usual" without enrollment, not with it.
    learnt = DistractionAnalyzer(
        DistractionConfig(baseline_calibrate_s=0.0, baseline_recalibrate_s=0.0, baseline_adapt=False)
    )
    states, _ = run(learnt, 0.0, 8.0, iris=USUAL + 0.15)
    assert states[-1].gaze_down_deg == pytest.approx(0.0, abs=1e-6) and states[-1].gaze_down_duration == 0.0
    enrolled = DistractionAnalyzer(
        DistractionConfig(baseline_calibrate_s=0.0, baseline_recalibrate_s=0.0, baseline_adapt=False)
    )
    enrolled.set_road_pose(0.0, 0.0, USUAL)
    states, _ = run(enrolled, 0.0, 3.0, iris=USUAL + 0.15)
    assert states[0].gaze_down_deg == pytest.approx(15.0, abs=0.01)  # known from the first frame
    assert states[-1].gaze_down_duration == pytest.approx(3.0, abs=2 * DT)


def test_enrollment_without_iris_keeps_the_start_up_calibration():
    a = DistractionAnalyzer(
        DistractionConfig(baseline_calibrate_s=0.0, baseline_recalibrate_s=0.0, baseline_adapt=False)
    )
    a.set_road_pose(0.0, 0.0)  # 468-point model: the profile has no road_iris_y
    states, _ = run(a, 0.0, 6.0)
    assert a.baseline_iris == pytest.approx(USUAL) and states[0].gaze_down_deg is None
