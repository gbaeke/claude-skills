"""Wraps the deep agent in the A2A protocol.

A deep agent is a library object; this file turns it into a service:

- an Agent Card at /.well-known/agent-card.json (who the agent is, how to call it)
- a JSON-RPC endpoint at / (send a message, stream the answer)

Mapping between A2A and LangGraph:

  A2A contextId        ->  LangGraph thread_id (the conversation)
  WORKING + message    <-  progress: thinking, reading a skill, calling a tool
  streamed artifact    <-  model tokens
  input-required state <-  human-in-the-loop interrupt (approve / reject a tool call)

State: the conversation lives in the LangGraph checkpointer and the A2A tasks
live in the A2A task store, both in PostgreSQL. Nothing is kept in this
process, so you can run several replicas.
"""

import asyncio
import logging
import os
import uuid

import uvicorn
from a2a.helpers import new_data_part, new_task_from_user_message, new_text_part
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import DatabaseTaskStore, TaskUpdater
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill, TaskState
from langchain_core.messages import AIMessageChunk
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.types import Command
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Route

from agent import AgentConfig, build_agent

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
log = logging.getLogger("a2a-wrapper")

AGENT_CONFIG = os.environ["AGENT_CONFIG"]  # which agent this process is
DATABASE_URL = os.environ["DATABASE_URL"]
PUBLIC_URL = os.environ.get("PUBLIC_URL", "http://localhost:8000")
PORT = int(os.environ.get("PORT", "8000"))


def tool_calls_in(update: dict) -> list[dict]:
    """Tool calls the model just asked for, from one LangGraph "updates" event."""
    calls = []
    for node_update in update.values():
        if isinstance(node_update, dict):
            for message in node_update.get("messages", []) or []:
                calls.extend(getattr(message, "tool_calls", None) or [])
    return calls


def describe(call: dict, config: AgentConfig) -> str:
    """Progress text for a tool call the model asked for."""
    name, args = call["name"], call.get("args") or {}
    path = str(args.get("file_path", ""))
    if name == "read_file" and "/skills/" in path:
        return f"Reading the {path.split('/skills/')[1].split('/')[0]} skill…"
    builtin = {"write_todos": "Planning the steps…", "task": "Handing part of the work to a subagent…"}
    return config.progress.get(name) or builtin.get(name) or f"Using {name}…"


def running(action: dict, config: AgentConfig) -> str:
    """Progress text for an approved tool call that runs now."""
    return config.running.get(action["name"]) or f"Running {action['name']}…"


class DeepAgentExecutor(AgentExecutor):
    """Runs one A2A request against the deep agent."""

    def __init__(self, agent, config: AgentConfig):
        self.agent = agent
        self.config = config

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = context.current_task
        if task is None:
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.context_id)

        # One A2A context = one LangGraph thread.
        config = {"configurable": {"thread_id": task.context_id}}
        user_text = context.get_user_input()

        # If the thread is paused on a tool approval, this message is the decision.
        state = await self.agent.aget_state(config)
        if state.interrupts:
            approved = user_text.strip().lower() in ("approve", "approved", "yes", "ok")
            decision = {"type": "approve"} if approved else {"type": "reject", "message": user_text}
            graph_input = Command(resume={"decisions": [decision]})
            action = state.interrupts[0].value["action_requests"][0]
            progress = running(action, self.config) if approved else "Not running the tool, as you asked…"
            # Resuming replays the approved tool call as the first step; announce `progress` then.
            # (Updates published right at the start of a resumed task reach the caller as one
            # status without its message, so the progress waits for that first step.)
            on_replay = {action["name"]: progress}
        else:
            graph_input = {"messages": [{"role": "user", "content": user_text}]}
            on_replay = {}

        # WORKING with a short message: progress the caller can show while it waits.
        await updater.start_work()
        if not on_replay:
            await updater.update_status(TaskState.TASK_STATE_WORKING, updater.new_agent_message([new_text_part("Thinking…")]))

        # Two streams from LangGraph: "messages" for model tokens (the answer), and
        # "updates" for finished steps, where we see which tools the model calls.
        artifact_id = str(uuid.uuid4())
        first = True
        async for mode, data in self.agent.astream(graph_input, config, stream_mode=["messages", "updates"]):
            if mode == "messages":
                chunk, _meta = data
                if isinstance(chunk, AIMessageChunk) and chunk.text:
                    await updater.add_artifact(
                        [new_text_part(chunk.text)], artifact_id=artifact_id, name="answer", append=not first
                    )
                    first = False
            else:
                for call in tool_calls_in(data):
                    text = on_replay.pop(call["name"], None) or describe(call, self.config)
                    log.info("progress: %s", text)
                    await updater.update_status(
                        TaskState.TASK_STATE_WORKING, updater.new_agent_message([new_text_part(text)])
                    )

        # Paused for approval? Tell the caller which tool call waits, and stop.
        state = await self.agent.aget_state(config)
        if state.interrupts:
            action = state.interrupts[0].value["action_requests"][0]
            await updater.requires_input(
                updater.new_agent_message(
                    [
                        new_text_part(f"Approve {action['name']}? Reply 'approve' or give a reason to reject."),
                        new_data_part({"tool": action["name"], "args": action["args"]}),
                    ]
                )
            )
            return

        await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("cancel is not supported")


def agent_card(config: AgentConfig) -> AgentCard:
    """The Agent Card: a JSON description of the agent and how to call it."""
    return AgentCard(
        name=config.display_name,
        description=config.description,
        version="0.1.0",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=True),
        supported_interfaces=[AgentInterface(protocol_binding="JSONRPC", url=PUBLIC_URL, protocol_version="1.0")],
        skills=[
            AgentSkill(
                id=config.name,
                name=config.display_name,
                description=config.description,
                tags=[config.name],
                examples=config.examples,
            )
        ],
    )


async def wait_for_agent(config: AgentConfig, checkpointer):
    """The MCP server may start after us; retry until its tools load."""
    for attempt in range(30):
        try:
            return await build_agent(config, checkpointer)
        except Exception as exc:  # noqa: BLE001
            log.info("waiting for MCP server (%s): %s", attempt + 1, type(exc).__name__)
            await asyncio.sleep(2)
    raise RuntimeError("MCP server not reachable")


async def main():
    config = AgentConfig.load(AGENT_CONFIG)
    log.info("starting agent %s", config.name)
    # Each agent has its own database (DATABASE_URL), so agents never share tables.
    async with AsyncPostgresSaver.from_conn_string(DATABASE_URL) as checkpointer:
        await checkpointer.setup()  # creates the checkpoint tables once; safe to repeat
        agent = await wait_for_agent(config, checkpointer)

        # A2A tasks in PostgreSQL too, so every replica sees every task.
        engine = create_async_engine(DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1))
        task_store = DatabaseTaskStore(engine, table_name="a2a_tasks")

        async def delete_thread(request):
            """Forget a conversation: its checkpoints and its A2A tasks.

            A2A has no "delete conversation" call, so this is a small extra
            endpoint next to the A2A routes. The BFF calls it when a chat is deleted.
            """
            context_id = request.path_params["context_id"]
            await checkpointer.adelete_thread(context_id)
            async with engine.begin() as conn:
                await conn.execute(text("DELETE FROM a2a_tasks WHERE context_id = :c"), {"c": context_id})
            log.info("deleted thread %s", context_id)
            return Response(status_code=204)

        card = agent_card(config)
        handler = DefaultRequestHandler(
            agent_executor=DeepAgentExecutor(agent, config), task_store=task_store, agent_card=card
        )
        app = Starlette(
            routes=[
                *create_agent_card_routes(card),
                *create_jsonrpc_routes(handler, "/"),
                Route("/threads/{context_id}", delete_thread, methods=["DELETE"]),
            ]
        )
        await uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=PORT)).serve()


if __name__ == "__main__":
    asyncio.run(main())
