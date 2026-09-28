"""Pack the Python the in-browser agent needs (frontend #/live) into one zip for Pyodide.

python tools/build_web_py.py frontend/public/py/edge_agent.zip

Contents: edge_agent/ (no __pycache__) + config/thresholds.yaml + config/scenarios/*.yaml, laid out
as in the repo, so edge_agent.config.PROJECT_ROOT finds the config next to the package.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def files() -> list[Path]:
    out = [p for p in sorted((ROOT / "edge_agent").rglob("*.py")) if "__pycache__" not in p.parts]
    out.append(ROOT / "config" / "thresholds.yaml")
    out += sorted((ROOT / "config" / "scenarios").glob("*.yaml"))
    return out


def build(dest: Path) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    paths = files()
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for p in paths:
            z.write(p, p.relative_to(ROOT).as_posix())
    return len(paths)


if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "frontend" / "public" / "py" / "edge_agent.zip")
    print(f"{target}: {build(target)} files")
