"""One A2A turn, shared by smoke.py and stress.py."""

import time

import httpx
from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import get_text_parts, new_text_message
from a2a.types import Role, SendMessageRequest, TaskState

# Long read timeout: the stream is quiet while the model thinks or a tool runs.
TIMEOUT = httpx.Timeout(10.0, read=300.0)


async def get_card(url: str):
    async with httpx.AsyncClient(timeout=10) as http:
        return await A2ACardResolver(httpx_client=http, base_url=url).get_agent_card()


class Session:
    """An A2A client on its own HTTP connection. Close it to release the connection."""

    def __init__(self, card):
        self.card = card

    async def __aenter__(self):
        self.http = httpx.AsyncClient(timeout=TIMEOUT)
        self.client = await create_client(self.card, client_config=ClientConfig(streaming=True, httpx_client=self.http))
        return self

    async def __aexit__(self, *_):
        await self.client.close()  # does not close a client it was given ...
        await self.http.aclose()  # ... so close the HTTP client too

    async def turn(self, context_id: str, text: str, task_id: str | None = None, on_event=None) -> dict:
        """Send one message and follow the stream to the end. Returns what happened."""
        t0 = time.perf_counter()
        result = {"state": None, "task": None, "answer": "", "progress": [], "ttft": None, "prompt": ""}
        message = new_text_message(text, role=Role.ROLE_USER, context_id=context_id, task_id=task_id)
        async for event in self.client.send_message(SendMessageRequest(message=message)):
            if event.HasField("artifact_update"):
                result["answer"] += "".join(get_text_parts(event.artifact_update.artifact.parts))
                result["ttft"] = result["ttft"] or time.perf_counter() - t0
            elif event.HasField("status_update"):
                status = event.status_update.status
                result["state"], result["task"] = status.state, event.status_update.task_id
                text_parts = "".join(get_text_parts(status.message.parts))
                if status.state == TaskState.TASK_STATE_WORKING and text_parts:
                    result["progress"].append(text_parts)
                if status.state == TaskState.TASK_STATE_INPUT_REQUIRED:
                    result["prompt"] = text_parts
            if on_event:
                on_event(event)
        result["total"] = time.perf_counter() - t0
        return result


def state_name(state) -> str:
    return TaskState.Name(state) if state is not None else "NONE"
