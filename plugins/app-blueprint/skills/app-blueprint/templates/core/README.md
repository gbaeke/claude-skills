# {{title}}

<!-- What it does, in two sentences. -->

## Run it

Needs [uv](https://docs.astral.sh/uv/){{#frontend}}, Node.js 24+{{/frontend}}{{#db}} and Docker (for PostgreSQL){{/db}}.

```bash
scripts/run-local.sh        # http://localhost:{{port}}
```

Settings live in `.env` (created from `.env.example` on the first run).

## Develop

```bash
{{#frontend}}
scripts/run-local.sh --dev  # hot reload on http://localhost:5173
{{/frontend}}
scripts/check.sh            # lint, types, tests: what CI runs
```

API docs: http://localhost:{{port}}/api/docs
{{#azure}}

## Deploy to Azure

Needs `az` (logged in: `az login`) and Docker.

```bash
scripts/azure-up.sh        # once, and when infra/main.bicep changes: the shared infrastructure, then the app
scripts/azure-deploy.sh    # every new version: build and push the image, update only the Container App
scripts/azure-down.sh      # remove everything
```

Container Apps scales to zero: the first request after an idle period takes a few seconds.
{{#db}}
PostgreSQL accepts Entra sign-in only: the app uses its managed identity, and you (as the deployer) are an admin too:
`PGPASSWORD=$(az account get-access-token --resource-type oss-rdbms --query accessToken -o tsv) psql "host=<server> user=<you@domain> dbname={{pkg}} sslmode=require"`.
{{/db}}
{{/azure}}
