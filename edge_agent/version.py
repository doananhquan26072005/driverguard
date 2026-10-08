"""What is running on this device (M41): app version, thresholds version, model fingerprints.

Sent with every heartbeat and every event, so the backend can tell which vehicles still run an
older thresholds version or another model, and every stored event says under which configuration
it was raised (PRD NFR-6). Numbers and short hex strings only.

- app: APP_VERSION below, bumped by hand with a release.
- thresholds_version: the version of the engineers' overrides fetched from the backend
  (edge_agent/io/remote_config.py); 0 = none applied, the local config/thresholds.yaml alone.
- thresholds_ignored: overrides were fetched but refused (inconsistent, or during the trip a version
  changing a section that needs a restart), so the device runs on other thresholds than the tuned
  version it was given.
- models: the first FINGERPRINT_CHARS hex characters of the SHA-256 of each model file, by the
  thresholds section that uses it (landmarks, eye_state, phone). The device hashes its files at
  start-up; the browser cannot read its model files from Python, so tools/build_web_py.py writes
  the fingerprints of the files it ships into config/build_info.json.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from edge_agent.config import PROJECT_ROOT

APP_VERSION = "3.0.0"
FINGERPRINT_CHARS = 12
BUILD_INFO = PROJECT_ROOT / "config" / "build_info.json"


def fingerprint(path: str | Path) -> str | None:
    """Short SHA-256 of a file, None when it is missing."""
    p = Path(path)
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:FINGERPRINT_CHARS]


def model_fingerprints(models: dict[str, str | Path | None]) -> dict[str, str]:
    """{section: fingerprint} for the model files that exist (a model that is off or missing is left out)."""
    out = {}
    for name, path in models.items():
        fp = fingerprint(path) if path is not None else None
        if fp is not None:
            out[name] = fp
    return out


def bundled_models(path: Path = BUILD_INFO) -> dict[str, str]:
    """Model fingerprints written at build time (the in-browser agent); {} without the file."""
    try:
        models = json.loads(path.read_text(encoding="utf-8")).get("models", {})
    except (OSError, ValueError):
        return {}
    return {str(k): str(v) for k, v in models.items()}


def version_info(
    thresholds_version: int = 0, models: dict[str, str] | None = None, thresholds_ignored: bool = False
) -> dict[str, Any]:
    return {
        "app": APP_VERSION,
        "thresholds_version": int(thresholds_version),
        "thresholds_ignored": bool(thresholds_ignored),
        "models": dict(models or {}),
    }
