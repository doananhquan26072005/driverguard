#!/usr/bin/env bash
# Build dist/driveguard-edge-<version>.zip: edge agent + pretrained models + install/run scripts.
# The backend, frontend, tools and datasets are not included.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="${1:-v1}"
NAME="driveguard-edge-$VERSION"
STAGE="$(mktemp -d)/$NAME"
MODELS=(face_landmarker.task open_closed_eye.onnx yolov8n.onnx)

for m in "${MODELS[@]}"; do
  [ -f "$ROOT/models/$m" ] || { echo "missing models/$m (python tools/download_models.py)" >&2; exit 1; }
done

mkdir -p "$STAGE/models" "$STAGE/config/scenarios"
rsync -a --exclude __pycache__ "$ROOT/edge_agent" "$STAGE/"
cp "$ROOT/config/thresholds.yaml" "$STAGE/config/"
cp "$ROOT"/config/scenarios/*.yaml "$STAGE/config/scenarios/"
for m in "${MODELS[@]}"; do cp "$ROOT/models/$m" "$STAGE/models/"; done
cd "$ROOT/packaging/edge"
cp requirements.txt edge.env.example install.sh run.sh install.ps1 run.ps1 README.md "$STAGE/"

mkdir -p "$ROOT/dist"
rm -f "$ROOT/dist/$NAME.zip"
(cd "$(dirname "$STAGE")" && zip -qr "$ROOT/dist/$NAME.zip" "$NAME")
echo "$ROOT/dist/$NAME.zip ($(du -h "$ROOT/dist/$NAME.zip" | cut -f1))"
