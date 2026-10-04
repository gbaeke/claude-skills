# Azure

## Shape

- **`infra/main.bicep`**: the shared infrastructure. Log Analytics; a registry (no admin user) with a user-assigned
  identity that has AcrPull; PostgreSQL Flexible Server (Burstable B1ms, Entra auth only) with the app identity and
  the deployer as Entra admins; and the Container Apps environment (Consumption). It contains no apps. It changes
  rarely and is deployed by `scripts/azure-up.sh`.
- **`infra/app.bicep`**: one Container App on that infrastructure, found through `existing` references. Every name
  derives from `uniqueString(resourceGroup().id)`, so it needs no outputs passed in. It is deployed on every
  release by `scripts/azure-deploy.sh` and touches only that one resource. Its configuration (env, secrets, probes,
  scale) lives in code, never in portal edits or `az containerapp update` flags that the next deploy would undo. A
  second app or a worker is another deployment of `app.bicep` with its own `name` and `image`.
- **`infra/modules/pg-admin.bicep`**: a PostgreSQL Entra admin. It is a module because the resource's name is the
  identity's object id, which isn't known at the start of the deployment (BCP120).
- **`infra/bicepconfig.json`**: the linter, with `use-recent-api-versions` on (warning past two years), plus errors
  for secrets in outputs and hardcoded URLs. `check.sh` builds every `.bicep` file; `scripts/versions.sh` lists stale
  API versions.

## Scripts

```bash
scripts/azure-up.sh        # infra (main.bicep), then azure-deploy.sh. Asks before creating billable resources.
scripts/azure-deploy.sh    # docker build (linux/amd64), push with a <timestamp>-<git sha> tag, deploy app.bicep
scripts/azure-down.sh      # deletes the resource group after you type its name; removes the WorkOS URIs
```

`AZURE_RESOURCE_GROUP` (default `rg-<app>`), `LOCATION` (default swedencentral) and `YES=1` (no prompts).
`.azure/<rg>.env` (git-ignored, mode 600) keeps what every deploy needs again: the region, `ALLOWED_IPS`, and with
auth the WorkOS settings and the generated `SESSION_SECRET`. A variable set in the environment wins over the file and
is saved; set it empty to clear it. `ALLOWED_IPS=1.2.3.4/32,...` becomes ingress IP rules (in code, so it survives
deploys).

## Runtime

- Scale 0–1: the app sleeps when idle (the first request takes a few seconds) and costs almost nothing. Migrations
  run at startup under an advisory lock, so more replicas are safe for them. Raise `maxReplicas` once nothing lives
  in process memory (queues, caches, progress).
- Startup and readiness probes hit `/api/health`. Traffic arrives only after migrations are done.
- `LOG_JSON=true`: container logs land in Log Analytics as JSON (query by `request_id`).
- PostgreSQL: Entra tokens via the managed identity, so no password exists anywhere (see `database.md`).

## Left out on purpose (and how to add it)

- **Key Vault:** Container Apps secrets are enough for a few secrets. Move to Key Vault references
  (`keyVaultUrl` + `identity` on the secret) for rotation, audit, or secrets shared between apps.
- **Private networking:** a VNet-integrated environment plus PostgreSQL private access. Worth it for sensitive data;
  it costs more and adds more to manage.
- **Application Insights / OpenTelemetry:** add the resource to `main.bicep`, its connection string as a secret in
  `app.bicep`, and `azure-monitor-opentelemetry` in `main()`.
- **Deploying from CI:** a GitHub Actions job with OIDC federated credentials (no stored secrets) that runs
  `scripts/azure-deploy.sh` on main. Add it once more than one person deploys.
- **azd (Azure Developer CLI)** is Microsoft's supported wrapper for the same flow (`azd provision` = azure-up,
  `azd deploy` = azure-deploy, with state in `.azure/` too). The blueprint keeps plain scripts because they are
  transparent and need no extra conventions (`azure.yaml`, parameter files). azd is a reasonable choice for teams
  that already use it.
- **Static Web Apps / separate frontend hosting:** not needed; the frontend ships inside the app image.
