#!/usr/bin/env bash
# Stop the containerised demo.
#
# The shared state volume is kept by default so the ledger survives a restart;
# pass --volumes to drop it, which is the container equivalent of
# ./scripts/reset.sh --new-key.
#
# Usage: ./scripts/compose-down.sh [--volumes]
set -euo pipefail

DEMO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE="$DEMO/docker/docker-compose.yml"
DROP_VOLUMES=0

while [ $# -gt 0 ]; do
  case "$1" in
    --volumes|-v) DROP_VOLUMES=1; shift ;;
    -h|--help)    sed -n '2,8p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

cd "$DEMO"

if [ "$DROP_VOLUMES" -eq 1 ]; then
  echo "Removing containers and the demo-state volume ..."
  exec docker compose -f "$COMPOSE" down --volumes
fi

exec docker compose -f "$COMPOSE" down
