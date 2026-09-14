#!/usr/bin/env bash
# Reset the ledger and audit log to a known state.
# Operator-only: scoped to the demo data directory, refuses to run when
# AUTH_MODE=entra unless ALLOW_RESET=1. Never exposed as an MCP tool.
#
# The signing key is preserved, so this is safe with the services still up.
# Pass --new-key to rotate it; refused while devidp is listening.
set -euo pipefail
# shellcheck source=_common.sh
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
require_venv
cd "$DEMO"
exec "$PY" -m refund_demo.reset "$@"
