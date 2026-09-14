#!/usr/bin/env bash
# Run every check: unit tests, end-to-end tests, and all stage scenarios.
set -euo pipefail
DEMO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DEMO"

./scripts/health.sh
echo
echo "== test suite =="
./.venv/bin/python -m pytest tests/ -q
echo
echo "== stage scenarios =="
./.venv/bin/python -m refund_demo.scenarios run-all
echo
echo "READY"
