"""onnxruntime with its telemetry off (blocks 4 and 5, tools).

onnxruntime ships Microsoft's telemetry client (1DS "Events"), which uploads usage events over
HTTP from a background thread. Nothing but metadata JSON to our own backend may leave the
device (CLAUDE.md), and that thread also aborted the process (libc++ "recursive_mutex lock
failed") when an upload answered while Python was shutting down. Every session is made through
`load_ort()`, which turns it off first: ORT_DISABLE_TELEMETRY must be set before onnxruntime
is imported (its POSIX telemetry starts with the module), disable_telemetry_events() covers the
platform event logger.
"""

from __future__ import annotations

import os
from typing import Any


def load_ort() -> Any:
    """Import onnxruntime (lazily: the in-browser agent has none) with its telemetry off."""
    os.environ.setdefault("ORT_DISABLE_TELEMETRY", "1")
    import onnxruntime as ort

    ort.disable_telemetry_events()
    return ort
