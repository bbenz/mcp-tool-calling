#!/usr/bin/env bash
# Show the most recent audit records, formatted for a projector.
#   ./scripts/audit.sh            # last 5
#   ./scripts/audit.sh 10         # last 10
#   ./scripts/audit.sh 3 --raw    # last 3 as raw JSON
set -euo pipefail
# shellcheck source=_common.sh
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
require_venv
cd "$DEMO"

LAST="${1:-5}"
if [ "${2:-}" = "--raw" ]; then
  exec "$PY" -c "import json;from refund_demo import audit;[print(json.dumps(r,indent=2,sort_keys=True)) for r in audit.read_all($LAST)]"
fi
exec "$PY" -m refund_demo.audit_view --last "$LAST"
