"""Static files of the built web app (dashboard, HUD, #/live) with compression and cache headers.

The first visit of #/live downloads tens of MB (ONNX Runtime and MediaPipe wasm, Pyodide, two
models). Two things the plain StaticFiles mount did not do (docs/improvements.md, first-load size):

- Compression: a file with a `.gz` sibling is sent gzip-encoded to clients that accept it. The
  siblings are made once when the image is built (`python -m backend.static <dir>`), at the highest
  level, instead of compressing 14 MB of wasm on every request.
- Cache-Control: files under `assets/` carry a content hash in their name (Vite), so they never
  change: cached for a year, `immutable`. Everything else (index.html, the models, the Python zip)
  keeps its name across releases: `no-cache`, i.e. the browser keeps its copy but asks first, and
  an unchanged file costs a 304 without a body.

- Cross-origin isolation (M51): every file goes out with `Cross-Origin-Opener-Policy: same-origin` and
  `Cross-Origin-Embedder-Policy: require-corp`. Only an isolated page may use SharedArrayBuffer, which
  the phone detector's wasm threads need (one thread without it: 172 ms per run against 91 ms with
  two, eval/results/benchmark_web.md). The worker scripts need the header as much as index.html.
- Content-Security-Policy (M99): the page loads code from its own origin only. Pyodide and MediaPipe
  used to come from a CDN at run time, with no integrity check, into the page that holds the camera
  stream and the login token (audit 08/10, A4 H3); they are now files of the build
  (frontend/scripts/web-runtime.mjs), and the policy keeps it that way: a script from anywhere else,
  an inline script or `eval` is refused by the browser. See CSP below for each directive.

Only files are served here; nothing in this module reads a request body.
"""

from __future__ import annotations

import gzip
import mimetypes
import os
import sys
from pathlib import Path

from starlette.datastructures import Headers
from starlette.responses import FileResponse, Response
from starlette.staticfiles import NotModifiedResponse, StaticFiles
from starlette.types import Scope

IMMUTABLE_DIRS = ("assets",)  # hashed file names (Vite)
IMMUTABLE = "public, max-age=31536000, immutable"
REVALIDATE = "no-cache"
ISOLATION_HEADERS = {
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Embedder-Policy": "require-corp",
}
# What the page may load and talk to (M99). One line per need of the app:
CSP = {
    "default-src": "'self'",
    # the app's own bundles and the three wasm runtimes (Pyodide, MediaPipe, ONNX Runtime); no eval, no inline script
    "script-src": "'self' 'wasm-unsafe-eval'",
    "worker-src": "'self' blob:",  # the phone detector's worker and the wasm thread workers it starts
    "style-src": "'self' 'unsafe-inline'",  # React writes style attributes (sizes of the HUD stage, chart bars)
    "img-src": "'self' data: blob:",  # the icon of index.html is a data: URL
    "font-src": "'self' data:",
    "media-src": "'self' blob: mediastream:",  # the camera stream of #/live, the recorded voice lines
    # the API on this origin; on the driver's own machine: the driving simulator (tools/drive_sim.py), the
    # in-car HUD's agent, a backend on another port while developing. Nowhere else: no frame can be posted away.
    "connect-src": "'self' http://127.0.0.1:* http://localhost:*",
    "object-src": "'none'",
    "base-uri": "'self'",
    "form-action": "'self'",
    "frame-ancestors": "'none'",
}
CSP_HEADER = "; ".join(f"{k} {v}" for k, v in CSP.items())
SECURITY_HEADERS = {**ISOLATION_HEADERS, "Content-Security-Policy": CSP_HEADER}

# Worth compressing: text, wasm, and the model files (ONNX 14 %, .task 13 % smaller). A zip is
# deflated already.
COMPRESS_SUFFIXES = (".js", ".mjs", ".css", ".html", ".svg", ".json", ".wasm", ".onnx", ".task", ".map", ".txt")
MIN_COMPRESS_BYTES = 1024


def precompress(directory: str | Path, level: int = 9) -> list[tuple[Path, int, int]]:
    """Write `<file>.gz` next to every compressible file that gets smaller. Returns (file, bytes, gz bytes)."""
    done = []
    for path in sorted(Path(directory).rglob("*")):
        if not path.is_file() or path.suffix not in COMPRESS_SUFFIXES:
            continue
        raw = path.read_bytes()
        if len(raw) < MIN_COMPRESS_BYTES:
            continue
        packed = gzip.compress(raw, compresslevel=level, mtime=0)
        if len(packed) >= len(raw):
            continue
        gz = path.with_name(path.name + ".gz")
        gz.write_bytes(packed)
        done.append((path, len(raw), len(packed)))
    return done


class CachedStaticFiles(StaticFiles):
    """StaticFiles + precompressed siblings + Cache-Control (see the module doc)."""

    def cache_control(self, full_path: str) -> str:
        """Cache-Control of a file: immutable for the hashed files under assets/, revalidate for the rest."""
        rel = Path(os.path.relpath(full_path, str(self.directory)))
        return IMMUTABLE if rel.parts and rel.parts[0] in IMMUTABLE_DIRS else REVALIDATE

    def file_response(
        self, full_path: str | os.PathLike[str], stat_result: os.stat_result, scope: Scope, status_code: int = 200
    ) -> Response:
        """Serve the file, or its .gz sibling when the client accepts gzip and it is not older,
        with the cache and security headers; a 304 when the client's copy is current."""
        request_headers = Headers(scope=scope)
        full_path = os.fspath(full_path)
        response = FileResponse(full_path, status_code=status_code, stat_result=stat_result)
        gz_path = full_path + ".gz"
        if "gzip" in request_headers.get("accept-encoding", "").lower() and os.path.isfile(gz_path):
            gz_stat = os.stat(gz_path)
            if gz_stat.st_mtime >= stat_result.st_mtime:  # never an older sibling of a replaced file
                media_type = mimetypes.guess_type(full_path)[0] or "application/octet-stream"
                response = FileResponse(gz_path, status_code=status_code, stat_result=gz_stat, media_type=media_type)
                response.headers["Content-Encoding"] = "gzip"
        response.headers["Vary"] = "Accept-Encoding"
        response.headers["Cache-Control"] = self.cache_control(full_path)
        response.headers.update(SECURITY_HEADERS)
        if self.is_not_modified(response.headers, request_headers):
            not_modified = NotModifiedResponse(response.headers)
            # A 304 keeps only a few headers; a copy cached before M51 / M99 would stay without them.
            not_modified.headers.update(SECURITY_HEADERS)
            return not_modified
        return response


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "static"
    files = precompress(target)
    before, after = sum(f[1] for f in files), sum(f[2] for f in files)
    print(f"{target}: {len(files)} files compressed, {before / 1e6:.1f} MB -> {after / 1e6:.1f} MB")
