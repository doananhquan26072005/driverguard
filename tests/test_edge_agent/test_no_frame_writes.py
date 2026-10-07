"""CLAUDE.md: frames live in RAM only. No code of the agent, of the in-browser agent, or of the tools
may write, encode or record an image (M41). A static scan: a red test here means someone added such
a call; if a debugging tool really needs one, it has to be listed in ALLOWED with the reason."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PYTHON_CALLS = (
    r"\bimwrite\s*\(",  # cv2.imwrite
    r"\bVideoWriter\b",  # cv2.VideoWriter
    r"\bimencode\s*\(",  # cv2.imencode: an image as JPEG / PNG bytes
    r"\bimsave\s*\(",  # matplotlib / skimage
    r"\.savefig\s*\(",  # a plotted frame
    r"\bImage\.fromarray\b",  # PIL, the step before .save()
)
BROWSER_CALLS = (
    r"\btoDataURL\s*\(",  # canvas -> base64 image
    r"\btoBlob\s*\(",  # canvas -> image file
    r"\bMediaRecorder\b",  # records the camera stream
    r"\bcaptureStream\s*\(",
    r"\bImageCapture\b",
    r"\bconvertToBlob\s*\(",  # OffscreenCanvas
)
# path (relative to the repo) -> why it may contain such a call. Empty: nothing does today.
ALLOWED: dict[str, str] = {}


def hits(files, patterns):
    found = []
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        if rel in ALLOWED:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if any(re.search(p, line) for p in patterns):
                found.append(f"{rel}:{number}: {line.strip()}")
    return found


def python_files(folder):
    return [p for p in sorted((ROOT / folder).rglob("*.py")) if "__pycache__" not in p.parts]


def browser_files():
    src = ROOT / "frontend" / "src"
    return [p for p in sorted(src.rglob("*.ts*")) if not p.name.endswith((".test.ts", ".test.tsx"))]


def test_the_agent_never_writes_or_encodes_a_frame():
    assert hits(python_files("edge_agent"), PYTHON_CALLS) == []


def test_the_backend_never_handles_an_image():
    assert hits(python_files("backend"), PYTHON_CALLS) == []


def test_the_tools_do_not_write_frames_either():
    assert hits(python_files("tools"), PYTHON_CALLS) == []


def test_the_browser_code_never_exports_or_records_the_camera():
    files = browser_files()
    assert any(p.parent.name == "live" for p in files)  # the in-browser agent is in the scan
    assert hits(files, BROWSER_CALLS) == []


def test_the_scan_sees_what_it_is_looking_for(tmp_path):
    bad = tmp_path / "bad.py"
    bad.write_text('import cv2\ncv2.imwrite("face.jpg", frame)\nw = cv2.VideoWriter()\n', encoding="utf-8")
    found = [line for p in PYTHON_CALLS for line in bad.read_text().splitlines() if re.search(p, line)]
    assert len(found) == 2
    js = "const url = canvas.toDataURL('image/jpeg'); new MediaRecorder(stream);"
    assert sum(bool(re.search(p, js)) for p in BROWSER_CALLS) == 2
