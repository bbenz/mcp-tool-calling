#!/usr/bin/env bash
# Start all four demo services and wait until every one answers /health.
set -euo pipefail
# shellcheck source=_common.sh
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
require_venv
cd "$DEMO"

[ "${1:-}" = "--reset" ] && ./scripts/reset.sh

mkdir -p .local/logs
: > .local/services.pids

start() {
  local name="$1" module="$2"
  "$PY" -m "$module" > ".local/logs/$name.out.log" 2> ".local/logs/$name.err.log" &
  echo "$name $!" >> .local/services.pids
  echo "starting $name (pid $!)"
}

start devidp   refund_demo.devidp.server
start upstream refund_demo.upstream_api.app
start mcp-a    refund_demo.mcp_server.app
start mcp-b    refund_demo.resource_b.app

wait_for() {
  local name="$1" port="$2" deadline=$((SECONDS + 45))
  while [ $SECONDS -lt $deadline ]; do
    if curl -fsS "http://localhost:$port/health" > /dev/null 2>&1; then
      echo "  healthy  $name  http://localhost:$port"; return 0
    fi
    sleep 0.4
  done
  echo "  FAILED   $name - see .local/logs/$name.err.log" >&2
  return 1
}

wait_for devidp 8800
wait_for upstream 8803
wait_for mcp-a 8801
wait_for mcp-b 8802
echo
echo "all services healthy"
