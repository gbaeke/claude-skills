# BFF, web UI, Teams and Foundry

## BFF (`bff/main.py`)

The browser never talks to an agent. The BFF serves the UI (`GET /` returns `static/index.html`, so UI and API share
one origin) and:

| Route | Does |
|---|---|
| `GET /api/agent` | name, description, examples from the Agent Card (the UI's header and sample questions) |
| `GET/POST /api/chats`, `GET /api/chats/{id}` | chat list (title = first words of the first message), messages incl. approvals |
| `POST /api/chats/{id}/messages` | calls the agent over A2A and streams UI events as SSE |
| `DELETE /api/chats/{id}` | deletes the agent's thread (`DELETE /threads/{id}`) and the BFF's rows |

UI events: `status` (progress), `token`, `approval` (`text`, `action: {tool, args}`), `done`, `error`. Anything that
fails, including connecting to the agent, becomes an `error` event, so the UI never waits forever.

**Approvals survive reloads:** the BFF stores an `approval` row in `chat_messages` (`data` JSONB with the action and
`decision`). The next message while `pending_task_id` is set is the decision: it is written onto that row instead of
being stored as a user message, and sent with the pending `taskId`. Reopened chats draw decided cards
("✓ Approved") or an open card with buttons.

## Web UI (`bff/static/index.html`)

One static file, no build step. Light theme. Markdown via `marked` + `DOMPurify` from cdnjs (re-rendered on every
token while streaming; plain-text fallback offline). Progress line with a spinner, approval card listing the tool's
arguments, sample-question cards from the Agent Card, auto-growing composer (Enter sends, Shift+Enter newline),
chat list with delete, drawer on phones.

## Teams instead

Replace the BFF with a Teams bot built with the **Microsoft 365 Agents SDK** (Python packages
`microsoft-agents-*`), behind **Azure Bot Service**. It does what the BFF does: map the Teams conversation to a
`contextId`, call the agent over A2A, keep the pending `taskId`, show the approval as an Adaptive Card (in Python,
card actions need custom handlers). Pass the signed-in user's token on for on-behalf-of access downstream.

## On Microsoft Foundry instead

As a **hosted agent** the same graph gets a managed endpoint (Responses API), conversation history, a checkpointer
(`FoundryCheckpointSaver` from `langchain-azure-ai`), the A2A task store (tasks kept 60 days), an Entra agent
identity, sessions that scale per conversation, versions, tracing and Teams / Microsoft 365 publishing.
Limits seen in the docs: incoming A2A is switched on through the API, text only, **no streaming**; publishing to
Teams uses channel translation by default, which has no card actions and no streaming (the native Activity adapter
has both).
