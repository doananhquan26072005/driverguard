"""Load thresholds from config/thresholds.yaml."""

from pathlib import Path
from typing import Any

import yaml

DEFAULT_THRESHOLDS_PATH = Path(__file__).resolve().parent.parent / "config" / "thresholds.yaml"


def load_thresholds(path: str | Path | None = None) -> dict[str, Any]:
    """Return the whole thresholds file as a dict."""
    with open(path or DEFAULT_THRESHOLDS_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
