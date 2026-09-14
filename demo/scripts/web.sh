#!/usr/bin/env bash
# Serve the web front end against the locally running services.
#
# Optional. The four services must already be up (start-all.sh); this only adds
# a browser view over them, and it makes no authorization decision of its own --
# every verdict it renders came from the MCP server.
#
# Runs in the foreground. Ctrl+C stops it. Nothing else about the demo changes.
#
# Usage: ./scripts/web.sh [--port PORT] [--allow-reset]
set -euo pipefail

# shellcheck source=_common.sh
. "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
require_venv

PORT=8080

while [ $# -gt 0 ]; do
  case "$1" in
    --port)        PORT="$2"; shift 2 ;;
    --allow-reset) export WEB_ALLOW_RESET=1; shift ;;
    -h|--help)     sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

export WEB_PORT="$PORT"

echo "web UI  http://localhost:$PORT"
echo "Ctrl+C to stop."

cd "$DEMO"
exec "$PY" -m refund_demo.web.app
