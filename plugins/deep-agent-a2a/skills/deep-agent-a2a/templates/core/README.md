# {{title}}

Deep Agents agents, each wrapped in the **A2A** protocol so any A2A client can call it.
{{#web}}A web UI talks to them through a small backend for frontend (BFF).{{/web}}
{{#mcp}}Tools come from an **MCP server**; tools with side effects wait for the user's approval.{{/mcp}}
All state is in PostgreSQL (one database per agent, behind PgBouncer), so agents scale out.

```mermaid
flowchart LR
    # {{#web}}
    UI["Web UI"] -- "HTTP + SSE" --> BFF["BFF"]
    BFF -- "A2A" --> AG["{{agent}}-agent"]
    # {{/web}}
    CLI["CLI"] -- "A2A" --> AG["{{agent}}-agent"]
    # {{#mcp}}
    AG -- "MCP" --> MCP["mcp-server"]
    # {{/mcp}}
    AG -- "model" --> GW["AI gateway"]
    AG --> PB["PgBouncer"] --> PG[("PostgreSQL")]
```

## Run it

Prerequisites: Docker with Compose v2, and an OpenAI-compatible model endpoint that supports the Responses API
(default: an AI gateway on the host at `{{model_base_url}}`). Check it with `curl -s localhost:4000/v1/models`.

```sh
docker compose up --build -d
docker compose run --rm --entrypoint python cli smoke.py http://{{agent}}-agent:8000   # one conversation, end to end
docker compose run --rm cli http://{{agent}}-agent:8000                                # chat in the terminal
```
{{#web}}
Web UI: <http://localhost:{{port}}>
{{/web}}

Stop with `docker compose down` (`-v` also deletes the data). Logs: `docker compose logs -f {{agent}}-agent`.

| Setting | Default | Meaning |
| --- | --- | --- |
| `MODEL` | `{{model}}` | LangChain `provider:model` |
| `MODEL_BASE_URL` | `{{model_base_url}}` | OpenAI-compatible endpoint (Responses API) |
| `MODEL_API_KEY` | `not-needed` | key for that endpoint |

## Layout

| Path | What |
| --- | --- |
| `agent/agent.py` | The deep agent: model, system prompt, tools{{#mcp}} from MCP{{/mcp}}, skills, a hook, approvals, checkpointer. No HTTP. |
| `agent/main.py` | The A2A wrapper: Agent Card, streaming, progress updates, approvals as *input-required*, task store in PostgreSQL, `DELETE /threads/{contextId}`. |
| `agent/agents/<name>/` | One folder per agent: `agent.toml` (name, prompt, MCP server, tools that need approval, progress texts) and `skills/`. |
{{#mcp}}
| `mcp-server/` | Stateless FastMCP server with a sample tool, `save_note`. |
{{/mcp}}
{{#web}}
| `bff/` | Backend for frontend + `static/index.html` (the web UI). Keeps the chat list, calls the agent over A2A, streams to the browser. |
{{/web}}
| `cli/` | `chat.py` (terminal chat), `smoke.py` (end-to-end test), `stress.py` (load test). |
| `postgres/init.sql` | Creates one database per agent{{#web}} and one for the BFF{{/web}}. |

## Add an agent

Every agent runs the same code with its own config folder and database:

```sh
python3 <skill>/scripts/scaffold.py add-agent . --agent hr --agent-title "HR agent" --agent-description "Answers HR policy questions."
docker compose exec postgres psql -U postgres -c "CREATE DATABASE hr"   # init.sql only runs on a new volume
docker compose up --build -d hr-agent
docker compose run --rm --entrypoint python cli smoke.py http://hr-agent:8000
```

## Scale an agent

```sh
docker compose up -d --scale {{agent}}-agent=3
docker compose run --rm --entrypoint python cli stress.py http://{{agent}}-agent:8000 20 40
docker compose exec -e PGPASSWORD=postgres postgres psql -h pgbouncer -p 6432 -U postgres -d pgbouncer -c "SHOW POOLS"
```

Nothing lives in an agent process: conversations are in the LangGraph checkpointer, A2A tasks in the A2A task store,
both in the agent's database. A streamed answer is one connection to one replica.

## Not production

No authentication, one PostgreSQL password for everything, no TLS, no retention job for old checkpoints.
