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
  two, eval/results/benchmark_web.md). The worker scripts need the header as much as index.html. What
  the page loads from other origins (Pyodide and MediaPipe from their CDN) is fetched with CORS or
  carries `Cross-Origin-Resource-Policy: cross-origin`; the API is called with CORS.

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
        rel = Path(os.path.relpath(full_path, str(self.directory)))
        return IMMUTABLE if rel.parts and rel.parts[0] in IMMUTABLE_DIRS else REVALIDATE

    def file_response(
        self, full_path: str | os.PathLike[str], stat_result: os.stat_result, scope: Scope, status_code: int = 200
    ) -> Response:
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
        response.headers.update(ISOLATION_HEADERS)
        if self.is_not_modified(response.headers, request_headers):
            not_modified = NotModifiedResponse(response.headers)
            # A 304 keeps only a few headers; a copy cached before M51 would stay without isolation.
            not_modified.headers.update(ISOLATION_HEADERS)
            return not_modified
        return response


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "static"
    files = precompress(target)
    before, after = sum(f[1] for f in files), sum(f[2] for f in files)
    print(f"{target}: {len(files)} files compressed, {before / 1e6:.1f} MB -> {after / 1e6:.1f} MB")
