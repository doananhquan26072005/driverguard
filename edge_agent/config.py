"""Load thresholds from config/thresholds.yaml."""

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_THRESHOLDS_PATH = PROJECT_ROOT / "config" / "thresholds.yaml"


def load_thresholds(path: str | Path | None = None) -> dict[str, Any]:
    """Return the whole thresholds file as a dict."""
    with open(path or DEFAULT_THRESHOLDS_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def flatten(d: dict[str, Any] | None, prefix: str = "") -> dict[str, Any]:
    """{"eye": {"close_ratio": 0.6}} -> {"eye_close_ratio": 0.6}, to fill flat config dataclasses."""
    out: dict[str, Any] = {}
    for k, v in (d or {}).items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flatten(v, f"{key}_"))
        else:
            out[key] = v
    return out
