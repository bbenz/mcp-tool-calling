#!/usr/bin/env bash
# Start the whole demo in Docker containers.
#
# Optional path. The script-based demo (start-all.sh) is unchanged and is still
# the rehearsed stage path; this is for handing the demo to someone who has
# Docker and nothing else, and for testing the topology the AKS manifests
# deploy.
#
# Usage: ./scripts/compose-up.sh [--no-build] [--timeout SECONDS]
set -euo pipefail

DEMO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE="$DEMO/docker/docker-compose.yml"
BUILD=1
TIMEOUT=180

while [ $# -gt 0 ]; do
  case "$1" in
    --no-build) BUILD=0; shift ;;
    --timeout)  TIMEOUT="$2"; shift 2 ;;
    -h|--help)  sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose not available. Install Docker Desktop and make sure it is running." >&2
  exit 1
fi

cd "$DEMO"

if [ "$BUILD" -eq 1 ]; then
  echo "Building refund-demo:local ..."
  if ! docker compose -f "$COMPOSE" build; then
    echo
    echo "Build failed. If the failure is a TLS or connection error against" >&2
    echo "files.pythonhosted.org, this network blocks the PyPI wheel CDN." >&2
    echo "See docs/DEPLOYMENT.md, 'When the image build cannot reach PyPI'." >&2
    exit 1
  fi
fi

echo "Starting containers ..."
docker compose -f "$COMPOSE" up -d

# Compose returns as soon as the containers are created; healthchecks are what
# actually tell us the services are answering.
expected=5
deadline=$(( $(date +%s) + TIMEOUT ))
while [ "$(date +%s)" -lt "$deadline" ]; do
  healthy=0
  for id in $(docker compose -f "$COMPOSE" ps -q); do
    state="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$id" 2>/dev/null || echo none)"
    [ "$state" = "healthy" ] && healthy=$(( healthy + 1 ))
  done
  if [ "$healthy" -ge "$expected" ]; then
    echo
    echo "All $expected containers healthy."
    echo "  Web UI    http://localhost:8080"
    echo "  devidp    http://localhost:8800/.well-known/openid-configuration"
    echo "  MCP A     http://localhost:8801/.well-known/oauth-protected-resource"
    echo "  MCP B     http://localhost:8802/.well-known/oauth-protected-resource"
    echo
    echo "Stop with: ./scripts/compose-down.sh"
    exit 0
  fi
  sleep 3
done

echo "Timed out waiting for containers to become healthy." >&2
docker compose -f "$COMPOSE" ps
echo "Logs: docker compose -f docker/docker-compose.yml logs" >&2
exit 1
