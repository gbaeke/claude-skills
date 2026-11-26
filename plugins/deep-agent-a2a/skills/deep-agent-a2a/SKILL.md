---
name: deep-agent-a2a
description: Scaffold, extend or explain a LangChain Deep Agents agent served over the A2A protocol - a reusable A2A wrapper (Agent Card, streaming, progress updates, human-in-the-loop as input-required, PostgreSQL task store), LangGraph checkpointer in PostgreSQL behind PgBouncer with one database per agent, tools from MCP servers through LangChain's built-in MCP adapter, a FastMCP server, a BFF + web UI (chats, streaming Markdown, approval cards) and a CLI with smoke and load tests, all in Docker Compose. Use when the user wants a new LangGraph / Deep Agents agent, wants to expose an agent over A2A, add another agent to such a project, give an agent MCP tools or approvals, put a web UI or a Teams-style bot in front of an agent, make agents stateless or scale them, set up PostgreSQL / PgBouncer for agent state, or load-test an agent.
---

# Deep agent over A2A

A working multi-service project on day one: a Deep Agents agent wrapped in A2A, called by a web UI through a BFF
and by a CLI, with MCP tools that wait for approval and all state in PostgreSQL. `scripts/scaffold.py` renders it
from `templates/`; `reference/` explains each part, the decisions behind it and the traps already hit. Read the
matching reference file before changing that part of a project.

| Module | What | Default |
|---|---|---|
| core | Agent service (`agent/main.py` A2A wrapper + `agent/agent.py` deep agent, one `agent/agents/<name>/` config folder per agent), PostgreSQL with a database per agent, PgBouncer, `cli/` (chat, smoke, stress), compose.yaml, Dockerfile, README | always |
| mcp | `mcp-server/` (stateless FastMCP, sample `save_note` tool), wired into the first agent with approval and progress texts | on |
| web | `bff/` (FastAPI) + `bff/static/index.html`: chat list, streaming Markdown, progress line, approval cards that survive reloads, delete chat | on |

## Principles

1. **The agent is a library object; A2A makes it a service.** `agent.py` knows nothing about HTTP. `main.py` is the
   only A2A code, shared by every agent. A new agent is a config folder, not new code.
2. **Stateless processes.** Conversations live in the LangGraph checkpointer, A2A tasks in the A2A task store, chat
   lists in the BFF's database. Any replica serves any turn; an approval may land on another replica.
3. **One database per agent, one server, behind PgBouncer.** Agents never share tables; PgBouncer keeps PostgreSQL
   connections few however many replicas run.
4. **Stateless calls outward too:** the model through the Responses API with `store=False`, MCP servers in
   stateless HTTP mode.
5. **Show what happens.** Progress as A2A `WORKING` updates with a message, the answer as streamed artifact chunks,
   approvals as `input-required` with the exact tool call in a data part.
6. **Verified versions by default.** These libraries change fast; the templates pin a set that passed end to end.

## Git

Work on a branch, and commit or push only when the user says so.

## A. New project

1. **Ask only what the brief leaves open** (AskUserQuestion, one round):
   - the project name (kebab-case) and the first agent's name, title and one-sentence purpose;
   - the modules: drop `mcp` if the agent needs no tools, drop `web` if only other agents or Teams will call it;
   - the model endpoint, if not an OpenAI-compatible gateway on the host at `http://host.docker.internal:4000/v1`
     with `openai:azure-gpt-6-luna` (it must support the Responses API);
   - **versions: always ask** whether to use the verified versions (default, safe) or check for newer releases
     (`--latest`). Show the date and set from `reference/versions.md`.
2. **Prerequisites:** Docker with Compose v2; `uv` only for `--latest`. Check the model endpoint answers
   (`curl -s localhost:4000/v1/models` for the default gateway); without it the agent can't answer.
3. **Scaffold:**
   `python3 <this skill>/scripts/scaffold.py new <dest> --name <name> --agent <agent> --agent-title "<Title>"
   --agent-description "<one sentence>" [--without mcp,web] [--model ... --model-base-url ...] [--latest]`.
4. **Fit the agent to the brief:** edit `agent/agents/<agent>/agent.toml` (system prompt, examples, approve_tools,
   progress texts) and its `skills/`. With mcp, replace the sample tool in `mcp-server/server.py` or point
   `mcp_url` at an existing MCP server. See `reference/tools-and-model.md`.
5. **Run and prove it:** `docker compose up --build -d`, then
   `docker compose run --rm --entrypoint python cli smoke.py http://<agent>-agent:8000`. It must print `OK`:
   a turn (with approval if the agent asks), and a follow-up that remembers the first turn. With `--latest`, a
   failure here usually means an API changed: compare with `reference/versions.md`, then fix or fall back to the
   verified set. Show the web UI URL printed by the scaffold.
6. **Report** what was generated, the versions used, and the smoke-test result.

## B. Add an agent

`python3 <this skill>/scripts/scaffold.py add-agent <project> --agent <name> --agent-title "<Title>"
--agent-description "<one sentence>" [--mcp]`. It adds the config folder, a compose service and a database in
`postgres/init.sql`. On a running project create the database by hand (init.sql only runs on a new volume):
`docker compose exec postgres psql -U postgres -c "CREATE DATABASE <name_with_underscores>"`, then
`docker compose up --build -d <name>-agent` and run the smoke test against it. The BFF talks to one agent
(`AGENT_URL`); point it elsewhere or run a second BFF for another agent.

## C. Change or explain an existing project

Read the reference file first, keep the principles, and rerun the smoke test after any change to `agent/`, `bff/`
or the versions. For scale questions run `cli/stress.py` and look at `SHOW POOLS` (`reference/database.md`).

| Topic | Read |
|---|---|
| Components, state, request flow, scaling | `reference/architecture.md` |
| A2A wrapper: tasks, task store, streaming, progress, approvals, delete, client timeouts | `reference/a2a.md` |
| Model, MCP tools, skills, hooks, approvals config | `reference/tools-and-model.md` |
| Databases, PgBouncer, connections, retention | `reference/database.md` |
| BFF, web UI, Teams instead of the web UI | `reference/web.md` |
| Verified versions, upgrading, smoke and load tests | `reference/versions.md` |
