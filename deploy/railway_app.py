"""Railway entry point: the backend API plus the built dashboard on the same origin.

API routes are registered first, so they win over the static mount at "/".
"""

from __future__ import annotations

import os

from fastapi.staticfiles import StaticFiles

from backend.app import create_app

app = create_app()
app.mount("/", StaticFiles(directory=os.environ.get("DG_STATIC_DIR", "static"), html=True), name="dashboard")
