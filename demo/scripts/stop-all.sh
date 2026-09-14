#!/usr/bin/env bash
# Stop the demo services started by start-all.sh.
set -uo pipefail
DEMO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIDS="$DEMO/.local/services.pids"
[ -f "$PIDS" ] || { echo "no recorded services"; exit 0; }
while read -r name pid; do
  if kill -0 "$pid" 2> /dev/null; then kill "$pid" && echo "stopped $name (pid $pid)"; fi
done < "$PIDS"
rm -f "$PIDS"
