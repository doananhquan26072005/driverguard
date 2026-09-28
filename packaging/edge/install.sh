#!/usr/bin/env bash
# DriveGuard edge agent: one-time setup on macOS / Linux.
set -euo pipefail
cd "$(dirname "$0")"

PY=""
for c in python3.12 python3.11 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if (3, 11) <= sys.version_info[:2] <= (3, 12) else 1)'; then
    PY="$c"; break
  fi
done
if [ -z "$PY" ]; then
  echo "Need Python 3.11 or 3.12 (https://www.python.org/downloads/)." >&2
  exit 1
fi

echo "[install] using $($PY --version)"
"$PY" -m venv .venv
.venv/bin/python -m pip install --upgrade pip >/dev/null
.venv/bin/python -m pip install -r requirements.txt
[ -f edge.env ] || cp edge.env.example edge.env
echo "[install] done. Put your device key in edge.env, then run: ./run.sh"
