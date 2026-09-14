#!/usr/bin/env bash
# Run one named scenario and print its protocol trace.
#   ./scripts/scenario.sh wrong-audience
#   ./scripts/scenario.sh --all        # every scenario, in stage order
#   ./scripts/scenario.sh              # list the available scenarios
set -euo pipefail
# shellcheck source=_common.sh
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
require_venv
cd "$DEMO"

case "${1:-}" in
  --all|-a) exec "$PY" -m refund_demo.scenarios run-all ;;
  "")       exec "$PY" -m refund_demo.scenarios list ;;
  *)        exec "$PY" -m refund_demo.scenarios run "$1" ;;
esac
