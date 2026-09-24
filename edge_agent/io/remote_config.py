"""Tuned thresholds from the backend (engineers edit them in the dashboard).

At startup the edge agent fetches the latest overrides (GET /api/v1/device/thresholds)
and applies them on top of config/thresholds.yaml. Keys are dotted paths into the YAML
("risk.drowsy.l1", "alert.cooldown_s.2"). Offline, or if the merged result is not
consistent, the local YAML is used unchanged: a bad remote value never breaks the device.
"""

from __future__ import annotations

import copy
import json
import logging
import urllib.error
import urllib.request
from typing import Any

log = logging.getLogger("driverguard.remote_config")


def fetch_thresholds(base_url: str, device_key: str, timeout_s: float = 5.0) -> dict[str, float] | None:
    """Overrides from the backend, {} if none were set, None if the backend is unreachable."""
    req = urllib.request.Request(
        base_url.rstrip("/") + "/api/v1/device/thresholds", headers={"X-Device-Key": device_key}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            data = json.loads(resp.read())
    except (OSError, ValueError) as e:  # URLError / HTTPError / timeout are OSErrors
        log.warning("could not fetch thresholds: %s", e)
        return None
    values = data.get("values") or {}
    return {str(k): float(v) for k, v in values.items()}


def _set(tree: dict[Any, Any], dotted: str, value: float) -> None:
    node = tree
    parts = [int(p) if p.isdigit() else p for p in dotted.split(".")]  # alert.cooldown_s.2 -> int key 2
    for part in parts[:-1]:
        if not isinstance(node.get(part), dict):
            raise KeyError(dotted)
        node = node[part]
    current = node.get(parts[-1])
    # Only an existing numeric leaf may change: never replace a whole section or a flag.
    if isinstance(current, bool) or not isinstance(current, (int, float)):
        raise KeyError(dotted)
    node[parts[-1]] = value


def consistency_errors(th: dict[str, Any]) -> list[str]:
    errors = []
    drowsy = th.get("risk", {}).get("drowsy", {})
    if drowsy.get("l1", 0) >= drowsy.get("l2", 100):
        errors.append("risk.drowsy.l1 must be lower than risk.drowsy.l2")
    dist = th.get("risk", {}).get("distraction", {})
    if dist.get("off_road_high_speed_s", 0) > dist.get("off_road_s", 1e9):
        errors.append("off_road_high_speed_s must not exceed off_road_s")
    return errors


def apply_overrides(th: dict[str, Any], values: dict[str, float]) -> tuple[dict[str, Any], list[str]]:
    """Return (thresholds with overrides applied, problems). On any problem the original is returned."""
    merged = copy.deepcopy(th)
    problems = []
    for key, value in values.items():
        try:
            _set(merged, key, value)
        except KeyError:
            problems.append(f"unknown key {key}")
    problems += consistency_errors(merged)
    if problems:
        return th, problems
    return merged, []
