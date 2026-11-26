"""A tiny A2A chat client for the terminal.

Works with any A2A agent: it reads the Agent Card, then sends your messages
and prints the streamed answer. All turns use one A2A contextId, so the agent
sees one conversation. When the agent asks for approval, type `approve` or a
reason to reject.

    python chat.py http://hr-agent:8000
"""

import asyncio
import sys
import uuid

import httpx
from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import get_text_parts, new_text_message
from a2a.types import Role, SendMessageRequest, TaskState


async def main(url: str) -> None:
    # Read the Agent Card first: it says who the agent is and how to call it.
    async with httpx.AsyncClient() as http:
        card = await A2ACardResolver(httpx_client=http, base_url=url).get_agent_card()
    # Long read timeout: the stream is quiet while the model thinks or a tool runs
    # (httpx's default of 5 s would cut it off).
    http = httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=300.0))
    client = await create_client(card, client_config=ClientConfig(streaming=True, httpx_client=http))
    print(f"Connected to {card.name}: {card.description}")
    print("Type a message, or 'exit' to quit.\n")

    context_id = str(uuid.uuid4())  # one conversation for the whole session
    pending_task_id = None  # set while the agent waits for an approval

    while True:
        text = (await asyncio.to_thread(input, "you > ")).strip()
        if text in ("exit", "quit"):
            break
        if not text:
            continue

        message = new_text_message(text, role=Role.ROLE_USER, context_id=context_id, task_id=pending_task_id)
        pending_task_id = None
        answering = False
        async for event in client.send_message(SendMessageRequest(message=message)):
            if event.HasField("artifact_update"):  # a chunk of the answer
                if not answering:
                    print("agent > ", end="")
                    answering = True
                print("".join(get_text_parts(event.artifact_update.artifact.parts)), end="", flush=True)
            elif event.HasField("status_update"):
                status = event.status_update.status
                parts_text = "\n".join(get_text_parts(status.message.parts))
                if status.state == TaskState.TASK_STATE_WORKING and parts_text:  # progress
                    print(f"  [{parts_text}]", flush=True)
                elif status.state == TaskState.TASK_STATE_INPUT_REQUIRED:  # waits for approval
                    pending_task_id = event.status_update.task_id
                    print(f"agent > {parts_text}", end="")
                elif status.state == TaskState.TASK_STATE_FAILED:
                    print("agent > (the agent failed)", end="")
        print("\n")

    await client.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python chat.py <agent url>")
    asyncio.run(main(sys.argv[1]))
