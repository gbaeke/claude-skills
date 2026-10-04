#!/usr/bin/env bash
# Deploy the app on the existing infrastructure: build and push the image, then deploy infra/app.bicep (the
# Container App only). The infrastructure comes from scripts/azure-up.sh, once.
#   scripts/azure-deploy.sh
{{#auth}}
#   WORKOS_CLIENT_ID=client_... WORKOS_API_KEY=sk_... [ALLOWED_USERS=a@x,b@y] scripts/azure-deploy.sh   # sign-in on
#   WORKOS_CLIENT_ID= scripts/azure-deploy.sh        # sign-in off again
{{/auth}}
#   ALLOWED_IPS=203.0.113.4/32 scripts/azure-deploy.sh   # only these addresses (ALLOWED_IPS= opens it again)
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck source=scripts/azure-lib.sh
source scripts/azure-lib.sh

need docker
az_login
[ -f "$STATE" ] || { echo "No $STATE: create the infrastructure first with scripts/azure-up.sh" >&2; exit 1; }
load_state
{{#auth}}
if [ -n "${WORKOS_CLIENT_ID:-}" ]; then
  [ -n "${WORKOS_API_KEY:-}" ] || { echo "WORKOS_CLIENT_ID is set: also set WORKOS_API_KEY." >&2; exit 1; }
  SESSION_SECRET="${SESSION_SECRET:-$(openssl rand -base64 32)}"
fi
{{/auth}}
save_state

out() { az deployment group show -g "$RG" -n infra --query "properties.outputs.$1.value" -o tsv; }
ACR_NAME=$(out acrName)
IMAGE="$(out acrLoginServer)/{{app}}:$(date +%Y%m%d-%H%M%S)-$(git rev-parse --short HEAD)"
[ -z "$(git status --porcelain)" ] || echo "Note: uncommitted changes go into this image; its tag names HEAD."

echo "== Image $IMAGE"
docker build --platform linux/amd64 -t "$IMAGE" .
az acr login -n "$ACR_NAME"
docker push "$IMAGE"

echo "== App (app.bicep)"
FQDN=$(az deployment group create -g "$RG" -n app -f infra/app.bicep \
  -p location="$LOCATION" image="$IMAGE" ipRules="$(ip_rules_json)" \
{{#auth}}
  workosClientId="${WORKOS_CLIENT_ID:-}" workosApiKey="${WORKOS_API_KEY:-}" sessionSecret="${SESSION_SECRET:-}" \
  allowedUsers="${ALLOWED_USERS:-}" \
{{/auth}}
  --query properties.outputs.fqdn.value -o tsv)
{{#auth}}

if [ -n "${WORKOS_CLIENT_ID:-}" ]; then
  scripts/workos-uris.sh add "https://$FQDN" ||
    echo "Add in WorkOS (Redirects): redirect URI https://$FQDN/auth/callback, sign-out URI https://$FQDN/"
fi
{{/auth}}

echo
echo "Running at https://$FQDN (the first request after an idle period starts it: a few seconds)"
{{#auth}}
[ -n "${WORKOS_CLIENT_ID:-}" ] || [ -n "${ALLOWED_IPS:-}" ] ||
{{/auth}}
{{^auth}}
[ -n "${ALLOWED_IPS:-}" ] ||
{{/auth}}
  echo "No sign-in and no IP rules: anyone with this URL can use the app."
