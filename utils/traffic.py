"""Seed traffic: runs the seed conversations through the agent so later modules have traces."""

import json
import time
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from langchain_core.tracers.langchain import wait_for_all_tracers

from utils.config import REPO_ROOT, load_active_agent

SEED_FILE = REPO_ROOT / "data" / "seed_conversations.json"
SOURCE = "tour-seed"
MAX_CONCURRENCY = 5
# deepagents defaults to 9,999 steps; bound a model that keeps guessing IDs.
RECURSION_LIMIT = 150


def load_seed_conversations() -> list[dict]:
    """Return the seed threads, each `{"id", "category", "turns"}`."""
    return json.loads(SEED_FILE.read_text())


def run_thread(agent, seed: dict, thread_id: str) -> int:
    """Send each turn of one seed thread to `agent` in order; return the number of turns."""
    for turn, text in enumerate(seed["turns"], start=1):
        config = {
            "configurable": {"thread_id": thread_id},
            # langchain-core no longer copies configurable keys into run metadata.
            "metadata": {
                "source": SOURCE,
                "thread_id": thread_id,
                "turn": turn,
                "seed_id": seed["id"],
                "category": seed["category"],
            },
            "recursion_limit": RECURSION_LIMIT,
        }
        agent.invoke({"messages": [{"role": "user", "content": text}]}, config=config)
    return len(seed["turns"])


def generate_traffic(threads: int = 24, *, build_agent=load_active_agent) -> list[str]:
    """Run `threads` seed threads (cycling the seed file) 5 at a time; return their thread IDs."""
    seeds = load_seed_conversations()
    jobs = [(seeds[i % len(seeds)], str(uuid4())) for i in range(threads)]

    def run_job(seed: dict, thread_id: str) -> int:
        return run_thread(build_agent(), seed, thread_id)

    started = time.monotonic()
    turns = 0
    failed = 0
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENCY) as pool:
        futures = [pool.submit(run_job, seed, thread_id) for seed, thread_id in jobs]
        for (seed, _), future in zip(jobs, futures):
            error = future.exception()
            if error is not None:
                failed += 1
                print(f"Thread {seed['id']} failed: {type(error).__name__}: {str(error)[:120]}")
            else:
                turns += future.result()
    wait_for_all_tracers()

    minutes, seconds = divmod(int(time.monotonic() - started), 60)
    print(f"Threads: {threads} · turns: {turns} · failed: {failed} · {minutes}m {seconds:02d}s")
    return [thread_id for _, thread_id in jobs]
