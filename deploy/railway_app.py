"""Railway entry point: the backend API plus the built dashboard on the same origin.

API routes are registered first, so they win over the static mount at "/". The files go out
gzip-encoded where the image holds a precompressed copy, and with cache headers (backend/static.py).
"""

from __future__ import annotations

import os

from backend.app import create_app
from backend.static import CachedStaticFiles

app = create_app()
app.mount("/", CachedStaticFiles(directory=os.environ.get("DG_STATIC_DIR", "static"), html=True), name="dashboard")
