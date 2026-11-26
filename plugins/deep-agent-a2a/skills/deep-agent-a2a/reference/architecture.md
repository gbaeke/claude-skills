# Architecture

```
Web UI ──HTTP+SSE──▶ BFF ──A2A──▶ <agent>-agent ──MCP──▶ mcp-server
CLI ─────────────A2A──────────▶ any agent       ──Responses API──▶ AI gateway ──▶ LLM
every service ──▶ PgBouncer :6432 ──▶ PostgreSQL :5432 (db per agent + bff)
```

| Component | Owns | State |
|---|---|---|
| Web UI (`bff/static/index.html`) | chat list, streaming Markdown, progress line, approval cards | none |
| BFF (`bff/main.py`) | maps a chat to an A2A `contextId`, turns A2A events into UI events, keeps the pending `taskId` | `chats`, `chat_messages` (db `bff`) |
| A2A wrapper (`agent/main.py`) | Agent Card, JSON-RPC route, `AgentExecutor`, progress, approvals, `DELETE /threads/{contextId}` | A2A tasks (table `a2a_tasks`) |
| Deep agent (`agent/agent.py`) | model, system prompt, MCP tools, skills, hook, `interrupt_on`, checkpointer | checkpoints (LangGraph tables) |
| Agent config (`agent/agents/<name>/`) | `agent.toml` + `skills/` | read-only, in the image |
| MCP server (`mcp-server/`) | tools | none (stateless HTTP) |
| PgBouncer | few real connections per database, lent per transaction | none |

## One turn

1. UI posts the text to the BFF; the BFF calls the agent with `SendStreamingMessage` (`contextId` = chat id).
2. The wrapper creates (or loads) the A2A task, maps `contextId` to the LangGraph `thread_id`, checks the
   checkpoint for a pending approval, sends `WORKING` + progress, and streams the run.
3. Tool calls show up as progress; a tool in `approve_tools` interrupts the run; the wrapper answers with
   `input-required` and the tool call as a data part. The BFF stores it as an approval card.
4. The decision goes back on the **same** `contextId` and `taskId`; the run resumes from the checkpoint, the tool
   runs on the MCP server, the answer streams as artifact chunks, the task completes.

## Scaling

`docker compose up -d --scale <agent>-agent=3`. Works because nothing lives in the process. The open SSE stream of
one answer is the only thing tied to a replica: if it dies mid-answer the stream breaks, the checkpoint keeps the
work, and the next message continues. Load balancing is per connection, so long streams spread unevenly.

Sizing from a load test (gateway on the host, Luna): 20-40 parallel conversations, no errors, turn p50 2-3 s; the
model quota is the first limit, not the agent or PostgreSQL (2 ms per checkpoint transaction). Concurrency in
practice: turns/second × seconds/turn; 2,000 users × 10 turns/day ≈ 2 concurrent turns, peaks ≈ 10.

## Teams and Foundry

Teams replaces the web UI and BFF: Teams → Azure Bot Service → a Teams bot (Microsoft 365 Agents SDK) that calls
the agent over A2A, maps the Teams conversation to `contextId` and shows approvals as an Adaptive Card. The agent,
MCP server and database don't change. On Microsoft Foundry hosted agents, the platform provides the endpoint,
conversation state (`FoundryCheckpointSaver`), the A2A task store and Teams publishing; see `web.md`.
