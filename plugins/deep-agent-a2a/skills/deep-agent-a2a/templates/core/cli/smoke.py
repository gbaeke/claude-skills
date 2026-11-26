"""Smoke test for any A2A agent: one conversation, end to end.

    python smoke.py http://my-agent:8000 ["question"]

1. sends the question (default: the last example in the Agent Card),
2. approves a tool call if the agent asks for one, on a new connection (so it can
   land on another replica),
3. asks a follow-up in the same conversation, to prove the checkpoint keeps it.

Prints every progress line and exits non-zero if a turn doesn't complete.
"""

import asyncio
import sys
import uuid

from a2a.types import TaskState

from a2a_turn import Session, get_card, state_name


def report(label: str, r: dict) -> None:
    print(f"--- {label}: {state_name(r['state'])} in {r['total']:.1f}s")
    for line in r["progress"]:
        print(f"    [{line}]")
    if r["prompt"]:
        print(f"    asks: {r['prompt']}")
    if r["answer"]:
        print(f"    answer: {r['answer'][:300]}")


async def main(url: str, question: str | None) -> int:
    card = await get_card(url)
    examples = [e for s in card.skills for e in s.examples]
    question = question or (examples[-1] if examples else "What can you help me with?")
    print(f"Agent: {card.name} ({card.supported_interfaces[0].url})")
    ctx = str(uuid.uuid4())

    async with Session(card) as s:
        r1 = await s.turn(ctx, question)
    report(f"turn 1: {question}", r1)
    if r1["state"] == TaskState.TASK_STATE_INPUT_REQUIRED:
        async with Session(card) as s:  # new connection for the approval
            r2 = await s.turn(ctx, "approve", task_id=r1["task"])
        report("approve (same taskId)", r2)
        if r2["state"] != TaskState.TASK_STATE_COMPLETED or r2["task"] != r1["task"]:
            return 1
    elif r1["state"] != TaskState.TASK_STATE_COMPLETED:
        return 1

    async with Session(card) as s:
        r3 = await s.turn(ctx, "In one sentence: what did I just ask you?")
    report("follow-up (same contextId)", r3)
    ok = r3["state"] == TaskState.TASK_STATE_COMPLETED and r3["answer"]
    print("OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(asyncio.run(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)))
