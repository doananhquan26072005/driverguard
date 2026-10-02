"""Prepare the end-to-end tests of the web app (frontend/e2e, Playwright).

python tools/e2e_setup.py --db frontend/e2e/.cache/e2e.db --faces frontend/e2e/.cache/faces.json

- packs edge_agent/ for Pyodide (frontend/public/py/edge_agent.zip, as `npm run prepare-live`);
- creates the test accounts in a fresh throwaway database: a driver and a fleet manager;
- writes synthetic faces as landmark numbers (the same generator as tests/test_edge_agent/test_web_bridge.py):
  478 x (x, y, z) pixels of a 640 x 480 frame, eyes open or shut. No image is made or stored.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.manage import main as manage  # noqa: E402
from tests.test_edge_agent.test_web_bridge import synthetic_face  # noqa: E402
from tools.build_web_py import build  # noqa: E402

PASSWORD = "e2e-password-1"  # throwaway database, deleted with the run
USERS = (("an", "driver", "drv-001"), ("quanly", "manager", None))


def faces() -> dict[str, list[float]]:
    return {
        "open": [round(float(v), 2) for v in synthetic_face(ear=0.30).ravel()],
        "shut": [round(float(v), 2) for v in synthetic_face(ear=0.05).ravel()],
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", required=True)
    p.add_argument("--faces", required=True)
    args = p.parse_args(argv)

    n = build(ROOT / "frontend" / "public" / "py" / "edge_agent.zip")
    print(f"[e2e] edge_agent.zip: {n} files")
    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    for old in (db_path, *(db_path.with_name(db_path.name + s) for s in ("-wal", "-shm"))):
        old.unlink(missing_ok=True)  # every run starts from an empty database
    for username, role, driver_id in USERS:
        extra = ["--driver-id", driver_id] if driver_id else []
        manage(["--db", str(db_path), "create-user", username, "--role", role, "--password", PASSWORD, *extra])
    out = Path(args.faces)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(faces()))
    print(f"[e2e] accounts in {db_path}, faces in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
