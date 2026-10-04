#!/usr/bin/env bash
# Create or update the shared infrastructure (infra/main.bicep), then deploy the app (scripts/azure-deploy.sh).
# Run it the first time and when main.bicep changes; for a new version of the app, azure-deploy.sh is enough.
#   scripts/azure-up.sh                              # resource group rg-{{app}} in swedencentral
#   AZURE_RESOURCE_GROUP=rg-x LOCATION=westeurope scripts/azure-up.sh
#   YES=1 scripts/azure-up.sh                        # do not ask for confirmation
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck source=scripts/azure-lib.sh
source scripts/azure-lib.sh

az_login
load_state
LOCATION="${LOCATION:-swedencentral}"
echo "Region: $LOCATION"
confirm "Create or update the infrastructure here? This creates billable resources."
save_state

echo "== Infrastructure (main.bicep)"
az group create -n "$RG" -l "$LOCATION" -o none
{{#db}}
# you become a PostgreSQL admin next to the app's identity (psql with an az login token: see the README)
read -r ADMIN_ID ADMIN_NAME < <(az ad signed-in-user show --query "[id, userPrincipalName]" -o tsv | paste -sd ' ')
{{/db}}
az deployment group create -g "$RG" -n infra -f infra/main.bicep \
  -p location="$LOCATION"{{#db}} adminObjectId="$ADMIN_ID" adminName="$ADMIN_NAME"{{/db}} -o none

YES=1 scripts/azure-deploy.sh
