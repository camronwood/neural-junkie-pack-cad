#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${NJ_CAD_VENV:-${HOME}/.neural-junkie/cad/venv}"
PY="${VENV}/bin/python3"

echo "Setting up CAD sidecar venv at ${VENV}..."
mkdir -p "$(dirname "${VENV}")"
if [[ ! -x "${PY}" ]]; then
  python3 -m venv "${VENV}"
fi
"${PY}" -m pip install --upgrade pip
"${PY}" -m pip install trimesh numpy
echo "OK CAD sidecar ready: ${PY}"
echo "Optional: install OpenSCAD from https://openscad.org and FreeCAD for STEP/2D export."
