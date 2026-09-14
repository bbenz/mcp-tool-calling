#!/usr/bin/env bash
# Delete everything aks-up.sh created.
#
# Deletes the whole resource group, which is the only way to be confident the
# cluster, the registry, the load balancer, the public IP and the managed
# identity all went with it. A demo cluster left running over a conference
# weekend is a real bill.
#
# Usage: ./scripts/aks-down.sh [--resource-group NAME] [--cluster-name NAME]
#                              [--wait] [--yes]
set -euo pipefail

RESOURCE_GROUP=rg-mcp-refund-demo
CLUSTER_NAME=aks-mcp-refund-demo
WAIT=0
ASSUME_YES=0

while [ $# -gt 0 ]; do
  case "$1" in
    --resource-group) RESOURCE_GROUP="$2"; shift 2 ;;
    --cluster-name)   CLUSTER_NAME="$2"; shift 2 ;;
    --wait)           WAIT=1; shift ;;
    --yes|-y)         ASSUME_YES=1; shift ;;
    -h|--help)        sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

command -v az >/dev/null 2>&1 || { echo "az not found on PATH." >&2; exit 1; }

if ! az group show --name "$RESOURCE_GROUP" -o none 2>/dev/null; then
  echo "Resource group '$RESOURCE_GROUP' does not exist. Nothing to do."
  exit 0
fi

echo
echo "  About to delete resource group '$RESOURCE_GROUP' and everything in it."
az resource list --resource-group "$RESOURCE_GROUP" --query "[].{name:name,type:type}" -o table
echo

if [ "$ASSUME_YES" -eq 0 ]; then
  read -r -p "Type the resource group name to confirm: " answer
  [ "$answer" = "$RESOURCE_GROUP" ] || { echo "Cancelled."; exit 1; }
fi

if [ "$WAIT" -eq 1 ]; then
  az group delete --name "$RESOURCE_GROUP" --yes
else
  az group delete --name "$RESOURCE_GROUP" --yes --no-wait
  echo "Delete started. Check with: az group show --name $RESOURCE_GROUP"
fi

# The kubeconfig entry outlives the cluster and will otherwise sit there as a
# broken current-context, which is a confusing thing to hit later.
kubectl config delete-context "$CLUSTER_NAME" >/dev/null 2>&1 || true
kubectl config delete-cluster "$CLUSTER_NAME" >/dev/null 2>&1 || true
