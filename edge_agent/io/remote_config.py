"""Tuned thresholds from the backend (engineers edit them in the dashboard).

At startup the edge agent fetches the overrides meant for it (GET /api/v1/device/thresholds: the
fleet's version, or the one pinned to this device for a trial) and applies them on top of
config/thresholds.yaml. During the trip it asks again every publisher.config_poll_s, and
`ThresholdReloader` holds a changed version back until the vehicle is parked (M47): thresholds
never change under a driver who is being judged. Keys are dotted paths into the YAML
("risk.drowsy.l1", "alert.cooldown_s.2"). Offline, or if the merged result is not
consistent (edge_agent.config.consistency_errors, the same rules the backend checks
before saving), the local YAML is used unchanged: a bad remote value never breaks the device.
"""

from __future__ import annotations

import copy
import json
import logging
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from edge_agent.config import consistency_errors

log = logging.getLogger("driverguard.remote_config")


def fetch_thresholds(base_url: str, device_key: str, timeout_s: float = 5.0) -> dict[str, float] | None:
    """Overrides from the backend, {} if none were set, None if the backend is unreachable."""
    remote = fetch_remote(base_url, device_key, timeout_s)
    return None if remote is None else remote[1]


def fetch_remote(base_url: str, device_key: str, timeout_s: float = 5.0) -> tuple[int, dict[str, float]] | None:
    """(version, overrides) from the backend: version 0 and {} if none were set; None if it is unreachable.
    The version goes back to the backend with every heartbeat and event (edge_agent/version.py)."""
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
    try:
        version = int(data.get("version") or 0)
    except (TypeError, ValueError):
        version = 0
    return version, {str(k): float(v) for k, v in values.items()}


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


@dataclass(frozen=True)
class Reload:
    """A version taken by `ThresholdReloader.take`. applied False: refused as inconsistent (`problems`),
    the thresholds in use stay as they were."""

    version: int
    thresholds: dict[str, Any]
    applied: bool
    problems: tuple[str, ...] = ()


class ThresholdReloader:
    """Holds a version fetched during the trip until it may be applied: only while parked.

    `offer` is called with every answer of the backend (any thread), `take` once per frame by the
    loop. A version is taken once: applied, or refused when the merged result is inconsistent, in
    which case the same version is not tried again. Going back to an older version, or to "no
    overrides" (version 0), is a change like any other. Pure logic, no network.
    """

    def __init__(self, base: dict[str, Any], version: int = 0) -> None:
        """base: the device's own thresholds.yaml (overrides are always applied on top of it, never on
        top of earlier overrides). version: the one already in use (0 = none, or it was refused)."""
        self._base = base
        self.version = version  # in use, or the last one refused
        self._pending: tuple[int, dict[str, float]] | None = None
        self._lock = threading.Lock()

    def offer(self, version: int, values: dict[str, float]) -> bool:
        """What the backend now says this device should run. True when it differs from the version in use."""
        with self._lock:
            self._pending = (version, dict(values)) if version != self.version else None
            return self._pending is not None

    @property
    def pending(self) -> int | None:
        with self._lock:
            return None if self._pending is None else self._pending[0]

    def take(self, parked: bool) -> Reload | None:
        """The waiting version, once the vehicle is parked; None while driving or when nothing waits."""
        if not parked:
            return None
        with self._lock:
            if self._pending is None:
                return None
            (version, values), self._pending = self._pending, None
            self.version = version
        merged, problems = apply_overrides(self._base, values)
        return Reload(version, merged, not problems, tuple(problems))
