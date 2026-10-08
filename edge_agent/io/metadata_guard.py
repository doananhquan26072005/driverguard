"""Metadata-only guard shared by the device, the in-browser agent and the backend (M84).

One list of forbidden words and one scanner, so the three places that refuse image-like
content cannot drift apart:
- edge_agent/io/publisher.py `check_metadata_only`: before a record enters the device's outbox
- edge_agent/web/bridge.py `WebAgent._queue`: before a record is handed to the page to be sent
- backend/schemas.py `EventBatch.reject_image_data`: on the raw JSON of every batch (HTTP 422)

Standard library only: the backend imports it without the rest of the agent.
"""

from __future__ import annotations

import re
from typing import Any

# Substrings of a (lowercased) field name. A new metadata field must not contain any of them:
# "total", not "frame" (see publisher.PERF_STAGES).
FORBIDDEN_KEY_PARTS = (
    "image",
    "img",
    "frame",
    "photo",
    "picture",
    "snapshot",
    "thumbnail",
    "jpeg",
    "jpg",
    "png",
    "face_crop",
    "crop",
    "base64",
    "b64",
    "video",
    "blob",
)
DATA_URI = re.compile(r"data:[a-z]+/[a-z0-9.+-]+;base64,", re.IGNORECASE)
IMAGE_SIGNATURES = ("/9j/", "iVBORw0KGgo", "R0lGOD", "UklGR", "Qk0", "SUkq", "TU0AK")  # jpeg png gif webp bmp tiff
BASE64_RUN = re.compile(r"[A-Za-z0-9+/_-]{64,}={0,2}")


def find_image_data(obj: Any, path: str = "$") -> str | None:
    """Return a description of the first image-like content found in a JSON-like value, else None."""
    if isinstance(obj, (bytes, bytearray, memoryview)) or hasattr(obj, "__array__"):
        return f"{path}: binary / array data"
    if isinstance(obj, dict):
        for key, value in obj.items():
            k = str(key).lower()
            if any(part in k for part in FORBIDDEN_KEY_PARTS):
                return f"{path}.{key}: forbidden field name"
            found = find_image_data(value, f"{path}.{key}")
            if found:
                return found
        return None
    if isinstance(obj, (list, tuple)):
        for i, value in enumerate(obj):
            found = find_image_data(value, f"{path}[{i}]")
            if found:
                return found
        return None
    if isinstance(obj, str):
        if ";base64," in obj or DATA_URI.search(obj):
            return f"{path}: data URI"
        stripped = obj.strip()
        if len(stripped) >= 16 and stripped.startswith(IMAGE_SIGNATURES):
            return f"{path}: image signature"
        if BASE64_RUN.search(obj):
            return f"{path}: base64-like data"
    return None
