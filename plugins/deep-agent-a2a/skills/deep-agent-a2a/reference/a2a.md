# The A2A wrapper (`agent/main.py`)

A Deep Agents agent is a compiled LangGraph graph: a library object. Open-source LangGraph has no server for it
(LangSmith Deployment has one), so `main.py` adds A2A with the official `a2a-sdk` (protocol 1.0, JSON-RPC
binding, SSE streaming).

## Pieces

- **Agent Card** at `/.well-known/agent-card.json`, built from `agent.toml` (name, description, examples) and
  `PUBLIC_URL`. Clients read it first; the web UI takes its name and sample questions from it.
- **JSON-RPC route** at `/`: `SendStreamingMessage` etc. Requests carry `A2A-Version: 1.0`.
- **`DefaultRequestHandler`** with a **`DatabaseTaskStore`** (`a2a_tasks` table, SQLAlchemy + asyncpg). The
  default task store is in memory per replica: with two replicas an approval lands on a replica that never saw
  the task. Always use the database store.
- **`DeepAgentExecutor.execute()`**: one request = one run of the graph.

## Mapping

| A2A | LangGraph / Deep Agents |
|---|---|
| `contextId` | `thread_id` of the checkpointer |
| `WORKING` status + message | progress: "Thinking…", then one line per tool call (from `stream_mode="updates"`) |
| artifact chunks (`append: true` after the first) | model tokens (`stream_mode="messages"`, `AIMessageChunk.text`) |
| `INPUT_REQUIRED` + text part + data part `{tool, args}` | interrupt from `interrupt_on` (HumanInTheLoopMiddleware) |
| next message on the same `taskId` | `Command(resume={"decisions": [{"type": "approve"}]})` or `{"type": "reject", "message": ...}` |
| `COMPLETED` / `FAILED` | run finished / exception |

The wrapper decides "is this a decision?" from the **checkpoint** (`state.interrupts`), not from the task state, so a
lost task never breaks the conversation. "approve" / "yes" / "ok" approve; any other text rejects with that reason.

## Traps already hit

- **Progress at the start of a resumed task is lost.** Status updates published right after a resumed task starts
  reach the client as one status without its message. So on resume the wrapper sends a plain `start_work()` and
  announces the approved tool ("Saving the note…") when LangGraph replays that tool call as its first step
  (`on_replay`). New tasks send "Thinking…" as a second update after `start_work()`.
- **The replayed tool call shows up again in `updates`.** Without `on_replay` it would be announced twice.
- **Client read timeout.** httpx waits 5 s between stream events by default; the agent is silent while the model
  thinks. Clients use `httpx.Timeout(10.0, read=300.0)`. Progress updates also shorten the silences.
- **The A2A client doesn't close an httpx client you pass in** (`ClientConfig(httpx_client=...)`). Close it yourself
  (`finally: await http.aclose()`), or one leaks per request.
- **A2A has no "delete conversation".** `DELETE /threads/{contextId}` next to the A2A routes deletes the checkpoints
  (`checkpointer.adelete_thread`) and the context's rows in `a2a_tasks`. The BFF calls it when a chat is deleted.
- **Types are protobuf** in a2a-sdk 1.x: use `event.HasField("status_update")`, `TaskState.TASK_STATE_*`,
  `a2a.helpers` (`new_text_message`, `new_text_part`, `new_data_part`, `get_text_parts`), `MessageToDict` for data
  parts. Old 0.x samples (`TaskState.working`, `Part(root=TextPart(...))`) don't apply.

## Streamed turn, as captured

```
POST / · Accept: text/event-stream · A2A-Version: 1.0 · {"method": "SendStreamingMessage", ...}
← task                SUBMITTED
← statusUpdate        WORKING
← statusUpdate        WORKING  "Thinking…"
← statusUpdate        WORKING  "Reading the note-writing skill…"
← statusUpdate        WORKING  "Preparing a note…"
← statusUpdate        INPUT_REQUIRED  [text "Approve save_note? …", data {tool, args}]
(next request, same contextId + taskId, text "approve")
← statusUpdate        WORKING
← statusUpdate        WORKING  "Saving the note on the MCP server…"
← artifactUpdate ×N   "Saved: …" (append)
← statusUpdate        COMPLETED
```
