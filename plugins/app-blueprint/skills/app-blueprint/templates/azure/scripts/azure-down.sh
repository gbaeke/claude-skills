#!/usr/bin/env bash
# Remove everything: the resource group with all its data{{#auth}}, and the app's address in WorkOS{{/auth}}.
#   scripts/azure-down.sh
#   AZURE_RESOURCE_GROUP=rg-x scripts/azure-down.sh
#   YES=1 scripts/azure-down.sh          # do not ask for confirmation
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck source=scripts/azure-lib.sh
source scripts/azure-lib.sh

az_login
load_state
if [ "$(az group exists -n "$RG")" = "true" ]; then
  echo "Deletes resource group $RG with all its data. This cannot be undone."
  if [ -z "${YES:-}" ]; then
    read -r -p "Type the resource group name to confirm: " answer
    [ "$answer" = "$RG" ] || { echo "Not deleted."; exit 1; }
  fi
{{#auth}}
  FQDN=$(az containerapp show -g "$RG" -n {{app}} --query properties.configuration.ingress.fqdn -o tsv 2>/dev/null || true)
{{/auth}}
  echo "== Deleting $RG (takes several minutes)"
  az group delete -n "$RG" --yes
else
  echo "Resource group $RG does not exist."
fi
{{#auth}}
if [ -n "${WORKOS_CLIENT_ID:-}" ] && [ -n "${FQDN:-}" ]; then
  scripts/workos-uris.sh remove "https://$FQDN" ||
    echo "Remove https://$FQDN/auth/callback and https://$FQDN/ in WorkOS (Redirects)."
fi
{{/auth}}
rm -f "$STATE"
echo "Done."
