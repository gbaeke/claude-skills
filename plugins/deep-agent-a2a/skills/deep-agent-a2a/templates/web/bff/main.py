"""Backend for frontend (BFF) for the web UI.

The browser never talks to the agent. It talks to this service, which:

- keeps the list of chats (id + title) and their messages for display,
- calls the agent over A2A, one A2A contextId per chat,
- streams the agent's answer back to the browser as Server-Sent Events.

The chat id IS the A2A contextId, which the agent uses as its LangGraph
thread_id. Reopening an old chat and sending a message continues that thread.

For Teams, a Teams bot (Microsoft 365 Agents SDK) plays exactly this role.
"""

import json
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import psycopg
from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import get_text_parts, new_text_message
from a2a.types import Role, SendMessageRequest, TaskState
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from google.protobuf.json_format import MessageToDict
from pydantic import BaseModel

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")
AGENT_URL = os.environ.get("AGENT_URL", "http://localhost:8000")
AGENT_SERVICE = os.environ.get("AGENT_SERVICE", "agent")  # for the "check the logs" hint
STATIC = Path(__file__).parent / "static"
# httpx waits 5 s by default. On a streamed A2A call that is the gap allowed
# between events, and the agent stays silent while the model thinks or a tool
# runs. So: quick connect, but a long wait for the next event.
A2A_TIMEOUT = httpx.Timeout(10.0, read=300.0)

SCHEMA = """
CREATE TABLE IF NOT EXISTS chats (
    id TEXT PRIMARY KEY,                 -- = A2A contextId = LangGraph thread_id
    title TEXT NOT NULL,
    pending_task_id TEXT,                -- A2A task waiting for an approval, if any
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS chat_messages (
    id BIGSERIAL PRIMARY KEY,
    chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    role TEXT NOT NULL,                  -- 'user', 'agent' or 'approval'
    text TEXT NOT NULL,
    data JSONB,                          -- approval only: {"action": {...}, "decision": null | "approved" | "rejected"}
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS data JSONB;  -- for databases made before this column
"""


async def db():
    return await psycopg.AsyncConnection.connect(DATABASE_URL, autocommit=True)


@asynccontextmanager
async def lifespan(_app):
    async with await db() as conn:
        await conn.execute(SCHEMA)
    yield


app = FastAPI(title="BFF", lifespan=lifespan)


class NewMessage(BaseModel):
    text: str


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/agent")
async def agent_info():
    """Name, description and sample questions from the agent's Agent Card, for the UI."""
    async with httpx.AsyncClient(timeout=10) as http:
        card = await A2ACardResolver(httpx_client=http, base_url=AGENT_URL).get_agent_card()
    examples = [e for skill in card.skills for e in skill.examples]
    return {"name": card.name, "description": card.description, "examples": examples, "service": AGENT_SERVICE}


@app.get("/api/chats")
async def list_chats():
    async with await db() as conn:
        rows = await (await conn.execute("SELECT id, title FROM chats ORDER BY created_at DESC")).fetchall()
    return [{"id": r[0], "title": r[1]} for r in rows]


@app.post("/api/chats")
async def new_chat():
    chat_id = str(uuid.uuid4())
    async with await db() as conn:
        await conn.execute("INSERT INTO chats (id, title) VALUES (%s, 'New chat')", (chat_id,))
    return {"id": chat_id, "title": "New chat"}


@app.get("/api/chats/{chat_id}")
async def get_chat(chat_id: str):
    async with await db() as conn:
        chat = await (await conn.execute("SELECT title, pending_task_id FROM chats WHERE id=%s", (chat_id,))).fetchone()
        rows = await (
            await conn.execute("SELECT role, text, data FROM chat_messages WHERE chat_id=%s ORDER BY id", (chat_id,))
        ).fetchall()
    messages = [{"role": r[0], "text": r[1], "data": r[2]} for r in rows]
    return {"id": chat_id, "title": chat[0], "pending": chat[1] is not None, "messages": messages}


@app.delete("/api/chats/{chat_id}", status_code=204)
async def delete_chat(chat_id: str):
    """Delete a chat everywhere: the agent's thread first, then our own rows."""
    async with httpx.AsyncClient() as http:
        (await http.delete(f"{AGENT_URL}/threads/{chat_id}")).raise_for_status()
    async with await db() as conn:
        await conn.execute("DELETE FROM chats WHERE id=%s", (chat_id,))  # messages go with it (ON DELETE CASCADE)


@app.post("/api/chats/{chat_id}/messages")
async def send_message(chat_id: str, body: NewMessage):
    async with await db() as conn:
        chat = await (await conn.execute("SELECT title, pending_task_id FROM chats WHERE id=%s", (chat_id,))).fetchone()
        if chat[1]:
            # The chat waits for an approval, so this message is the decision: record it on
            # the approval itself (the card shows it), not as a separate user message.
            decision = "approved" if body.text.strip().lower() in ("approve", "approved", "yes", "ok") else "rejected"
            await conn.execute(
                """UPDATE chat_messages SET data = jsonb_set(data, '{decision}', to_jsonb(%s::text))
                   WHERE id = (SELECT max(id) FROM chat_messages WHERE chat_id=%s AND role='approval')""",
                (decision, chat_id),
            )
        else:
            await conn.execute("INSERT INTO chat_messages (chat_id, role, text) VALUES (%s, 'user', %s)", (chat_id, body.text))
        if chat[0] == "New chat":  # name the chat after its first message
            await conn.execute("UPDATE chats SET title=%s WHERE id=%s", (title_from(body.text), chat_id))
    return StreamingResponse(stream_from_agent(chat_id, body.text, pending_task_id=chat[1]), media_type="text/event-stream")


def title_from(text: str) -> str:
    words = text.split()
    return " ".join(words[:6]) + ("…" if len(words) > 6 else "")


def sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


async def stream_from_agent(chat_id: str, text: str, pending_task_id: str | None):
    """Call the agent over A2A and turn its events into simple UI events."""
    answer = ""
    # If the agent asked for an approval, this message answers that same A2A task.
    message = new_text_message(text, role=Role.ROLE_USER, context_id=chat_id, task_id=pending_task_id)
    client = None
    # Our own httpx client, for the timeout. The A2A client won't close a client it
    # was given, so we close it ourselves in `finally`.
    http = httpx.AsyncClient(timeout=A2A_TIMEOUT)
    try:
        config = ClientConfig(streaming=True, httpx_client=http)
        client = await create_client(AGENT_URL, client_config=config)
        async for event in client.send_message(SendMessageRequest(message=message)):
            if event.HasField("artifact_update"):  # a chunk of the answer
                chunk = "".join(get_text_parts(event.artifact_update.artifact.parts))
                answer += chunk
                yield sse({"type": "token", "text": chunk})
            elif event.HasField("status_update"):
                status = event.status_update.status
                if status.state == TaskState.TASK_STATE_WORKING and status.HasField("message"):  # progress
                    yield sse({"type": "status", "text": "".join(get_text_parts(status.message.parts))})
                elif status.state == TaskState.TASK_STATE_INPUT_REQUIRED:  # human-in-the-loop
                    parts = status.message.parts
                    action = next((MessageToDict(p)["data"] for p in parts if p.HasField("data")), {})
                    prompt = "".join(get_text_parts(parts))
                    await save(chat_id, answer, pending_task_id=event.status_update.task_id, approval=(prompt, action))
                    yield sse({"type": "approval", "text": prompt, "action": action})
                    return
                if status.state == TaskState.TASK_STATE_FAILED:
                    yield sse({"type": "error", "text": "The agent failed."})
        await save(chat_id, answer, pending_task_id=None)
        yield sse({"type": "done"})
    except Exception as exc:  # noqa: BLE001  (agent down, model error, ...): tell the UI
        yield sse({"type": "error", "text": f"{type(exc).__name__}: {exc}"})
    finally:
        if client is not None:
            await client.close()
        await http.aclose()


async def save(chat_id: str, answer: str, pending_task_id: str | None, approval: tuple[str, dict] | None = None):
    async with await db() as conn:
        if answer:
            await conn.execute("INSERT INTO chat_messages (chat_id, role, text) VALUES (%s, 'agent', %s)", (chat_id, answer))
        if approval:  # keep the proposed tool call, so a reopened chat can show the card again
            prompt, action = approval
            await conn.execute(
                "INSERT INTO chat_messages (chat_id, role, text, data) VALUES (%s, 'approval', %s, %s::jsonb)",
                (chat_id, prompt, json.dumps({"action": action, "decision": None})),
            )
        await conn.execute("UPDATE chats SET pending_task_id=%s WHERE id=%s", (pending_task_id, chat_id))
