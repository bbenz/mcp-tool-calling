#!/usr/bin/env bash
set -euo pipefail

RESOURCE_GROUP=""
LOCATION=""
ACR_NAME=""
KEY_VAULT_NAME=""
NAME_PREFIX="mcpauthdemo"
TAG="demo"
YES="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --resource-group) RESOURCE_GROUP="$2"; shift 2 ;;
    --location) LOCATION="$2"; shift 2 ;;
    --acr-name) ACR_NAME="$2"; shift 2 ;;
    --key-vault-name) KEY_VAULT_NAME="$2"; shift 2 ;;
    --name-prefix) NAME_PREFIX="$2"; shift 2 ;;
    --tag) TAG="$2"; shift 2 ;;
    --yes) YES="true"; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ "$YES" != "true" ]]; then
  echo "Dry run only. Re-run with --yes to execute Azure CLI commands."
  exit 0
fi

if [[ -z "$RESOURCE_GROUP" || -z "$LOCATION" || -z "$ACR_NAME" || -z "$KEY_VAULT_NAME" ]]; then
  echo "Missing required --resource-group, --location, --acr-name, or --key-vault-name." >&2
  exit 2
fi

run() {
  echo "+ $*"
  "$@"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SRC_ROOT="$REPO_ROOT/demo/src"
MCP_IMAGE="$ACR_NAME.azurecr.io/mcp-server:$TAG"
B_IMAGE="$ACR_NAME.azurecr.io/resource-b:$TAG"
UPSTREAM_IMAGE="$ACR_NAME.azurecr.io/upstream-api:$TAG"

run az deployment sub create --location "$LOCATION" --template-file "$SCRIPT_DIR/main.bicep" --parameters "$SCRIPT_DIR/main.bicepparam" resourceGroupName="$RESOURCE_GROUP" location="$LOCATION" namePrefix="$NAME_PREFIX" acrName="$ACR_NAME" keyVaultName="$KEY_VAULT_NAME" deployContainerApps=false mcpServerImage="$MCP_IMAGE" resourceBImage="$B_IMAGE" upstreamApiImage="$UPSTREAM_IMAGE"

run az acr build --registry "$ACR_NAME" --image "mcp-server:$TAG" "$SRC_ROOT/mcp-server"
run az acr build --registry "$ACR_NAME" --image "resource-b:$TAG" "$SRC_ROOT/resource-b"
run az acr build --registry "$ACR_NAME" --image "upstream-api:$TAG" "$SRC_ROOT/upstream-api"

run az deployment sub create --location "$LOCATION" --template-file "$SCRIPT_DIR/main.bicep" --parameters "$SCRIPT_DIR/main.bicepparam" resourceGroupName="$RESOURCE_GROUP" location="$LOCATION" namePrefix="$NAME_PREFIX" acrName="$ACR_NAME" keyVaultName="$KEY_VAULT_NAME" deployContainerApps=true mcpServerImage="$MCP_IMAGE" resourceBImage="$B_IMAGE" upstreamApiImage="$UPSTREAM_IMAGE"
