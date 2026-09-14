#!/usr/bin/env bash
set -euo pipefail

RESOURCE_GROUP=""
DEMO_TAG_NAME="mcp-auth-demo"
DEMO_TAG_VALUE="true"
YES="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --resource-group) RESOURCE_GROUP="$2"; shift 2 ;;
    --tag-name) DEMO_TAG_NAME="$2"; shift 2 ;;
    --tag-value) DEMO_TAG_VALUE="$2"; shift 2 ;;
    --yes) YES="true"; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ "$YES" != "true" ]]; then
  echo "Dry run only. Re-run with --yes to delete the tagged demo resource group."
  exit 0
fi

if [[ -z "$RESOURCE_GROUP" ]]; then
  echo "Missing required --resource-group." >&2
  exit 2
fi

TAG="$(az group show --name "$RESOURCE_GROUP" --query "tags.$DEMO_TAG_NAME" -o tsv)"
if [[ "$TAG" != "$DEMO_TAG_VALUE" ]]; then
  echo "Refusing to delete $RESOURCE_GROUP because tag $DEMO_TAG_NAME=$DEMO_TAG_VALUE was not found." >&2
  exit 1
fi

read -r -p "Type the resource group name '$RESOURCE_GROUP' to confirm deletion: " ANSWER
if [[ "$ANSWER" != "$RESOURCE_GROUP" ]]; then
  echo "Confirmation did not match; aborting." >&2
  exit 1
fi

echo "+ az group delete --name \"$RESOURCE_GROUP\" --yes"
az group delete --name "$RESOURCE_GROUP" --yes
