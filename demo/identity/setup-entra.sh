#!/usr/bin/env bash
set -euo pipefail

TENANT_ID=""
PREFIX="mcp-auth-demo"
REDIRECT_URI="https://vscode.dev/redirect"
CREATE_SECRET="false"
YES="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tenant-id) TENANT_ID="$2"; shift 2 ;;
    --prefix) PREFIX="$2"; shift 2 ;;
    --redirect-uri) REDIRECT_URI="$2"; shift 2 ;;
    --create-client-secret) CREATE_SECRET="true"; shift ;;
    --yes) YES="true"; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$TENANT_ID" ]]; then
  echo "Missing required --tenant-id." >&2
  exit 2
fi

echo "Tenant: $TENANT_ID"
echo "Prefix: $PREFIX"
echo "Redirect URI: $REDIRECT_URI"
echo "Plan: create/update Upstream Refund API, MCP Resource A, MCP Resource B, and public MCP client."
echo "No changes are made unless --yes is supplied."
if [[ "$YES" != "true" ]]; then exit 0; fi

need_app() {
  local name="$1"
  local existing
  existing="$(az ad app list --display-name "$name" --query '[0].appId' -o tsv)"
  if [[ -n "$existing" ]]; then
    echo "$existing"
  else
    az ad app create --display-name "$name" --sign-in-audience AzureADMyOrg --query appId -o tsv
  fi
}

object_id() {
  az ad app show --id "$1" --query id -o tsv
}

new_guid() {
  if command -v uuidgen >/dev/null 2>&1; then uuidgen | tr '[:upper:]' '[:lower:]'; else python -c "import uuid; print(uuid.uuid4())"; fi
}

scope_id() {
  local app_id="$1"
  local value="$2"
  local existing
  existing="$(az ad app show --id "$app_id" --query "api.oauth2PermissionScopes[?value=='$value'].id | [0]" -o tsv)"
  if [[ -n "$existing" ]]; then echo "$existing"; else new_guid; fi
}

patch_app() {
  local object="$1"
  local body="$2"
  echo "+ az rest PATCH application $object"
  az rest --method PATCH --url "https://graph.microsoft.com/v1.0/applications/$object" --headers "Content-Type=application/json" --body "$body" >/dev/null
}

UPSTREAM_APP_ID="$(need_app "$PREFIX-upstream-refund-api")"
MCP_A_APP_ID="$(need_app "$PREFIX-mcp-resource-a")"
MCP_B_APP_ID="$(need_app "$PREFIX-mcp-resource-b")"
CLIENT_APP_ID="$(need_app "$PREFIX-mcp-public-client")"

UPSTREAM_OBJ="$(object_id "$UPSTREAM_APP_ID")"
MCP_A_OBJ="$(object_id "$MCP_A_APP_ID")"
MCP_B_OBJ="$(object_id "$MCP_B_APP_ID")"
CLIENT_OBJ="$(object_id "$CLIENT_APP_ID")"

LEDGER_SCOPE_ID="$(scope_id "$UPSTREAM_APP_ID" "Ledger.Refund")"
READ_SCOPE_ID="$(scope_id "$MCP_A_APP_ID" "Refunds.Read")"
WRITE_SCOPE_ID="$(scope_id "$MCP_A_APP_ID" "Refunds.Write")"
PROBE_SCOPE_ID="$(scope_id "$MCP_B_APP_ID" "Probe.Read")"

patch_app "$UPSTREAM_OBJ" "{\"identifierUris\":[\"api://$UPSTREAM_APP_ID\"],\"api\":{\"requestedAccessTokenVersion\":2,\"oauth2PermissionScopes\":[{\"id\":\"$LEDGER_SCOPE_ID\",\"value\":\"Ledger.Refund\",\"type\":\"Admin\",\"isEnabled\":true,\"adminConsentDisplayName\":\"Refund ledger\",\"adminConsentDescription\":\"Allows refund mutations in the synthetic demo ledger.\"}]}}"

patch_app "$MCP_A_OBJ" "{\"identifierUris\":[\"api://$MCP_A_APP_ID\"],\"api\":{\"requestedAccessTokenVersion\":2,\"oauth2PermissionScopes\":[{\"id\":\"$READ_SCOPE_ID\",\"value\":\"Refunds.Read\",\"type\":\"Admin\",\"isEnabled\":true,\"adminConsentDisplayName\":\"Read refund data\",\"adminConsentDescription\":\"Allows reading order and refund assessment data from MCP Resource A.\"},{\"id\":\"$WRITE_SCOPE_ID\",\"value\":\"Refunds.Write\",\"type\":\"Admin\",\"isEnabled\":true,\"adminConsentDisplayName\":\"Write refunds\",\"adminConsentDescription\":\"Allows invoking refund_order through MCP Resource A.\"}],\"preAuthorizedApplications\":[{\"appId\":\"$CLIENT_APP_ID\",\"delegatedPermissionIds\":[\"$READ_SCOPE_ID\",\"$WRITE_SCOPE_ID\"]}]},\"requiredResourceAccess\":[{\"resourceAppId\":\"$UPSTREAM_APP_ID\",\"resourceAccess\":[{\"id\":\"$LEDGER_SCOPE_ID\",\"type\":\"Scope\"}]}]}"

patch_app "$MCP_B_OBJ" "{\"identifierUris\":[\"api://$MCP_B_APP_ID\"],\"api\":{\"requestedAccessTokenVersion\":2,\"oauth2PermissionScopes\":[{\"id\":\"$PROBE_SCOPE_ID\",\"value\":\"Probe.Read\",\"type\":\"Admin\",\"isEnabled\":true,\"adminConsentDisplayName\":\"Probe Resource B\",\"adminConsentDescription\":\"Allows wrong-audience probe calls to MCP Resource B.\"}]}}"

patch_app "$CLIENT_OBJ" "{\"isFallbackPublicClient\":true,\"publicClient\":{\"redirectUris\":[\"$REDIRECT_URI\"]},\"requiredResourceAccess\":[{\"resourceAppId\":\"$MCP_A_APP_ID\",\"resourceAccess\":[{\"id\":\"$READ_SCOPE_ID\",\"type\":\"Scope\"},{\"id\":\"$WRITE_SCOPE_ID\",\"type\":\"Scope\"}]}]}"

if [[ "$CREATE_SECRET" == "true" ]]; then
  echo "Creating MCP Resource A client secret. Store the value in Key Vault; it is printed once by Azure CLI."
  az ad app credential reset --id "$MCP_A_APP_ID" --display-name phase4-demo-obo --years 1
else
  echo "No secret created. Preferred production path: add a certificate credential to MCP Resource A."
fi

cat <<EOF

Expected values for infra parameters:
mcpAClientId=$MCP_A_APP_ID
mcpAAudience=api://$MCP_A_APP_ID
mcpBAudience=api://$MCP_B_APP_ID
upstreamApiAudience=api://$UPSTREAM_APP_ID
upstreamApiScope=api://$UPSTREAM_APP_ID/Ledger.Refund
allowedClientIds=$CLIENT_APP_ID

Admin consent commands/URLs:
+ az ad app permission admin-consent --id $MCP_A_APP_ID
+ az ad app permission admin-consent --id $CLIENT_APP_ID
https://login.microsoftonline.com/$TENANT_ID/adminconsent?client_id=$CLIENT_APP_ID&redirect_uri=https%3A%2F%2Fvscode.dev%2Fredirect
EOF
