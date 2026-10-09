"""M85: every threshold lives in config/thresholds.yaml, and a new one written into the code fails here.

Four guards (audit 08/10: A1 L1, A2 L5, A3 L4, A4 M7, A5 M6, X5, X8):
- a config dataclass built without arguments equals the one built from the YAML, and every field of
  it has a line in the YAML (a deleted line can no longer change behaviour in silence);
- constructor defaults that repeat a YAML value equal it;
- no numeric literal in edge_agent/ outside the config dataclasses, except the ones listed below with
  the reason each is a definition and not a threshold;
- the pages keep no number of their own: frontend/src/lib/defaults.gen.json is thresholds.yaml, and
  no SCREAMING_CASE numeric constant or `?? number` fallback exists outside the list below.
Then the keys moved in this milestone are checked to be the ones the code reads.
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import json
import re
from dataclasses import replace

import numpy as np
import pytest

from edge_agent.analysis.drowsiness.common import RollingWindow
from edge_agent.capture.frame_source import Frame
from edge_agent.config import PROJECT_ROOT, consistency_errors, flatten, load_thresholds, lookup
from edge_agent.context.can_sim import CanSimulator, ExternalVehicle
from edge_agent.decision.alert_manager import REPEATED_L1, AlertConfig, AlertManager
from edge_agent.decision.risk_engine import RiskAssessment, RiskConfig, RiskEngine, RuleHit
from edge_agent.decision.trip_summary import TripCollector
from edge_agent.hud.server import HudConfig, HudState, hud_display
from edge_agent.perception.enrollment import DriverEnrollment
from edge_agent.perception.preprocess import PreprocessConfig, Preprocessor
from edge_agent.web.bridge import WebAgent, web_thresholds
from tests.test_edge_agent.test_config_strict import CONFIGS
from tests.test_edge_agent.test_decision import C0, D0, X0
from tools.web_defaults import DEST, render

TH = load_thresholds()

# ---------------------------------------------------------------- defaults = YAML


def _plain(value):
    """Lists and tuples compare alike (a YAML list fills a tuple field)."""
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    return tuple(_plain(v) for v in value) if isinstance(value, (list, tuple)) else value


@pytest.mark.parametrize("section", sorted(CONFIGS))
def test_a_config_without_arguments_is_the_yaml(section):
    """The four defaults the audit found apart (eye_state.low_light_brightness 60 against 0, ...)."""
    cls = CONFIGS[section]
    assert _plain(dataclasses.asdict(cls())) == _plain(dataclasses.asdict(cls.from_dict(TH[section])))


@pytest.mark.parametrize("section", sorted(CONFIGS))
def test_every_config_field_has_a_line_in_the_yaml(section):
    """A key missing from the YAML takes the dataclass default without a word (config_from_dict only
    refuses unknown keys): so none may be missing."""
    written = flatten(TH[section])
    for nested in ("rise_confirm_s", "cooldown_s", "night_hours", "dim_hours"):  # kept as one value, not flattened
        if nested in TH[section]:
            written[nested] = TH[section][nested]
    missing = [f.name for f in dataclasses.fields(CONFIGS[section]) if f.name not in written]
    assert missing == []


# Constructor arguments that repeat a YAML value (tests build these objects alone): (callable,
# argument, dotted YAML path).
MIRRORED_DEFAULTS = [
    (TripCollector.__init__, "tired_score", "risk.drowsy.l1"),
    (TripCollector.__init__, "score_l2", "risk.drowsy.l2"),
    (TripCollector.__init__, "long_drive_s", "context.long_drive_s"),
    (TripCollector.__init__, "bin_s", "trip_memory.bin_s"),
    (DriverEnrollment.__init__, "ear_min", "drowsiness.eye.baseline_min"),
    (DriverEnrollment.__init__, "ear_max", "drowsiness.eye.baseline_max"),
    (DriverEnrollment.__init__, "road_max_deg", "distraction.baseline.calibrate_max_deg"),
    (CanSimulator.__init__, "moving_kmh", "context.min_speed_kmh"),
    (ExternalVehicle.__init__, "moving_kmh", "context.min_speed_kmh"),
    (ExternalVehicle.__init__, "stale_s", "context.vehicle_signal_stale_s"),
    (ExternalVehicle.__init__, "stationary_kmh", "context.stationary_kmh"),
]


@pytest.mark.parametrize(("func", "arg", "path"), MIRRORED_DEFAULTS, ids=lambda v: v if isinstance(v, str) else "")
def test_constructor_defaults_repeat_the_yaml(func, arg, path):
    assert inspect.signature(func).parameters[arg].default == lookup(TH, path)


# ---------------------------------------------------------------- no number in the logic

# Files that are definitions from end to end: MediaPipe landmark indices and the 3D face model, the
# pose solver's numerics (kept equal to OpenCV by test_geometry), OpenCV drawing of the debug window.
DEFINITION_FILES = {"perception/features.py", "perception/geometry.py", "hud/hud.py"}
TRIVIAL = {0, 1, 2, -1}  # identities, halves, indices, the levels L0-L2
SECONDS = {60: "seconds per minute", 3600: "seconds per hour", 86400: "seconds per day"}
EPSILON = {1e-9: "division guard", 1e-6: "division guard", 1e-3: "division guard"}
HTTP = dict.fromkeys((200, 202, 204, 300, 400, 403, 404, 409, 413, 415, 422, 503), "HTTP status")
RGB = {3: "colour channels / the level L3 / (x, y, z)", 255: "8-bit pixel scale"}
SHARED_REASONS = {*SECONDS.values(), *EPSILON.values(), *HTTP.values(), *RGB.values()}

# file -> {literal: why it is not a threshold}. A literal not listed fails the test: move it to
# thresholds.yaml, or add it here with the reason.
ALLOWED: dict[str, dict[float, str]] = {
    "analysis/distraction.py": {10: "percentiles of 'spread' (10th-90th) and the median", 50: "", 90: ""},
    "analysis/drowsiness/brow.py": {50: "median"},
    "analysis/drowsiness/common.py": {9: "SHARE_DIGITS: decimals a share is rounded to, float noise not a threshold"},
    "analysis/drowsiness/eyes.py": {**SECONDS, **EPSILON},
    "analysis/drowsiness/head.py": {50: "median", **EPSILON},
    "analysis/drowsiness/mouth.py": {90: "cos() is taken up to a right angle"},
    "analysis/drowsiness/slow_blink.py": EPSILON,
    "capture/frame_source.py": {
        1000: "a reported FPS at or above this is not a frame rate",
        0.01: "idle sleep of the read loop",
    },
    "context/can_sim.py": {**SECONDS, **RGB, 5: "mirror of context.min_speed_kmh (MIRRORED_DEFAULTS)"},
    "decision/alert_manager.py": RGB,
    "decision/risk_engine.py": {3: "MAX_LEVEL, the scale L0-L3", 100: "MAX_SCORE, the scale 0-100"},
    "decision/trip_summary.py": {
        **SECONDS,
        3: "the level L3",
        90: "drowsy_p90 is the 90th percentile by name",
        40: "mirror of risk.drowsy.l1 (MIRRORED_DEFAULTS)",
        70: "mirror of risk.drowsy.l2",
        7200: "mirror of context.long_drive_s",
    },
    "hud/server.py": {
        **HTTP,
        **RGB,
        1024: "largest request body read",
        8: "queued button presses",
        8765: "default port",
    },
    "io/metadata_guard.py": {16: "shortest string checked for an image signature"},
    "io/publisher.py": {
        **HTTP,
        **RGB,
        64: "event ids remembered for the HUD / plausible thread count",
        0o600: "OWNER_ONLY, the mode of the outbox file",
        100: "the score scale 0-100",
        600000: "largest plausible loop timing, ms",
        100000: "largest plausible count in a perf record",
        10000000: "largest plausible count in a perf record",
    },
    "main.py": {
        5: "--status-every default",
        8765: "--hud-port default",
        8: "characters of an id printed",
        0.5: "wake-up of the read wait",
        255: "key code mask",
        27: "Esc",
    },  # fmt: skip
    "perception/enrollment.py": {
        10: "percentiles of 'spread' (10th-90th)",
        90: "",
        0.18: "mirror of drowsiness.eye.baseline_min (MIRRORED_DEFAULTS)",
        0.42: "mirror of drowsiness.eye.baseline_max",
        45: "mirror of distraction.baseline.calibrate_max_deg",
    },
    "perception/eye_state.py": {33: "MediaPipe landmark index", 133: "", 263: "", 362: "", **RGB},
    "perception/landmarks.py": {
        **dict.fromkeys((10, 33, 129, 133, 168, 234, 263, 358, 362, 454), "MediaPipe landmark index"),
        **EPSILON,
        1000: "ms per second",
    },
    "perception/phone_detector.py": {
        **RGB,
        **EPSILON,
        114: "YOLO letterbox padding colour",
        4: "box coordinates",
        0.5: "wake-up of the worker's wait",
        1000: "ms per second",
    },  # fmt: skip
    "perception/preprocess.py": {**RGB, 4: "BGRA channels"},
    "perception/quality.py": {**RGB, **EPSILON, 4: "centre weight of the Laplacian"},
    "runtime.py": RGB,
    "version.py": {12: "characters of a model fingerprint", 20: "1 << 20: file read chunk"},
    "web/bridge.py": {478: "MediaPipe landmark count", **RGB, 128: "neutral brightness when the page sends none"},
}


def _config_defaults(tree: ast.AST) -> set[int]:
    """ids of the nodes inside `class ...Config:` field lines (those are checked against the YAML above)."""
    skip: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name.endswith("Config"):
            for stmt in node.body:
                if isinstance(stmt, ast.AnnAssign):
                    skip |= {id(n) for n in ast.walk(stmt)}
    return skip


def numeric_literals(source: str) -> list[tuple[int, float]]:
    """(line, value) of every int / float literal that is not trivial and not a config field default."""
    tree = ast.parse(source)
    skip = _config_defaults(tree)
    return sorted(
        (node.lineno, node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and type(node.value) in (int, float)
        and id(node) not in skip
        and node.value not in TRIVIAL
    )


def test_no_number_in_the_logic_outside_thresholds_yaml():
    root = PROJECT_ROOT / "edge_agent"
    unknown = []
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        if rel in DEFINITION_FILES:
            continue
        allowed = ALLOWED.get(rel, {})
        unknown += [
            f"edge_agent/{rel}:{line}: {value}"
            for line, value in numeric_literals(path.read_text(encoding="utf-8"))
            if value not in allowed
        ]
    assert unknown == [], "numbers written into the code: move them to config/thresholds.yaml, or list them in ALLOWED"


def test_the_scan_sees_a_hardcoded_threshold():
    """The guard itself: a threshold in a comparison, in arithmetic and as an argument default is seen;
    a config field default and the trivial values are not."""
    source = (
        "class NodConfig:\n"
        "    bottom_frac: float = 0.15\n"
        "def f(x, limit=0.35):\n"
        "    if x > 1.5:\n"
        "        return x * 0.9 + 0 + 1 + 2\n"
    )
    assert numeric_literals(source) == [(3, 0.35), (4, 1.5), (5, 0.9)]


def test_the_allow_list_has_no_stale_entry():
    """A literal that left the code leaves the list too, or the list would pass it when it comes back.
    (The shared groups - units, guards, HTTP statuses - are given to a file as a whole.)"""
    root = PROJECT_ROOT / "edge_agent"
    stale = []
    for rel, allowed in ALLOWED.items():
        present = {value for _, value in numeric_literals((root / rel).read_text(encoding="utf-8"))}
        stale += [f"{rel}: {v}" for v, why in allowed.items() if v not in present and why not in SHARED_REASONS]
    assert stale == []


# ---------------------------------------------------------------- the pages keep no number

FRONTEND = PROJECT_ROOT / "frontend" / "src"
JS_CONST = re.compile(
    r"^\s*(?:export\s+)?const\s+([A-Z][A-Z0-9_]*)\s*(?::[^=]+)?=\s*(-?[\d_]+(?:\.\d+)?)\s*[;,]?\s*(?://.*)?$", re.M
)
JS_FALLBACK = re.compile(r"\?\?\s*(-?\d+(?:\.\d+)?)\b")
# Layout, refresh rates of the dashboard and sizes of local lists: nothing the agent decides with.
JS_ALLOWED = {
    "dashboard/Dashboard.tsx": {"REFRESH_MS"},
    "dashboard/FleetView.tsx": {"REFRESH_MS"},
    "dashboard/ManagerPages.tsx": {"REFRESH_MS"},
    "dashboard/FatigueChart.tsx": {"HEIGHT", "EVENT_HIT_PX"},
    "dashboard/ThresholdsView.tsx": {"FALSE_ALARM_HIGH"},  # which thresholds the engineers' table highlights
    "hud/HudStage.tsx": {"STAGE_W", "STAGE_H", "WIDE_MIN_W", "TALL_MIN_W", "MIN_RATIO"},
    "hud/demo.ts": {"DEMO_CYCLE_S"},
    "hud/forcedLog.ts": {"FORCED_LOG_MAX"},
    "hud/HudPreview.tsx": {"?? 68", "?? 52"},  # scores of the design preview's sample screens
    "lib/scale.ts": {"MINUTE", "?? 10"},
    # looks per capture.frame_timeout_s, not a time of its own; what a browser lets a closing page send
    "live/agent.ts": {"WATCH_LOOKS", "KEEPALIVE_BUDGET_BYTES"},
    "live/LiveScreen.tsx": {"TECH_WIDTH_PX"},  # layout of the self-view
    "live/selfView.ts": {"MARGIN"},
    "live/tripId.ts": {"RANDOM_BYTES"},
}


def js_numbers(source: str) -> set[str]:
    names = {m.group(1) for m in JS_CONST.finditer(source)}
    return names | {f"?? {m.group(1)}" for m in JS_FALLBACK.finditer(source) if float(m.group(1)) not in (0, 1)}


def test_the_pages_keep_no_numeric_constant_of_their_own():
    unknown = []
    for path in sorted(FRONTEND.rglob("*.ts*")):
        if ".test." in path.name:
            continue
        rel = path.relative_to(FRONTEND).as_posix()
        found = js_numbers(path.read_text(encoding="utf-8"))
        unknown += [f"frontend/src/{rel}: {name}" for name in sorted(found - JS_ALLOWED.get(rel, set()))]
        assert JS_ALLOWED.get(rel, set()) <= found, f"stale entry in JS_ALLOWED for {rel}"
    assert unknown == [], "read it from the agent (HudSnapshot.display, settings()) or from lib/defaults"


def test_the_page_scan_sees_a_copied_threshold():
    source = "const STALE_S = 3; // frozen\nexport const GAIN: number = 0.25;\nconst l2 = trip?.score_l2 ?? 70;\nconst n = x ?? 0;\n"
    assert js_numbers(source) == {"STALE_S", "GAIN", "?? 70"}


def test_the_build_time_defaults_are_the_yaml():
    """frontend/src/lib/defaults.gen.json is generated (tools/web_defaults.py) and checked in."""
    assert DEST.read_text(encoding="utf-8") == render(), "run: python tools/web_defaults.py"


def test_the_screen_gets_its_numbers_with_every_state():
    """X5: the HUD's stale time, repeat rates, loudness and the two rule numbers its eye tile shows."""
    display = hud_display(TH)
    assert display == {
        "poll_s": TH["hud"]["poll_s"],
        "state_timeout_s": TH["hud"]["state_timeout_s"],
        "link_down_failures": TH["hud"]["link_down_failures"],
        "stale_s": TH["hud"]["stale_s"],
        "chime_to_voice_s": TH["hud"]["chime_to_voice_s"],
        "alarm_repeat_s": TH["hud"]["alarm_repeat_s"],
        "presence_repeat_s": TH["hud"]["presence_repeat_s"],
        "gain": [0.0, TH["hud"]["gain"][1], TH["hud"]["gain"][2], TH["hud"]["gain"][3]],
        "feedback_window_s": TH["hud"]["feedback_window_s"],
        "blink_max_s": TH["drowsiness"]["blink_max_s"],
        "microsleep_l3_s": TH["risk"]["microsleep_l3_s"],
        "score_l1": TH["risk"]["drowsy"]["l1"],
        "score_l2": TH["risk"]["drowsy"]["l2"],
    }
    assert HudState(HudConfig.from_dict(TH["hud"]), display).to_json()["display"] == display
    assert "display" not in HudState().to_json()  # built alone (tests): the screen uses its build's


def test_a_tuned_l3_rule_reaches_the_screen():
    """The eye tile turned red at a hand-copied 1.5 s whatever risk.microsleep_l3_s was."""
    th, problems = web_thresholds({"risk.microsleep_l3_s": 2.5})
    assert problems == [] and hud_display(th)["microsleep_l3_s"] == 2.5
    agent = WebAgent("web-an", "trip-1", overrides={"risk.microsleep_l3_s": 2.5})
    assert json.loads(agent.hud_state())["display"]["microsleep_l3_s"] == 2.5


def test_the_page_loop_gets_its_numbers_from_settings():
    s = json.loads(WebAgent("web-an", "trip-1").settings())
    assert s["sample_stride"] == TH["preprocess"]["sample_stride"]
    assert s["eye_blink_missing"] == TH["eye_state"]["web_blink_missing"]
    assert s["vehicle"] == {
        "poll_s": TH["context"]["vehicle_poll_s"],
        "stale_s": TH["context"]["vehicle_signal_stale_s"],
    }
    assert s["capture"]["max_frame_age_s"] == TH["capture"]["web_max_frame_age_s"]


# ---------------------------------------------------------------- the moved keys are the ones read


def test_the_pages_eye_source_is_a_yaml_key():
    assert web_thresholds()[0]["eye_state"]["source"] == TH["eye_state"]["web_source"] == "blendshape"
    th = load_thresholds()
    th["eye_state"]["web_source"] = "cnn"
    assert web_thresholds(base=th)[0]["eye_state"]["source"] == "cnn"


def test_the_ir_test_samples_every_sample_stride_th_pixel():
    """One stride for block 2 and block 6, device and page. A colour image whose every 4th pixel is grey
    reads as infrared at stride 4 and as colour at stride 3."""
    image = np.zeros((48, 48, 3), np.uint8)
    image[..., 0], image[..., 2] = 200, 40
    image[::4, ::4] = 90
    assert Preprocessor(PreprocessConfig(sample_stride=4)).is_ir_image(image)
    assert not Preprocessor(PreprocessConfig(sample_stride=3)).is_ir_image(image)
    assert not Preprocessor(PreprocessConfig(sample_stride=4))(Frame(image[:, 1:], 0, 0.0)).is_ir


def test_the_baseline_recompute_period_is_read():
    w = RollingWindow(60.0, recompute_s=1.0)
    w.add(0.0, 1.0)
    assert w.percentile(50, 0.0) == 1.0
    w.add(0.5, 3.0)
    assert w.percentile(50, 0.5) == 1.0  # cached
    assert w.percentile(50, 1.0) == 2.0
    every_frame = RollingWindow(60.0, recompute_s=0.0)
    every_frame.add(0.0, 1.0)
    every_frame.percentile(50, 0.0)
    every_frame.add(0.5, 3.0)
    assert every_frame.percentile(50, 0.5) == 2.0


@pytest.mark.parametrize(
    ("over", "reason", "level"),
    [
        ({}, "microsleep", 3),
        ({"microsleep_level": 2}, "microsleep", 2),
        ({"microsleep_level": 0}, "microsleep", 0),  # note only, as trend.level / blink.level
        ({"distraction_off_road_level": 1}, "off_road", 1),
        ({"distraction_phone_level": 3}, "phone", 3),
    ],
)
def test_the_level_of_a_rule_is_a_yaml_key(over, reason, level):
    """A3 L4: only trend and blink_rate could be turned down by config."""
    engine = RiskEngine(RiskConfig(**over))
    d = replace(D0, closed_duration=2.0) if reason == "microsleep" else D0
    x = replace(X0, off_road_duration=5.0) if reason == "off_road" else replace(X0, phone_ratio_2s=1.0)
    r = engine.assess(d, X0 if reason == "microsleep" else x, C0)
    assert {h.reason: h.level for h in r.hits}[reason] == level


def test_the_escalated_l1_goes_out_at_l1_repeat_level():
    def third_alert(config: AlertConfig) -> tuple[int, tuple[str, ...]]:
        manager = AlertManager(config)
        hit = RiskAssessment(0.0, 1, (RuleHit(1, "drowsy_score", 45.0),), 45.0, 0.0, (0.0,) * 6)
        alerts, t = [], 0.0
        while len(alerts) < 3 and t < 600.0:
            out = manager.update(replace(hit, t=t))
            if out.new_alert is not None:
                alerts.append(out.new_alert)
            t += 0.5
        return alerts[-1].level, alerts[-1].reasons

    # reminders of every reason, so that a steady L1 reaches its third alert (M92 skips drowsy_score)
    assert third_alert(AlertConfig(remind_skip_reasons=())) == (2, ("drowsy_score", REPEATED_L1))
    assert third_alert(AlertConfig(remind_skip_reasons=(), l1_repeat_level=3)) == (3, ("drowsy_score", REPEATED_L1))


def test_the_fps_smoothing_is_read():
    """The FPS the low-FPS warning is judged on was 0.9 x the last value + 0.1 x the newest, in the code."""
    from edge_agent.runtime import TripRuntime
    from tests.test_edge_agent.test_runtime import FPS, FakeSelector, Recorder, obedient, scenario

    def fps_one_frame_after_slowing(smoothing: float) -> float:
        th = load_thresholds()
        th["hud"]["fps_smoothing"] = smoothing
        th["enrollment"]["enabled"] = False
        rt = TripRuntime(th, "trip-1", CanSimulator(scenario([(0, 60)])), "t", FakeSelector(), emit=Recorder())
        for i in range(30):
            rt.step(obedient(i, i / FPS, "waiting"), False, i / FPS, clock=i / 30)
        rt.step(obedient(30, 30 / FPS, "waiting"), False, 30 / FPS, clock=29 / 30 + 0.1)  # one gap of 10 FPS
        return rt.fps

    assert fps_one_frame_after_slowing(0.9) == pytest.approx(0.9 * 30 + 0.1 * 10, rel=0.01)
    assert fps_one_frame_after_slowing(0.0) == pytest.approx(10.0, rel=0.01)


# ---------------------------------------------------------------- X8: one bin for trend and summary


def test_the_summary_minute_is_trip_memorys_bin():
    """trip_summary cut minutes at a fixed 60 s while trip memory used trip_memory.bin_s."""
    from edge_agent.decision.pipeline import DecisionPipeline

    th = load_thresholds()
    assert DecisionPipeline(th).trip_log.bin_s == th["trip_memory"]["bin_s"]
    th["trip_memory"]["bin_s"] = 30
    assert DecisionPipeline(th).trip_log.bin_s == 30


# ---------------------------------------------------------------- consistency rules (A3 L4)


def _errors(path: str, value: object) -> list[str]:
    th = load_thresholds()
    node = th
    *parents, leaf = path.split(".")
    for part in parents:
        node = node[part]
    node[leaf] = value
    return consistency_errors(th)


@pytest.mark.parametrize(
    ("path", "value", "names"),
    [
        ("context.vehicle_poll_s", 1.0, "context.vehicle_poll_s"),  # read as often as it goes stale
        ("context.vehicle_send_s", 2.0, "context.vehicle_send_s"),
        ("hud.poll_s", 3.0, "hud.poll_s"),
        ("alert.l1_repeat_window_s", 240, "repeated_l1 would never fire"),  # 3 alerts need 2 x 120 s
        ("trip_memory.bin_s", 0, "trip_memory.bin_s"),
        ("trip_memory.trend_window_bins", 0, "trip_memory.trend_window_bins"),
    ],
)
def test_values_that_switch_a_rule_off_by_accident_are_refused(path, value, names):
    errors = _errors(path, value)
    assert len(errors) == 1 and names in errors[0]


def test_escalation_switched_off_on_purpose_is_allowed():
    assert _errors("alert.l1_repeat_count", 0) == []
    assert _errors("alert.l1_repeat_count", 1) == []
