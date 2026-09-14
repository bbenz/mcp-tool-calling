#!/usr/bin/env bash
# Reset the ledger, audit log, and local signing key to a known state.
# Operator-only: scoped to DATA_DIR, refuses to run when AUTH_MODE=entra
# unless ALLOW_RESET=1. Never exposed as an MCP tool.
set -euo pipefail
DEMO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DEMO"
if [ "${1:-}" = "--keep-key" ]; then
  ./.venv/bin/python -m refund_demo.reset --keep-key
else
  ./.venv/bin/python -m refund_demo.reset
fi
