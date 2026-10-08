"""M79 (audit 08/10, A3 M1 and M5): the per-minute fatigue samples go on after "Đổi tài xế" and after
a reload of the thresholds; thresholds are reloaded during a rest only, not at a red light, and trip
memory survives it; a version the running trip cannot take is refused, not reported as applied.
Fake sequences only."""

import pytest

from edge_agent.config import load_thresholds
from edge_agent.context.can_sim import CanSimulator, scenario_from_dict
from edge_agent.decision.pipeline import RELOADABLE
from edge_agent.io.remote_config import ThresholdReloader, apply_overrides
from edge_agent.perception.features import FrameFeatures
from edge_agent.runtime import TripRuntime
from edge_agent.version import version_info
from tests.test_edge_agent.test_runtime import FakeSelector, Recorder

FPS = 5
OPEN, SHUT = 0.30, 0.06


def face(t, ear=OPEN):
    return FrameFeatures(round(t * FPS), t, True, 1.0, ear=ear, mar=0.05, pitch=0.0, yaw=0.0, roll=0.0)


def runtime(speeds):
    th = load_thresholds()
    th["enrollment"] = {**th["enrollment"], "enabled": False}
    timeline = [{"t": t, "speed_kmh": v} for t, v in speeds]
    can = CanSimulator(scenario_from_dict({"start_clock": "12:00", "timeline": timeline}))
    rec = Recorder()
    return TripRuntime(th, "trip-1", can, "t", FakeSelector(), emit=rec, versions=version_info(3, {})), rec, th


def drive(rt, t0, t1, between=None, closed=()):
    """Frames from t0 to t1 (s); between(t) runs before each frame, as the callers' loops do."""
    last = None
    for i in range(round(t0 * FPS), round(t1 * FPS)):
        t = i / FPS
        if between is not None:
            between(t)
        shut = any(a <= t < b for a, b in closed)
        last = rt.step(face(t, SHUT if shut else OPEN), False, t).result
    return last


# ------------------------------------------------------------------ A3 M1: samples go on
def test_an_untouched_hour_sends_one_sample_per_closed_minute():
    rt, rec, _ = runtime([(0, 60)])
    drive(rt, 0, 3600)
    assert rec.kinds().count("sample") == 59


def test_samples_go_on_after_a_driver_change():
    rt, rec, _ = runtime([(0, 60)])
    sent_at = []

    def between(t):
        if t == 1512.0:  # minute 25.2, as in the audit (34 samples before the fix, none for 26 minutes)
            rt.change_driver()
        sent_at.append(rec.kinds().count("sample"))

    drive(rt, 0, 3600, between)
    assert rec.kinds().count("sample") == 59  # 25 of the first driver, 34 of the second
    at = lambda minute: sent_at[round(minute * 60 * FPS)]  # noqa: E731
    assert at(25.1) == 25 and at(26.1) == 25  # the new driver's first minute is still running
    assert at(26.3) == 26 and at(27.3) == 27  # ... and closes one minute after the change


def test_the_new_drivers_first_sample_does_not_carry_the_previous_drivers_alert_level():
    rt, rec, _ = runtime([(0, 60)])

    def between(t):
        if t == 100.0:
            rt.change_driver()

    drive(rt, 0, 170, between, closed=[(70, 73)])  # L3 of the first driver in the minute of the change
    samples = [d for k, d in rec.records if k == "sample"]
    assert [s["max_level"] for s in samples] == [0, 0]  # minute 1 (before the closure), then the new driver's


def test_samples_go_on_after_a_reload_that_restarts_trip_memory():
    rt, rec, th = runtime([(0, 60), (598, 60), (600, 0), (730, 0), (732, 60)])
    drive(rt, 0, 725)
    before = rec.kinds().count("sample")
    assert before == 12 and rt.parked  # 10 minutes driven + the 2 of the stop before it became a rest
    assert rt.apply_thresholds({**th, "trip_memory": {**th["trip_memory"], "trend_window_bins": 10}}, 4)
    drive(rt, 725, 1100)
    assert rec.kinds().count("sample") - before == 6  # before the fix: none until the new count passed 12


# ------------------------------------------------------------------ A3 M5: when, and what survives
def test_a_red_light_does_not_take_new_thresholds_and_keeps_the_microsleep():
    rt, rec, th = runtime([(0, 60), (38, 60), (40, 0), (70, 0), (72, 60)])
    reloader = ThresholdReloader(th, version=3)
    applied = []

    def between(t):
        if t == 5.0:  # the backend's answer arrives while driving
            reloader.offer(4, {"risk.drowsy.l1": 45.0})
        reload = reloader.take(rt.parked)
        if reload is not None:
            applied.append(t)
            rt.apply_thresholds(reload.thresholds, reload.version)

    r = drive(rt, 0, 90, between, closed=[(20, 21.2)])  # a microsleep on the road, then a 30 s red light
    assert applied == [] and reloader.pending == 4
    assert rt.decisions.risk.config.drowsy_l1 == 40
    assert r.trip.last_microsleep_t == pytest.approx(21.2, abs=0.5)  # still counted after the light
    assert r.risk.drowsy_score > 0
    assert ["config_applied"] not in rec.reasons()


def test_a_rest_takes_them_and_trip_memory_goes_on():
    rt, rec, th = runtime([(0, 60), (238, 60), (240, 0), (380, 0), (382, 60)])
    reloader = ThresholdReloader(th, version=3)
    applied = []

    def between(t):
        if t == 5.0:  # the backend's answer arrives while driving
            reloader.offer(4, {"risk.drowsy.l1": 45.0})
        reload = reloader.take(rt.parked)
        if reload is not None:
            applied.append(t)
            assert rt.apply_thresholds(reload.thresholds, reload.version) is True

    memory = rt.decisions.trip
    r = drive(rt, 0, 420, between, closed=[(200, 201.2)])
    assert len(applied) == 1 and 359.0 <= applied[0] <= 361.0  # 120 s after the vehicle stopped
    assert rt.decisions.risk.config.drowsy_l1 == 45.0
    assert rt.decisions.trip is memory  # not rebuilt: its own section did not change
    assert r.trip.last_microsleep_t == pytest.approx(201.2, abs=0.5)  # from before the rest: kept
    assert len(r.trip.minute_scores) == 4  # the minutes driven; the stop was dropped on driving off, as before
    assert rec.kinds().count("sample") == r.trip.bins_completed  # the count went on: no gap, no repeat
    applied_event = next(d for k, d in rec.records if d.get("reasons") == ["config_applied"])
    assert applied_event["versions"]["thresholds_version"] == 4


# ------------------------------------------------------------------ A3 M5: config_applied says what is in use
@pytest.mark.parametrize(
    "key", ["context.long_drive_s", "quality.clear_s", "hud.low_fps_s", "enrollment.reopen_grace_s"]
)
def test_a_version_the_running_trip_cannot_take_is_refused_whole(key):
    rt, rec, th = runtime([(0, 0)])
    rt.step(face(0.0), False, 0.0)
    section, name = key.split(".")
    merged, problems = apply_overrides(th, {key: th[section][name] + 1.0, "risk.drowsy.l1": 45.0})
    assert problems == []
    assert rt.needs_restart(merged) == [section]
    assert rt.apply_thresholds(merged, 9) is False
    assert rt.decisions.risk.config.drowsy_l1 == 40  # nothing of the version is in use, not half of it
    assert ["config_applied"] not in rec.reasons()
    refused = next(d for k, d in rec.records if d.get("reasons") == ["config_refused"])
    assert refused["versions"]["thresholds_version"] == 3 and refused["versions"]["thresholds_ignored"] is True
    assert rec.beats[-1]["versions"]["thresholds_ignored"] is True


def test_the_next_version_without_that_section_is_applied():
    rt, rec, th = runtime([(0, 0)])
    rt.step(face(0.0), False, 0.0)
    bad, _ = apply_overrides(th, {"context.long_drive_s": 3600.0})
    assert rt.apply_thresholds(bad, 9) is False
    good, _ = apply_overrides(th, {"risk.drowsy.l1": 45.0})
    assert rt.needs_restart(good) == [] and rt.apply_thresholds(good, 10) is True
    assert rec.beats[-1]["versions"] == {
        **rec.beats[-1]["versions"],
        "thresholds_version": 10,
        "thresholds_ignored": False,
    }


def test_every_key_the_dashboard_may_tune_is_in_a_reloadable_section():
    from backend.schemas import THRESHOLD_SPECS

    assert {key.split(".")[0] for key in THRESHOLD_SPECS} <= set(RELOADABLE)
