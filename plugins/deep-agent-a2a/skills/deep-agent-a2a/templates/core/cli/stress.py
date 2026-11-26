"""Load test for any A2A agent: many conversations at once.

    python stress.py http://my-agent:8000 [concurrency=10] [conversations=20]

Each conversation sends one of the Agent Card's examples. If the agent asks for
approval, the approval goes out on a new connection, so with several replicas
it can land on a different one than the turn that paused. Every turn uses
real model calls, so keep the numbers modest.

Watch the database side while it runs:
    docker compose exec -e PGPASSWORD=postgres postgres \\
      psql -h pgbouncer -p 6432 -U postgres -d pgbouncer -c "SHOW POOLS"
"""

import asyncio
import sys
import time
import uuid

from a2a.types import TaskState

from a2a_turn import Session, get_card, state_name


async def conversation(card, question: str) -> dict:
    ctx, turns = str(uuid.uuid4()), []
    try:
        async with Session(card) as s:
            turns.append(await s.turn(ctx, question))
        if turns[0]["state"] == TaskState.TASK_STATE_INPUT_REQUIRED:
            async with Session(card) as s:  # new connection: may reach another replica
                turns.append(await s.turn(ctx, "approve", task_id=turns[0]["task"]))
        ok = turns[-1]["state"] == TaskState.TASK_STATE_COMPLETED
        return {"ok": ok, "err": None if ok else f"ended in {state_name(turns[-1]['state'])}", "turns": turns}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "err": f"{type(e).__name__}: {str(e)[:120]}", "turns": turns}


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, round(p / 100 * (len(xs) - 1)))] if xs else float("nan")


async def main(url: str, conc: int, total: int) -> None:
    card = await get_card(url)
    examples = [e for s in card.skills for e in s.examples] or ["What can you help me with?"]
    sem = asyncio.Semaphore(conc)

    async def run(n):
        async with sem:
            return await conversation(card, examples[n % len(examples)])

    t0 = time.perf_counter()
    res = await asyncio.gather(*(run(n) for n in range(total)))
    wall = time.perf_counter() - t0
    turns = [t for r in res for t in r["turns"]]
    totals = [t["total"] for t in turns]
    ttfts = [t["ttft"] for t in turns if t["ttft"] is not None]
    bad = [r for r in res if not r["ok"]]
    print(f"{card.name}: concurrency={conc} conversations={total} turns={len(turns)} wall={wall:.1f}s")
    print(f"  ok={total - len(bad)} failed={len(bad)}  throughput={len(turns) / wall:.2f} turns/s")
    if totals:
        print(f"  turn time   p50={pct(totals, 50):.1f}s p95={pct(totals, 95):.1f}s max={max(totals):.1f}s")
    if ttfts:
        print(f"  first token p50={pct(ttfts, 50):.1f}s p95={pct(ttfts, 95):.1f}s")
    errors: dict[str, int] = {}
    for r in bad:
        errors[r["err"]] = errors.get(r["err"], 0) + 1
    for err, count in errors.items():
        print(f"  error x{count}: {err}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    args = sys.argv[1:] + [None, None]
    asyncio.run(main(args[0], int(args[1] or 10), int(args[2] or 20)))
