"""M45: the web app's files go out compressed and with cache headers (backend/static.py)."""

import gzip
import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.static import IMMUTABLE, ISOLATION_HEADERS, REVALIDATE, CachedStaticFiles, precompress

JS = b"export const answer = 42;\n" * 200
WASM = bytes(range(256)) * 64  # compressible
ZIP = os.urandom(4096)  # already-packed bytes do not shrink


@pytest.fixture
def site(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "models").mkdir()
    (tmp_path / "py").mkdir()
    (tmp_path / "index.html").write_bytes(b"<!doctype html><title>DriverGuard</title>" + b" " * 2000)
    (tmp_path / "assets" / "index-abc123.js").write_bytes(JS)
    (tmp_path / "assets" / "ort-wasm-def456.wasm").write_bytes(WASM)
    (tmp_path / "models" / "yolov8n.onnx").write_bytes(WASM)
    (tmp_path / "py" / "edge_agent.zip").write_bytes(ZIP)
    (tmp_path / "assets" / "tiny.js").write_bytes(b"1")
    return tmp_path


@pytest.fixture
def client(site):
    precompress(site)
    app = FastAPI()

    @app.get("/api/ping")
    def ping() -> dict[str, bool]:
        return {"ok": True}

    app.mount("/", CachedStaticFiles(directory=site, html=True), name="web")
    return TestClient(app)


def test_precompress_writes_smaller_siblings_only(site):
    done = {p.name: (raw, gz) for p, raw, gz in precompress(site)}
    assert set(done) == {"index.html", "index-abc123.js", "ort-wasm-def456.wasm", "yolov8n.onnx"}
    assert all(gz < raw for raw, gz in done.values())
    assert not (site / "py" / "edge_agent.zip.gz").exists()  # a zip is packed already
    assert not (site / "assets" / "tiny.js.gz").exists()
    assert gzip.decompress((site / "assets" / "index-abc123.js.gz").read_bytes()) == JS


def test_hashed_assets_are_gzipped_and_cached_for_good(client):
    r = client.get("/assets/index-abc123.js")
    assert r.status_code == 200 and r.content == JS  # the client decodes gzip
    assert r.headers["content-encoding"] == "gzip"
    assert r.headers["cache-control"] == IMMUTABLE and "accept-encoding" in r.headers["vary"].lower()
    assert "javascript" in r.headers["content-type"]
    assert int(r.headers["content-length"]) < len(JS)
    w = client.get("/assets/ort-wasm-def456.wasm")
    assert w.headers["content-type"] == "application/wasm" and w.headers["content-encoding"] == "gzip"


def test_client_without_gzip_gets_the_plain_file(client):
    r = client.get("/assets/index-abc123.js", headers={"Accept-Encoding": "identity"})
    assert r.content == JS and "content-encoding" not in r.headers
    assert int(r.headers["content-length"]) == len(JS)


def test_models_and_pages_are_revalidated_and_cost_a_304_when_unchanged(client):
    r = client.get("/models/yolov8n.onnx")
    assert r.content == WASM and r.headers["cache-control"] == REVALIDATE
    again = client.get("/models/yolov8n.onnx", headers={"If-None-Match": r.headers["etag"]})
    assert again.status_code == 304 and again.content == b""
    assert again.headers["cache-control"] == REVALIDATE
    page = client.get("/")
    assert page.status_code == 200 and page.headers["cache-control"] == REVALIDATE
    z = client.get("/py/edge_agent.zip")
    assert z.content == ZIP and "content-encoding" not in z.headers


def test_a_replaced_file_is_not_served_from_its_old_sibling(client, site):
    target = site / "models" / "yolov8n.onnx"
    target.write_bytes(b"new model bytes" * 100)
    stamp = os.stat(target).st_mtime + 10
    os.utime(target, (stamp, stamp))  # newer than its .gz
    r = client.get("/models/yolov8n.onnx")
    assert r.content == b"new model bytes" * 100 and "content-encoding" not in r.headers


def test_api_routes_still_win_and_missing_files_are_404(client):
    assert client.get("/api/ping").json() == {"ok": True}
    assert client.get("/assets/nope.js").status_code == 404
    assert client.get("/../backend/settings.py").status_code == 404


def test_every_file_is_served_cross_origin_isolated(client):
    """M51: the phone detector's wasm threads need an isolated page, and its worker scripts the header too."""
    for path in ("/", "/assets/index-abc123.js", "/assets/ort-wasm-def456.wasm", "/models/yolov8n.onnx"):
        r = client.get(path, headers={"Accept-Encoding": "gzip"})
        assert r.status_code == 200
        for name, value in ISOLATION_HEADERS.items():
            assert r.headers[name] == value, (path, name)
    first = client.get("/models/yolov8n.onnx")
    again = client.get("/models/yolov8n.onnx", headers={"If-None-Match": first.headers["etag"]})
    assert again.status_code == 304 and again.headers["Cross-Origin-Embedder-Policy"] == "require-corp"
    assert "Cross-Origin-Embedder-Policy" not in client.get("/api/ping").headers  # the API is called with CORS


# ---------------------------------------------------------------- M99: code from this origin only


def test_every_file_and_every_304_carries_the_content_security_policy(client):
    from backend.static import CSP_HEADER

    for path in ("/", "/assets/index-abc123.js", "/models/yolov8n.onnx", "/py/edge_agent.zip"):
        r = client.get(path)
        assert r.headers["content-security-policy"] == CSP_HEADER, path
        again = client.get(path, headers={"If-None-Match": r.headers["etag"]})
        assert again.status_code == 304 and again.headers["content-security-policy"] == CSP_HEADER, path


def test_the_policy_lets_in_no_code_but_the_apps_own():
    from backend.static import CSP

    assert CSP["default-src"] == "'self'"
    script = CSP["script-src"].split()
    assert script == ["'self'", "'wasm-unsafe-eval'"]  # no CDN, no 'unsafe-inline', no 'unsafe-eval'
    assert all("http" not in v or k == "connect-src" for k, v in CSP.items())
    # what the page may talk to: its own server and the driver's own machine, nothing on the internet
    assert CSP["connect-src"].split() == ["'self'", "http://127.0.0.1:*", "http://localhost:*"]
    assert CSP["object-src"] == CSP["frame-ancestors"] == "'none'"


def test_the_preview_server_of_the_end_to_end_tests_uses_the_same_policy():
    """frontend/vite.config.ts repeats the header for `vite preview` (what Playwright drives), so the
    end-to-end tests run under the policy the backend sends."""
    import re
    from pathlib import Path

    from backend.static import CSP_HEADER

    config = (Path(__file__).resolve().parents[2] / "frontend" / "vite.config.ts").read_text(encoding="utf-8")
    assert re.search(r'const CSP =\s*"([^"]+)"', config).group(1) == CSP_HEADER


def test_the_page_names_no_cdn():
    """The two runtimes are files of the build (frontend/scripts/web-runtime.mjs); no source file of the
    page may point at a CDN again."""
    from pathlib import Path

    src = Path(__file__).resolve().parents[2] / "frontend" / "src"
    hits = [
        f"{p.relative_to(src)}: {host}"
        for p in src.rglob("*.ts*")
        if ".test." not in p.name
        for host in ("cdn.jsdelivr.net", "unpkg.com", "cdnjs.", "googleapis.com")
        if host in p.read_text(encoding="utf-8")
    ]
    assert hits == []
