#!/usr/bin/env bash
# Smoke-test CAD sidecar routes in dry-run mode (no OpenSCAD/FreeCAD required).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HUB="${ROOT}/assets/hub"
PORT="${NJ_CAD_SMOKE_PORT:-18793}"
export NJ_PACK_ID=cad
export NJ_PACK_DIR="${ROOT}"
export NJ_PACK_SETTINGS_JSON='{"cad_sidecar_dry_run":true,"cad_artifacts_dir":"'"${TMPDIR:-/tmp}"'/nj-cad-smoke"}'

python3 "${HUB}/server.py" --port "${PORT}" &
PID=$!
cleanup() { kill "${PID}" 2>/dev/null || true; }
trap cleanup EXIT

for _ in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:${PORT}/health" >/dev/null; then
    break
  fi
  sleep 0.2
done

curl -sf "http://127.0.0.1:${PORT}/health" | grep -q '"ok"'
curl -sf "http://127.0.0.1:${PORT}/api/cad/status" | grep -q '"ok"'

FIXTURE="${ROOT}/scenarios/fixtures/minimal-scad/cube.scad"
curl -sf -X POST "http://127.0.0.1:${PORT}/api/cad/render" \
  -H 'Content-Type: application/json' \
  -d "{\"path\":\"${FIXTURE}\",\"params\":{\"size\":\"20\"}}" | grep -q 'content_base64'

curl -sf -X POST "http://127.0.0.1:${PORT}/api/cad/printability" \
  -H 'Content-Type: application/json' \
  -d '{"stl_path":"dry-run"}' | grep -q 'overhang'

curl -sf -X POST "http://127.0.0.1:${PORT}/api/cad/geometry/repair" \
  -H 'Content-Type: application/json' \
  -d '{"stl_path":"dry-run"}' | grep -q 'repaired'

curl -sf -X POST "http://127.0.0.1:${PORT}/api/cad/gcode/sanity" \
  -H 'Content-Type: application/json' \
  -d '{"gcode":"; test\nG1 Z0.2 F3000\nM104 S200"}' | grep -q 'ok'

echo "OK sidecar smoke"
