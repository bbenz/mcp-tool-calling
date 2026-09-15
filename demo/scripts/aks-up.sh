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
#                       [--foundry-endpoint URL] [--foundry-deployment NAME]
#                       [--foundry-api-key KEY]
#                       [--no-access-key] [--yes]
set -euo pipefail

DEMO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# az is a Python application, and `az acr build` streams the build log through
# its stdout encoder. Under Git Bash on Windows that can default to cp1252, and
# one non-cp1252 character in pip's output then kills the command with
# UnicodeEncodeError *after* the image has already been built and pushed.
export PYTHONIOENCODING=utf-8

RESOURCE_GROUP=rg-mcp-refund-demo
LOCATION=eastus
CLUSTER_NAME=aks-mcp-refund-demo
REGISTRY_NAME=""
NODE_COUNT=1
NODE_SIZE=Standard_D2s_v3
ACCESS_KEY_ENABLED=1
ASSUME_YES=0
FOUNDRY_ENDPOINT=""
FOUNDRY_DEPLOYMENT=""
FOUNDRY_API_KEY=""

while [ $# -gt 0 ]; do
  case "$1" in
    --resource-group) RESOURCE_GROUP="$2"; shift 2 ;;
    --location)       LOCATION="$2"; shift 2 ;;
    --cluster-name)   CLUSTER_NAME="$2"; shift 2 ;;
    --registry-name)  REGISTRY_NAME="$2"; shift 2 ;;
    --node-count)     NODE_COUNT="$2"; shift 2 ;;
    --node-size)      NODE_SIZE="$2"; shift 2 ;;
    --no-access-key)  ACCESS_KEY_ENABLED=0; shift ;;
    --foundry-endpoint)   FOUNDRY_ENDPOINT="$2"; shift 2 ;;
    --foundry-deployment) FOUNDRY_DEPLOYMENT="$2"; shift 2 ;;
    --foundry-api-key)    FOUNDRY_API_KEY="$2"; shift 2 ;;
    --yes|-y)         ASSUME_YES=1; shift ;;
    -h|--help)        sed -n '2,22p' "$0"; exit 0 ;;
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
#
# --no-logs is not cosmetic. Streaming the build log routes it through
# colorama, which under Git Bash on Windows writes in cp1252 and dies with
# UnicodeEncodeError on the first character it cannot map -- *after* the image
# has been built and pushed. The command still waits for the run to finish and
# still fails loudly if the build fails; you just have to ask for the log.
if ! az acr build --registry "$REGISTRY_NAME" --image "refund-demo:$TAG" \
     --file docker/Dockerfile "$DEMO" --no-logs -o none; then
  echo ""
  echo "The image build failed. Fetch the log with:" >&2
  echo "  az acr task list-runs --registry $REGISTRY_NAME --top 1 -o table" >&2
  echo "  az acr task logs --registry $REGISTRY_NAME --run-id <runId>" >&2
  exit 1
fi

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

# Optional: point the advisory tool at a real Foundry deployment. Without this
# the tool returns a labelled offline assessment and every scenario still
# passes -- the model is a demo layer, never a dependency.
#
# All of it goes in a Secret rather than the ConfigMap, including the endpoint
# and deployment name, which are not secrets in the cryptographic sense but do
# name a resource in someone's subscription. The ConfigMap is read by all five
# containers; this Secret is read by mcp-a alone, which is the only caller. One
# object, one lifecycle, one blast radius.
if [ -n "$FOUNDRY_ENDPOINT" ] && [ -n "$FOUNDRY_DEPLOYMENT" ]; then
  secret_args=(
    --from-literal=FOUNDRY_ENDPOINT="$FOUNDRY_ENDPOINT"
    --from-literal=FOUNDRY_DEPLOYMENT="$FOUNDRY_DEPLOYMENT"
  )
  if [ -n "$FOUNDRY_API_KEY" ]; then
    secret_args+=(--from-literal=FOUNDRY_API_KEY="$FOUNDRY_API_KEY")
    how="api key"
  else
    how="no key -- needs workload identity"
  fi
  kubectl -n refund-demo create secret generic refund-demo-foundry "${secret_args[@]}" \
    --dry-run=client -o yaml | kubectl apply -f -
  echo "      Foundry: $FOUNDRY_DEPLOYMENT ($how)"
elif [ -n "$FOUNDRY_ENDPOINT" ] || [ -n "$FOUNDRY_DEPLOYMENT" ]; then
  echo "--foundry-endpoint and --foundry-deployment must be given together" >&2
  exit 2
else
  # A leftover Secret from a previous deploy would silently re-enable the
  # model on a run that did not ask for it.
  kubectl -n refund-demo delete secret refund-demo-foundry --ignore-not-found >/dev/null
fi

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
