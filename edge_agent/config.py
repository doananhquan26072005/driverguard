"""Load thresholds from config/thresholds.yaml.

Unknown keys are an error, not a silent fallback to the default: a typo such as
`yawn: {mar_opn: 0.9}` would otherwise leave a safety threshold at its default
without anyone noticing.

Thresholds that only make sense relative to each other (L1 < L2, a microsleep event no
later than the L3 rule, ...) are checked by `consistency_errors`: at startup on the local
YAML, on the engineers' overrides fetched from the backend, and by the backend itself
before it stores a new version.
"""

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_THRESHOLDS_PATH = PROJECT_ROOT / "config" / "thresholds.yaml"

SECTIONS = frozenset(
    {
        "capture",
        "preprocess",
        "landmarks",
        "eye_state",
        "features",
        "enrollment",
        "phone",
        "drowsiness",
        "distraction",
        "context",
        "risk",
        "trip_memory",
        "trip_summary",
        "eval",
        "alert",
        "hud",
        "publisher",
    }
)

# Keys that used to be duplicated: each threshold now lives in exactly one place.
MOVED_KEYS = {
    "distraction.min_speed_kmh": "context.min_speed_kmh",
    "distraction.assume_moving_when_speed_unknown": "context.assume_moving_when_speed_unknown",
    "risk.drowsy.perclos_min_coverage_s": "drowsiness.perclos_min_coverage_s",
}
# Keys replaced by a different setting: the hint says what to use instead.
REPLACED_KEYS = {
    "risk.drowsy.active_when_stopped": "risk.drowsy.stationary_max_level (0 = off while standing still)",
    "risk.distraction.no_face_s": "risk.unavailable.no_face_s (no face now means monitoring unavailable, not L2)",
}


# (a, op, b, why): the value at dotted path a must be `op` the value at b.
CONSISTENCY_RULES: tuple[tuple[str, str, str, str], ...] = (
    ("risk.drowsy.l1", "<", "risk.drowsy.l2", "L1 score below L2 score"),
    ("risk.drowsy.perclos_low", "<", "risk.drowsy.perclos_high", "PERCLOS term ramps up"),
    ("risk.distraction.off_road_high_speed_s", "<=", "risk.distraction.off_road_s", "stricter at high speed"),
    ("risk.blink.normal_min", "<", "risk.blink.normal_max", "normal blink range"),
    ("drowsiness.microsleep_min_s", "<=", "risk.microsleep_l3_s", "microsleep event no later than the L3 rule"),
    ("drowsiness.blink_max_s", "<", "drowsiness.microsleep_min_s", "a blink is shorter than a microsleep"),
    ("drowsiness.perclos_rearm", "<", "drowsiness.perclos_drowsy", "PERCLOS hysteresis"),
    ("drowsiness.perclos_min_coverage_s", "<=", "drowsiness.perclos_window_s", "coverage fits in the window"),
    ("drowsiness.eye.close_ratio", "<", "drowsiness.eye.open_ratio", "eye hysteresis"),
    ("drowsiness.eye.cnn_open", "<", "drowsiness.eye.cnn_closed", "eye CNN hysteresis"),
    ("drowsiness.eye.baseline_min", "<", "drowsiness.eye.baseline_max", "open-eye baseline range"),
    ("drowsiness.microsleep_deep.ear_ratio", "<=", "drowsiness.eye.close_ratio", "deep closure is closed"),
    ("drowsiness.perclos_close_ratio", "<=", "drowsiness.eye.close_ratio", "PERCLOS counts closed, not narrowed eyes"),
    ("drowsiness.eye.cnn_closed", "<=", "drowsiness.microsleep_deep.cnn", "deep closure is closed (CNN)"),
    ("drowsiness.yawn.mar_close", "<", "drowsiness.yawn.mar_open", "yawn hysteresis"),
    ("drowsiness.yawn.enrolled_close_above", "<", "drowsiness.yawn.enrolled_open_above", "enrolled yawn hysteresis"),
    ("enrollment.closed_ear_ratio", "<=", "drowsiness.eye.close_ratio", "enrolled shut eyes read as closed"),
    ("drowsiness.nod.min_s", "<", "drowsiness.nod.max_s", "nod duration range"),
    ("drowsiness.slow_blink.time_frac_low", "<", "drowsiness.slow_blink.time_frac_high", "blink time ramps up"),
    ("drowsiness.slow_blink.reopen_ratio_low", "<", "drowsiness.slow_blink.reopen_ratio_high", "reopen ramps up"),
    ("drowsiness.nod.return_deg", "<", "drowsiness.nod.pitch_down_deg", "nod hysteresis"),
    ("context.min_speed_kmh", "<", "context.high_speed_kmh", "moving before high speed"),
    ("context.stationary_kmh", "<=", "context.min_speed_kmh", "standing still is not moving"),
)
_OPS = {"<": lambda a, b: a < b, "<=": lambda a, b: a <= b}


class ConfigError(ValueError):
    """thresholds.yaml contains a key no module reads, or values that contradict each other."""


def load_thresholds(path: str | Path | None = None) -> dict[str, Any]:
    """Return the whole thresholds file as a dict. Unknown sections / inconsistent values raise ConfigError."""
    with open(path or DEFAULT_THRESHOLDS_PATH, encoding="utf-8") as f:
        th = yaml.safe_load(f) or {}
    unknown = sorted(set(th) - SECTIONS)
    if unknown:
        raise ConfigError(f"thresholds: unknown section(s) {', '.join(unknown)}")
    errors = consistency_errors(th)
    if errors:
        raise ConfigError("thresholds: " + "; ".join(errors))
    return th


def lookup(th: dict[str, Any], dotted: str) -> Any:
    """th["a"]["b"] for "a.b", None when missing."""
    node: Any = th
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def consistency_errors(th: dict[str, Any]) -> list[str]:
    """Rules of CONSISTENCY_RULES broken by `th` (pairs with a missing value are skipped)."""
    errors = []
    for a, op, b, why in CONSISTENCY_RULES:
        va, vb = lookup(th, a), lookup(th, b)
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)) and not _OPS[op](va, vb):
            errors.append(f"{a} ({va}) must be {op} {b} ({vb}): {why}")
    return errors


def flatten(d: dict[str, Any] | None, prefix: str = "", sep: str = "_") -> dict[str, Any]:
    """{"eye": {"close_ratio": 0.6}} -> {"eye_close_ratio": 0.6}, to fill flat config dataclasses."""
    out: dict[str, Any] = {}
    for k, v in (d or {}).items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flatten(v, f"{key}{sep}", sep))
        else:
            out[key] = v
    return out


def check_keys(section: str, keys: dict[str, str], known: Any) -> None:
    """Raise ConfigError for keys not in `known`. `keys` maps field name -> dotted path for the message."""
    unknown = [path for key, path in keys.items() if key not in known]
    if not unknown:
        return
    parts = []
    for path in unknown:
        full = f"{section}.{path}"
        if full in MOVED_KEYS:
            hint = f" (moved to {MOVED_KEYS[full]})"
        elif full in REPLACED_KEYS:
            hint = f" (replaced by {REPLACED_KEYS[full]})"
        else:
            hint = ""
        parts.append(full + hint)
    raise ConfigError(f"thresholds: unknown key(s) {', '.join(parts)}")


def config_from_dict(cls: Any, d: dict[str, Any] | None, section: str) -> Any:
    """Build a flat config dataclass from a (possibly nested) YAML section, rejecting unknown keys."""
    flat = flatten(d)
    dotted = flatten(d, sep=".")  # same order as `flat`
    check_keys(section, dict(zip(flat, dotted, strict=True)), cls.__dataclass_fields__)
    return cls(**flat)
