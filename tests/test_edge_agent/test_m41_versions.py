"""M41 on the device and in the browser: version info, model fingerprints, the simulated tag."""

import json
import zipfile

import pytest

from backend.schemas import EventBatch
from edge_agent import version as v
from edge_agent.config import load_thresholds
from edge_agent.context.can_sim import CanSimulator, scenario_from_dict
from edge_agent.io import remote_config
from edge_agent.io.publisher import batch_body, build_heartbeat, check_metadata_only
from edge_agent.perception.features import FrameFeatures
from edge_agent.perception.landmarks import DriverSelector
from edge_agent.runtime import TripRuntime
from edge_agent.web.bridge import WebAgent
from tools import build_web_py

FPS = 15


def test_fingerprint_is_a_short_stable_hash(tmp_path):
    a, b = tmp_path / "a.onnx", tmp_path / "b.onnx"
    a.write_bytes(b"model-one")
    b.write_bytes(b"model-two")
    fa = v.fingerprint(a)
    assert fa == v.fingerprint(a) and fa != v.fingerprint(b)
    assert len(fa) == v.FINGERPRINT_CHARS and int(fa, 16) >= 0
    assert v.fingerprint(tmp_path / "missing.onnx") is None
    assert v.model_fingerprints({"phone": a, "eye_state": None, "landmarks": tmp_path / "missing"}) == {"phone": fa}


def test_version_info_passes_the_device_and_backend_checks():
    info = v.version_info(7, {"landmarks": "0123456789ab"}, thresholds_ignored=False)
    assert info == {
        "app": v.APP_VERSION,
        "thresholds_version": 7,
        "thresholds_ignored": False,
        "models": {"landmarks": "0123456789ab"},
    }
    beat = build_heartbeat("monitoring", "trip-1", True, versions=info)
    check_metadata_only(beat)  # the device's own privacy guard
    EventBatch.model_validate({"device_id": "cam-001", "heartbeat": beat})
    assert "versions" not in build_heartbeat("monitoring", "trip-1", True)  # left out when unknown


def runtime(versions=None, simulated=True):
    th = load_thresholds()
    th["enrollment"] = {**th["enrollment"], "enabled": False}
    can = CanSimulator(scenario_from_dict({"start_clock": "15:00", "timeline": [{"t": 0, "speed_kmh": 60}]}))
    records = []
    rt = TripRuntime(
        th,
        "trip-1",
        can,
        "sim",
        DriverSelector(),
        emit=lambda k, d: records.append((k, d)),
        versions=versions,
        simulated=simulated,
    )
    for i in range(20 * FPS):
        t = i / FPS
        yaw = 50.0 if t >= 10 else 0.0
        rt.step(FrameFeatures(i, t, True, 1.0, ear=0.3, mar=0.05, pitch=0.0, yaw=yaw, roll=0.0), False, t)
    return records


def test_every_event_and_heartbeat_says_what_was_running():
    info = v.version_info(4, {"phone": "0123456789ab"})
    records = runtime(info)
    events = [d for k, d in records if k == "event"]
    beats = [d for k, d in records if k == "heartbeat"]
    assert events and beats
    assert all(e["versions"] == info and e["tags"] == ["simulated"] for e in events)
    assert all(b["versions"] == info for b in beats)
    assert [e["reasons"] for e in events if e["type"] != "system"] == [["off_road"]]
    body = batch_body("cam-001", [{"kind": "event", "data": e} for e in events])
    EventBatch.model_validate(body)


def test_a_real_vehicle_signal_would_drop_the_simulated_tag():
    events = [d for k, d in runtime(simulated=False) if k == "event"]
    assert events and all(e["tags"] == [] and "versions" not in e for e in events)


def test_no_event_is_ever_tagged_forced_by_the_agent():
    assert all("forced" not in d.get("tags", []) for k, d in runtime(v.version_info()) if k == "event")


def test_remote_thresholds_come_with_their_version(monkeypatch):
    class Response:
        def __init__(self, body):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return json.dumps(self.body).encode()

    reply = {"version": 12, "values": {"risk.drowsy.l1": 45}}
    monkeypatch.setattr(remote_config.urllib.request, "urlopen", lambda req, timeout: Response(reply))
    assert remote_config.fetch_remote("http://x", "key") == (12, {"risk.drowsy.l1": 45.0})
    assert remote_config.fetch_thresholds("http://x", "key") == {"risk.drowsy.l1": 45.0}  # the old call still works
    reply = {"version": 0, "values": {}}
    assert remote_config.fetch_remote("http://x", "key") == (0, {})

    def down(req, timeout):
        raise OSError("unreachable")

    monkeypatch.setattr(remote_config.urllib.request, "urlopen", down)
    assert remote_config.fetch_remote("http://x", "key") is None


def test_web_agent_reports_the_thresholds_version_it_applied():
    applied = WebAgent("web-an", "trip-1", overrides={"risk.drowsy.l1": 45.0}, thresholds_version=9)
    assert applied.versions["thresholds_version"] == 9 and applied.versions["thresholds_ignored"] is False
    plain = WebAgent("web-an", "trip-1", thresholds_version=9)  # nothing to apply: the local YAML
    assert plain.versions["thresholds_version"] == 0
    refused = WebAgent("web-an", "trip-1", overrides={"risk.drowsy.l1": 99.0}, thresholds_version=9)  # L1 above L2
    assert refused.problems and refused.versions["thresholds_version"] == 0
    assert refused.versions["thresholds_ignored"] is True
    refused.idle(0.0)
    assert json.loads(refused.take_heartbeat())["heartbeat"]["versions"]["thresholds_ignored"] is True


def test_web_bundle_carries_the_fingerprints_of_its_models(tmp_path, monkeypatch):
    model = tmp_path / "face_landmarker.task"
    model.write_bytes(b"landmarks")
    monkeypatch.setattr(build_web_py, "WEB_MODELS", {"landmarks": model, "phone": tmp_path / "missing.onnx"})
    dest = tmp_path / "edge_agent.zip"
    build_web_py.build(dest)
    with zipfile.ZipFile(dest) as z:
        info = json.loads(z.read("config/build_info.json"))
        assert "edge_agent/version.py" in z.namelist()
    assert info == {"models": {"landmarks": v.fingerprint(model)}}  # a missing model is left out, not invented
    path = tmp_path / "build_info.json"
    path.write_text(json.dumps(info), encoding="utf-8")
    assert v.bundled_models(path) == info["models"]
    assert v.bundled_models(tmp_path / "none.json") == {}


@pytest.mark.parametrize("name", ["landmarks", "eye_state", "phone"])
def test_model_names_are_thresholds_sections(name):
    assert name in load_thresholds()
