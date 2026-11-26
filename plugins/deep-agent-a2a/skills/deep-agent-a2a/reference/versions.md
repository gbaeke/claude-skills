# Versions and tests

## Verified set (2026-11-26)

Passed `smoke.py` (approval, MCP call, follow-up) and `stress.py` (up to 40 parallel conversations over 5 replicas)
with these versions. The templates pin them in each `pyproject.toml` and ship the matching `uv.lock` files.

| Package / image | Version |
|---|---|
| deepagents | 0.7.42 |
| langchain[mcp] | 1.5.2 (built-in `langchain.mcp`, beta, needs fastmcp ≥ 4) |
| langgraph | 1.2.24 |
| langchain-openai | 1.8.5 |
| langgraph-checkpoint-postgres | 3.2.1 |
| psycopg | 3.3.9 |
| a2a-sdk | 1.3.1 (A2A protocol 1.0) |
| fastmcp | 4.2.6 (mcp 2.3) |
| fastapi | 0.165.0 |
| uvicorn | 0.54.0 |
| httpx | 0.29.0 |
| Python image | python:3.13-slim, uv 0.13.4 |
| PostgreSQL / PgBouncer | postgres:18 / edoburu/pgbouncer:v1.26.1-p0 |

## Checking for newer releases

Always ask the user first. `scaffold.py new ... --latest` drops the pins and runs `uv lock --upgrade` per service
(images stay pinned). Then build and run `smoke.py`. What tends to break, from experience:

- **a2a-sdk:** type and helper names (protobuf types in 1.x), task-store and request-handler classes, how resumed
  tasks stream. Check `agent/main.py` against the SDK's samples (`a2aproject/a2a-samples`, `samples/python/agents/helloworld`).
- **langchain.mcp** is beta: the `MCPAdapter` API may change.
- **deepagents** is 0.x: `create_deep_agent` arguments, backends, the shape of `interrupt` values
  (`action_requests`), resume decisions.
- **Model endpoint:** a provider may stop accepting `store=False` or `include=[...]`.

If it fails and the fix isn't obvious, fall back to the verified set (rerun the scaffold without `--latest`). After
a successful upgrade, update the pins, the lock files and this table in the skill.

## Tests

```sh
docker compose run --rm --entrypoint python cli smoke.py http://<agent>-agent:8000 ["question"]   # exit 0 = OK
docker compose run --rm --entrypoint python cli stress.py http://<agent>-agent:8000 20 40          # concurrency, conversations
```

`stress.py` sends the Agent Card's examples, approves on a **new connection** (so approvals can cross replicas; reusing
one HTTP connection keeps both turns on one replica), and reports ok/failed, throughput, turn time and first-token
p50/p95. Every turn is real model calls; keep the numbers modest.
