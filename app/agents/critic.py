"""Critic / Reviewer node: judge each step's result and drive retries.

After the Executor runs a step, the Critic asks the LLM whether the result
actually satisfies the step. On APPROVE the graph moves on; on RETRY it
rolls the cursor back so the Executor re-runs the step — but only up to
MAX_RETRIES, so the loop always terminates.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.agents.state import AgentState
from app.core import llm

ChatFn = Callable[[list[dict]], Awaitable[str]]

MAX_RETRIES = 2

APPROVE = "approve"
RETRY = "retry"

_CRITIC_SYSTEM = (
    "You are a strict reviewer. Decide whether the RESULT adequately "
    "completes the STEP. Reply with exactly 'APPROVE' if it does, or "
    "'RETRY: <one-line reason>' if it does not."
)


async def review(
    step_description: str, result: str, chat_fn: ChatFn | None = None
) -> tuple[str, str]:
    """Return (verdict, reason). verdict is APPROVE or RETRY."""
    chat_fn = chat_fn or llm.chat
    user = f"STEP: {step_description}\n\nRESULT: {result}"
    messages = [
        {"role": "system", "content": _CRITIC_SYSTEM},
        {"role": "user", "content": user},
    ]
    raw = (await chat_fn(messages)).strip()
    if raw.lower().startswith("approve"):
        return APPROVE, ""
    reason = raw.split(":", 1)[1].strip() if ":" in raw else raw
    return RETRY, reason


async def critic_node(state: AgentState) -> AgentState:
    """Graph node: review the most recently executed step."""
    plan = state.get("plan", [])
    cursor = state.get("cursor", 0)
    results = state.get("results", [])
    retries = state.get("retries", 0)
    idx = cursor - 1  # the step the Executor just ran

    if idx < 0 or not results:
        return {}

    verdict, reason = await review(plan[idx].get("description", ""), results[-1])
    scratchpad = list(state.get("scratchpad", []))

    if verdict == RETRY and retries < MAX_RETRIES:
        # Roll back: re-run the step, drop its result, count the retry.
        new_plan = [dict(s) for s in plan]
        new_plan[idx]["status"] = "pending"
        new_plan[idx].pop("result", None)
        scratchpad.append(
            {"node": "critic", "content": f"retry step {idx}: {reason}"}
        )
        return {
            "plan": new_plan,
            "results": results[:-1],
            "cursor": idx,
            "retries": retries + 1,
            "verdict": RETRY,
            "scratchpad": scratchpad,
        }

    # Approve — or retries exhausted, accept and move on.
    note = "approved" if verdict == APPROVE else f"accepted after {retries} retries"
    scratchpad.append({"node": "critic", "content": f"step {idx} {note}"})
    return {"retries": 0, "verdict": APPROVE, "scratchpad": scratchpad}
