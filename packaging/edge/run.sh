#!/usr/bin/env bash
# DriveGuard edge agent: camera + models run here, only metadata JSON goes to the backend.
# Extra arguments go to edge_agent.main, e.g. ./run.sh --scenario config/scenarios/highway_night.yaml
set -euo pipefail
cd "$(dirname "$0")"

[ -x .venv/bin/python ] || { echo "Run ./install.sh first." >&2; exit 1; }
[ -f edge.env ] || { echo "Missing edge.env (copy edge.env.example)." >&2; exit 1; }
set -a; . ./edge.env; set +a
case "${DG_DEVICE_KEY:-}" in dgk_paste*|"") echo "Put your device key in edge.env." >&2; exit 1;; esac

URL="${DG_BACKEND_URL%/}"
HUD="$URL/#/hud"
( sleep 6; { command -v open >/dev/null && open "$HUD"; } || { command -v xdg-open >/dev/null && xdg-open "$HUD"; } || true ) &
echo "[run] HUD: $HUD  (Chrome / Edge; allow local network access if asked)"
exec .venv/bin/python -m edge_agent.main --source 0 \
  --backend "$URL" --device-id "$DG_DEVICE_ID" --hud-origin "$URL" "$@"
