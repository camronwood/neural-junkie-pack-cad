#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
"${ROOT}/scripts/verify-sidecar-smoke.sh"
echo "OK pack-smoke"
