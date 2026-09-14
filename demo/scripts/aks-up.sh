#!/usr/bin/env bash
# Deploy the demo to Azure Kubernetes Service.
#
# Optional path. The script-based demo is unchanged and is still the rehearsed
# stage path; this exists for a remote audience, for a room with unreliable
# laptop projection, and for the "what would this look like hosted" question.
#
# The image is built by ACR Tasks, not locally, so this works from a network
# that blocks the PyPI wheel CDN -- which is exactly the situation that makes
# docker compose build fail. See docs/DEPLOYMENT.md.
#
# This creates billable Azure resources. It asks first unless --yes is passed,
# and ./scripts/aks-down.sh removes everything.
#
# Usage:
#   ./scripts/aks-up.sh [--resource-group NAME] [--location REGION]
#                       [--cluster-name NAME] [--registry-name NAME]
#                       [--node-count N] [--node-size SIZE]
#                       [--no-access-key] [--yes]
set -euo pipefail

DEMO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

RESOURCE_GROUP=rg-mcp-refund-demo
LOCATION=eastus
CLUSTER_NAME=aks-mcp-refund-demo
REGISTRY_NAME=""
NODE_COUNT=1
NODE_SIZE=Standard_D2s_v3
ACCESS_KEY_ENABLED=1
ASSUME_YES=0

while [ $# -gt 0 ]; do
  case "$1" in
    --resource-group) RESOURCE_GROUP="$2"; shift 2 ;;
    --location)       LOCATION="$2"; shift 2 ;;
    --cluster-name)   CLUSTER_NAME="$2"; shift 2 ;;
    --registry-name)  REGISTRY_NAME="$2"; shift 2 ;;
    --node-count)     NODE_COUNT="$2"; shift 2 ;;
    --node-size)      NODE_SIZE="$2"; shift 2 ;;
    --no-access-key)  ACCESS_KEY_ENABLED=0; shift ;;
    --yes|-y)         ASSUME_YES=1; shift ;;
    -h|--help)        sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

for tool in az kubectl; do
  command -v "$tool" >/dev/null 2>&1 || {
    echo "$tool not found on PATH. See docs/DEPLOYMENT.md for prerequisites." >&2
    exit 1
  }
done

if ! SUB_ID="$(az account show --query id -o tsv 2>/dev/null)"; then
  echo "Not signed in. Run: az login" >&2
  exit 1
fi
SUB_NAME="$(az account show --query name -o tsv)"

if [ -z "$REGISTRY_NAME" ]; then
  # ACR names are globally unique and alphanumeric only. Derive one from the
  # subscription so repeat runs land on the same registry.
  hash="$(printf '%s' "$SUB_ID" | sha256sum | cut -c1-8)"
  REGISTRY_NAME="acrrefunddemo${hash}"
fi

TAG="v$(date -u +%Y%m%d%H%M%S)"

cat <<EOF

  subscription   $SUB_NAME  ($SUB_ID)
  resource group $RESOURCE_GROUP
  location       $LOCATION
  registry       $REGISTRY_NAME
  cluster        $CLUSTER_NAME  ($NODE_COUNT x $NODE_SIZE)
  image tag      $TAG

  This creates billable Azure resources.
  Remove them with: ./scripts/aks-down.sh --resource-group $RESOURCE_GROUP

EOF

if [ "$ASSUME_YES" -eq 0 ]; then
  read -r -p "Continue? (y/N) " answer
  case "$answer" in y|Y|yes|YES) ;; *) echo "Cancelled."; exit 1 ;; esac
fi

echo "[1/6] resource group ..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" \
  --tags purpose=conference-demo data=synthetic -o none

echo "[2/6] container registry ..."
if ! az acr show --name "$REGISTRY_NAME" --resource-group "$RESOURCE_GROUP" -o none 2>/dev/null; then
  az acr create --name "$REGISTRY_NAME" --resource-group "$RESOURCE_GROUP" \
    --sku Basic --location "$LOCATION" -o none
fi

echo "[3/6] building image in ACR (this is where the pip install happens) ..."
# Built server-side on purpose: ACR Tasks can reach PyPI even when the laptop
# cannot, and the build machine matches the cluster architecture.
az acr build --registry "$REGISTRY_NAME" --image "refund-demo:$TAG" \
  --file docker/Dockerfile "$DEMO" -o none

LOGIN_SERVER="$(az acr show --name "$REGISTRY_NAME" --resource-group "$RESOURCE_GROUP" --query loginServer -o tsv)"
IMAGE="$LOGIN_SERVER/refund-demo:$TAG"

echo "[4/6] AKS cluster (first run takes several minutes) ..."
if az aks show --name "$CLUSTER_NAME" --resource-group "$RESOURCE_GROUP" -o none 2>/dev/null; then
  az aks update --name "$CLUSTER_NAME" --resource-group "$RESOURCE_GROUP" \
    --attach-acr "$REGISTRY_NAME" -o none
else
  az aks create --name "$CLUSTER_NAME" --resource-group "$RESOURCE_GROUP" \
    --node-count "$NODE_COUNT" --node-vm-size "$NODE_SIZE" \
    --enable-managed-identity --attach-acr "$REGISTRY_NAME" \
    --network-plugin azure --network-plugin-mode overlay \
    --tier free --generate-ssh-keys -o none
fi

az aks get-credentials --name "$CLUSTER_NAME" --resource-group "$RESOURCE_GROUP" --overwrite-existing -o none

echo "[5/6] applying manifests ..."
kubectl apply -f "$DEMO/k8s/namespace.yaml"

ACCESS_KEY=""
if [ "$ACCESS_KEY_ENABLED" -eq 1 ]; then
  # The Service gets a public IP. An unauthenticated page that can move a
  # ledger should not sit on one, even with synthetic data.
  ACCESS_KEY="$(head -c 24 /dev/urandom | base64 | tr '+/' '-_' | tr -d '=')"
  kubectl -n refund-demo create secret generic refund-demo-secret \
    --from-literal=web-access-key="$ACCESS_KEY" --dry-run=client -o yaml | kubectl apply -f -
else
  kubectl -n refund-demo delete secret refund-demo-secret --ignore-not-found >/dev/null
fi

kubectl apply -f "$DEMO/k8s/configmap.yaml"
sed "s|IMAGE_PLACEHOLDER|$IMAGE|g" "$DEMO/k8s/deployment.yaml" | kubectl apply -f -
kubectl apply -f "$DEMO/k8s/service.yaml"

echo "[6/6] waiting for rollout and public address ..."
if ! kubectl -n refund-demo rollout status deploy/refund-demo --timeout=300s; then
  echo "Rollout did not complete. Inspect with:" >&2
  echo "  kubectl -n refund-demo get pods" >&2
  echo "  kubectl -n refund-demo describe pod -l app.kubernetes.io/name=refund-demo" >&2
  exit 1
fi

IP=""
deadline=$(( $(date +%s) + 300 ))
while [ -z "$IP" ] && [ "$(date +%s)" -lt "$deadline" ]; do
  IP="$(kubectl -n refund-demo get svc refund-demo-web -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || true)"
  [ -z "$IP" ] && sleep 5
done

echo
if [ -n "$IP" ]; then
  if [ -n "$ACCESS_KEY" ]; then
    echo "Demo is up."
    echo "  http://$IP/?k=$ACCESS_KEY"
    echo
    echo "  The access key is in that URL. Open it once and bookmark the tab;"
    echo "  the page forwards the key to its own API calls."
  else
    echo "Demo is up."
    echo "  http://$IP/"
  fi
else
  echo "Deployed, but the load balancer has not been assigned an address yet."
  echo "  kubectl -n refund-demo get svc refund-demo-web -w"
fi
echo
echo "Tear down with: ./scripts/aks-down.sh --resource-group $RESOURCE_GROUP"
