#!/usr/bin/env bash
# Run every check: unit tests, end-to-end tests, and all stage scenarios.
set -euo pipefail
# shellcheck source=_common.sh
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
require_venv
cd "$DEMO"

./scripts/health.sh
echo
echo "== test suite =="
"$PY" -m pytest tests/ -q
echo
echo "== stage scenarios =="
"$PY" -m refund_demo.scenarios run-all
echo
echo "READY"
