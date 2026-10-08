"""M47: thresholds tuned on the dashboard are reloaded during the trip and applied only while parked
(since M79: during a rest, see test_m79_reload_and_samples.py).
Fake sequences of backend answers and of frames; no network, no video."""

import json

from edge_agent.config import load_thresholds
from edge_agent.context.can_sim import CanSimulator, scenario_from_dict
from edge_agent.io.remote_config import ThresholdReloader
from edge_agent.perception.features import FrameFeatures
from edge_agent.runtime import TripRuntime
from edge_agent.version import version_info
from edge_agent.web.bridge import WebAgent
from tests.test_edge_agent.test_enrollment import obedient
from tests.test_edge_agent.test_runtime import FakeSelector, Recorder, make, run
from tests.test_edge_agent.test_web_bridge import H, W, synthetic_face

FPS = 15
OPEN, SHUT = 0.30, 0.06


def face(t, ear=OPEN):
    return FrameFeatures(round(t * FPS), t, True, 1.0, ear=ear, mar=0.05, pitch=0.0, yaw=0.0, roll=0.0)


# ------------------------------------------------------------------ when (pure)
def test_a_new_version_waits_for_the_vehicle_to_be_parked():
    r = ThresholdReloader(load_thresholds(), version=3)
    assert r.offer(3, {"risk.drowsy.l1": 45.0}) is False and r.pending is None  # already in use
    assert r.offer(4, {"risk.drowsy.l1": 45.0}) is True and r.pending == 4
    assert r.take(parked=False) is None and r.pending == 4  # driving: not now
    got = r.take(parked=True)
    assert got.applied and got.version == 4 and got.thresholds["risk"]["drowsy"]["l1"] == 45.0
    assert r.take(parked=True) is None and r.version == 4  # taken once


def test_only_the_newest_offer_is_kept_and_going_back_is_a_change():
    r = ThresholdReloader(load_thresholds(), version=4)
    r.offer(5, {"risk.drowsy.l1": 45.0})
    r.offer(6, {"risk.drowsy.l1": 50.0})
    assert r.take(True).thresholds["risk"]["drowsy"]["l1"] == 50.0
    assert r.offer(4, {"risk.drowsy.l1": 42.0}) is True  # rolled back on the dashboard
    assert r.take(True).version == 4
    r.offer(7, {"risk.drowsy.l1": 60.0})
    assert r.offer(4, {"risk.drowsy.l1": 42.0}) is False and r.pending is None  # withdrawn before it was applied
    assert r.offer(0, {}) is True  # overrides removed: back to the device's own YAML
    back = r.take(True)
    assert back.applied and back.thresholds == load_thresholds()


def test_overrides_go_on_the_yaml_never_on_earlier_overrides():
    r = ThresholdReloader(load_thresholds(), version=0)
    r.offer(1, {"risk.drowsy.l1": 45.0})
    r.take(True)
    r.offer(2, {"risk.drowsy.l2": 80.0})
    th = r.take(True).thresholds
    assert th["risk"]["drowsy"]["l2"] == 80.0 and th["risk"]["drowsy"]["l1"] == 40  # version 1's l1 is gone


def test_an_inconsistent_version_is_refused_once_and_not_retried():
    r = ThresholdReloader(load_thresholds(), version=2)
    r.offer(3, {"risk.drowsy.l1": 90.0})  # above l2 = 70
    got = r.take(True)
    assert not got.applied and "risk.drowsy.l1" in got.problems[0] and got.thresholds == load_thresholds()
    assert r.offer(3, {"risk.drowsy.l1": 90.0}) is False and r.take(True) is None
    r.offer(4, {"risk.made_up": 1.0})
    assert r.take(True).problems == ("unknown key risk.made_up",)


# ------------------------------------------------------------------ what applying does
def runtime(speeds, enroll=False):
    th = load_thresholds()
    th["enrollment"] = {**th["enrollment"], "enabled": enroll}
    timeline = [{"t": t, "speed_kmh": v} for t, v in speeds]
    can = CanSimulator(scenario_from_dict({"start_clock": "12:00", "timeline": timeline}))
    rec = Recorder()
    return TripRuntime(th, "trip-1", can, "t", FakeSelector(), emit=rec, versions=version_info(3, {})), rec, th


def test_parked_is_a_rest_and_a_trip_not_started_counts_as_parked():
    rt, _, _ = runtime([(0, 0), (130, 0), (135, 60)])
    assert rt.parked  # no frame yet: start of the trip
    rt.step(face(1.0), False, 1.0)
    assert not rt.parked  # standing still, but not for context.rest_after_s (M79)
    rt.step(face(122.0), False, 122.0)
    assert rt.parked
    rt.step(face(140.0), False, 140.0)
    assert not rt.parked


def test_applied_thresholds_change_the_rule_and_the_backend_is_told():
    rt, rec, th = runtime([(0, 60), (28, 60), (30, 0), (160, 0), (162, 60)])
    reloader = ThresholdReloader(th, version=3)
    applied_at, levels = None, {}
    for i in range(185 * FPS):
        t = i / FPS
        if i == 5 * FPS:  # the backend's answer arrives while driving
            reloader.offer(4, {"risk.microsleep_l3_s": 3.0})
        reload = reloader.take(rt.parked)
        if reload is not None:
            rt.apply_thresholds(reload.thresholds, reload.version, refused=not reload.applied)
            applied_at = t
        closed = 10 <= t < 12.5 or 175 <= t < 177.5  # the same 2.5 s closure before and after
        r = rt.step(face(t, SHUT if closed else OPEN), False, t).result
        levels[round(t)] = max(levels.get(round(t), 0), r.risk.level)
    assert 149.0 <= applied_at <= 150.2  # once the stop has lasted context.rest_after_s (120 s), not before
    assert max(levels[s] for s in range(10, 14)) == 3  # old rule: L3 after 1.5 s
    assert max(levels[s] for s in range(175, 179)) < 3  # new rule: 3.0 s, a 2.5 s closure is not L3
    assert ["config_applied"] in rec.reasons()
    applied = next(d for k, d in rec.records if d.get("reasons") == ["config_applied"])
    assert applied["versions"]["thresholds_version"] == 4 and applied["versions"]["thresholds_ignored"] is False
    assert rec.beats[-1]["versions"]["thresholds_version"] == 4
    assert rt.end_trip()["alerts_by_level"]["3"] == 1  # the trip summary went on across the change


def test_a_refused_version_changes_nothing_but_is_reported():
    rt, rec, th = runtime([(0, 0)])
    rt.step(face(0.0), False, 0.0)
    before = rt.decisions.risk.config
    rt.apply_thresholds(th, 9, refused=True)
    assert rt.decisions.risk.config is before
    refused = next(d for k, d in rec.records if d.get("reasons") == ["config_refused"])
    assert refused["versions"]["thresholds_version"] == 3 and refused["versions"]["thresholds_ignored"] is True


def test_the_driver_stays_enrolled_across_a_reload():
    rt, rec, _ = make(speeds=((0, 0), (40, 0), (45, 50)), enroll=True)
    _, t = run(rt, 20)  # parked: the driver agrees and follows the three steps
    assert rt.hud.to_json()["enrollment"]["status"] == "done"
    profile = rt.decisions.enrollment.profile
    th = load_thresholds()
    rt.apply_thresholds({**th, "risk": {**th["risk"], "microsleep_l3_s": 2.0}}, 4)
    assert rt.decisions.enrollment.profile is profile
    assert rt.decisions.risk.config.microsleep_l3_s == 2.0
    r = rt.step(obedient(9999, t + 0.1, "done"), False, t + 0.1).result
    assert r.enrollment.status == "done" and r.drowsiness.ear_open_baseline == profile.ear_open
    assert rec.reasons().count(["driver_enrolled"]) == 1  # not enrolled a second time


# ------------------------------------------------------------------ in the browser
def test_browser_takes_an_offer_while_parked_only():
    agent = WebAgent("web-an", "trip-web-1")  # speed from the page: none yet = parked
    pts = synthetic_face().ravel()
    assert json.loads(agent.settings())["config_poll_s"] == 300.0
    agent.vehicle_signal(60.0, None)
    agent.frame(0.0, 0, W, H, pts, 1, (0.05, 0.05), 12.0, 140.0)
    assert agent.offer_thresholds(7, {"risk.microsleep_l3_s": 3.0}) is True
    agent.vehicle_signal(60.0, None)
    agent.frame(0.1, 1, W, H, pts, 1, (0.05, 0.05), 12.0, 140.0)
    assert agent.runtime.decisions.risk.config.microsleep_l3_s == 1.5  # driving: still the old rule
    agent.vehicle_signal(0.0, None)
    agent.frame(0.2, 2, W, H, pts, 1, (0.05, 0.05), 12.0, 140.0)
    agent.frame(0.3, 3, W, H, pts, 1, (0.05, 0.05), 12.0, 140.0)
    assert agent.runtime.decisions.risk.config.microsleep_l3_s == 1.5  # a stop, not a rest yet (M79)
    agent.frame(121.0, 4, W, H, pts, 1, (0.05, 0.05), 12.0, 140.0)
    agent.frame(121.1, 5, W, H, pts, 1, (0.05, 0.05), 12.0, 140.0)
    assert agent.runtime.decisions.risk.config.microsleep_l3_s == 3.0
    events = json.loads(agent.take_batch())["events"]
    assert [e["reasons"] for e in events if e["reasons"][0].startswith("config")] == [["config_applied"]]
    assert events[-1]["versions"]["thresholds_version"] == 7
