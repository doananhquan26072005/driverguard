"""Railway entry point: the backend API plus the built dashboard on the same origin.

API routes and the short links (/privacy) are registered first, so they win over the static mount at "/". The files go out
gzip-encoded where the image holds a precompressed copy, and with cache headers (backend/static.py).
"""

from __future__ import annotations

import os

from backend.app import create_app
from backend.static import CachedStaticFiles, add_short_links

app = create_app()
add_short_links(app)
app.mount("/", CachedStaticFiles(directory=os.environ.get("DG_STATIC_DIR", "static"), html=True), name="dashboard")
