"""thresholds.yaml: unknown keys fail loudly, each threshold lives in one place."""

import pytest
import yaml

from edge_agent.analysis.distraction import DistractionConfig
from edge_agent.analysis.drowsiness import DrowsinessConfig
from edge_agent.capture import CaptureConfig
from edge_agent.config import ConfigError, load_thresholds
from edge_agent.context.vehicle_context import ContextConfig
from edge_agent.decision.alert_manager import AlertConfig
from edge_agent.decision.pipeline import DecisionPipeline
from edge_agent.decision.risk_engine import RiskConfig
from edge_agent.decision.trip_memory import TripMemoryConfig
from edge_agent.hud.server import HudConfig
from edge_agent.io.publisher import PublisherConfig
from edge_agent.perception import PreprocessConfig
from edge_agent.perception.eye_state import EyeStateConfig
from edge_agent.perception.features import FeatureConfig
from edge_agent.perception.landmarks import LandmarkConfig
from edge_agent.perception.phone_detector import PhoneDetectorConfig

CONFIGS = {
    "capture": CaptureConfig,
    "preprocess": PreprocessConfig,
    "landmarks": LandmarkConfig,
    "eye_state": EyeStateConfig,
    "features": FeatureConfig,
    "phone": PhoneDetectorConfig,
    "drowsiness": DrowsinessConfig,
    "distraction": DistractionConfig,
    "context": ContextConfig,
    "risk": RiskConfig,
    "trip_memory": TripMemoryConfig,
    "alert": AlertConfig,
    "hud": HudConfig,
    "publisher": PublisherConfig,
}


def test_shipped_yaml_has_no_unknown_keys():
    th = load_thresholds()
    assert set(th) == set(CONFIGS)
    for section, cls in CONFIGS.items():
        cls.from_dict(th[section])


@pytest.mark.parametrize(
    ("cls", "d", "path"),
    [
        (DrowsinessConfig, {"yawn": {"mar_opn": 0.9}}, "drowsiness.yawn.mar_opn"),
        (RiskConfig, {"drowsy": {"l1": 40, "l3": 90}}, "risk.drowsy.l3"),
        (DistractionConfig, {"baseline": {"tau": 30}}, "distraction.baseline.tau"),
        (PreprocessConfig, {"clahe": {"clip": 3.0}}, "preprocess.clahe.clip"),
        (ContextConfig, {"hight_speed_kmh": 90}, "context.hight_speed_kmh"),
        (AlertConfig, {"cooldown": {1: 60}}, "alert.cooldown"),
        (PhoneDetectorConfig, {"conf_treshold": 0.5}, "phone.conf_treshold"),
    ],
)
def test_unknown_key_raises(cls, d, path):
    with pytest.raises(ConfigError, match=path.replace(".", r"\.")):
        cls.from_dict(d)


def test_misspelled_yawn_threshold_is_not_silently_default():
    with pytest.raises(ConfigError):
        DecisionPipeline({"drowsiness": {"yawn": {"mar_opn": 0.9}}})


@pytest.mark.parametrize(
    ("section", "d", "moved_to"),
    [
        ("distraction", {"min_speed_kmh": 8}, "context.min_speed_kmh"),
        ("distraction", {"assume_moving_when_speed_unknown": False}, "context.assume_moving_when_speed_unknown"),
        ("risk", {"drowsy": {"perclos_min_coverage_s": 20}}, "drowsiness.perclos_min_coverage_s"),
    ],
)
def test_duplicated_keys_were_removed_and_point_to_their_new_place(section, d, moved_to):
    with pytest.raises(ConfigError, match=f"moved to {moved_to}"):
        CONFIGS[section].from_dict(d)


def test_replaced_key_says_what_to_use_instead():
    with pytest.raises(ConfigError, match=r"replaced by risk\.drowsy\.stationary_max_level"):
        RiskConfig.from_dict({"drowsy": {"active_when_stopped": True}})


def test_unknown_section_raises(tmp_path):
    p = tmp_path / "th.yaml"
    p.write_text(yaml.safe_dump({"drowsines": {"perclos_drowsy": 0.2}}))
    with pytest.raises(ConfigError, match="drowsines"):
        load_thresholds(p)


def test_shipped_yaml_is_consistent():
    from edge_agent.config import consistency_errors

    assert consistency_errors(load_thresholds()) == []


def test_inconsistent_local_yaml_stops_startup(tmp_path):
    th = load_thresholds()
    th["drowsiness"]["microsleep_min_s"] = 5.0  # event after the 1.5 s L3 rule
    p = tmp_path / "th.yaml"
    p.write_text(yaml.safe_dump(th))
    with pytest.raises(ConfigError, match="drowsiness.microsleep_min_s"):
        load_thresholds(p)
