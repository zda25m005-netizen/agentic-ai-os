"""Executor node: run the current plan step, routed by agent type.

Each step is handled by a specialist "worker" — for now every worker is
the LLM under a role-specific system prompt. Real tool calls (RAG, SQL,
Python) are wired in from Day 36; the routing seam here means those slot in
without changing the graph. The node runs ONE step per invocation and
advances the cursor, so the Day 26 loop can re-enter until the plan is done.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.agents.state import AgentState, Step
from app.core import llm

ChatFn = Callable[[list[dict]], Awaitable[str]]

AGENT_PROMPTS = {
    "research": "You are a research agent. Complete the step by providing the "
    "specific information requested. Be concise and factual.",
    "coding": "You are a coding agent. Complete the step by writing the code "
    "needed and stating the result.",
    "sql": "You are a data agent. Complete the step by describing the query "
    "and the result it would return.",
    "browser": "You are a browsing agent. Complete the step using current "
    "web knowledge. Be concise.",
}


def is_done(state: AgentState) -> bool:
    """True when every planned step has been executed."""
    return state.get("cursor", 0) >= len(state.get("plan", []))


async def execute_step(step: Step, chat_fn: ChatFn | None = None) -> str:
    """Run a single step with the worker prompt for its agent type."""
    chat_fn = chat_fn or llm.chat
    system = AGENT_PROMPTS.get(step.get("agent", "research"), AGENT_PROMPTS["research"])
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": step.get("description", "")},
    ]
    return await chat_fn(messages)


async def executor_node(state: AgentState) -> AgentState:
    """Graph node: execute the step at the cursor and advance."""
    plan = state.get("plan", [])
    cursor = state.get("cursor", 0)
    if cursor >= len(plan):
        return {}

    step = plan[cursor]
    result = await execute_step(step)

    new_plan = [dict(s) for s in plan]
    new_plan[cursor]["status"] = "done"
    new_plan[cursor]["result"] = result

    results = list(state.get("results", [])) + [result]
    scratchpad = list(state.get("scratchpad", []))
    scratchpad.append(
        {"node": "executor", "content": f"step {cursor} ({step.get('agent')}) done"}
    )
    return {
        "plan": new_plan,
        "results": results,
        "cursor": cursor + 1,
        "scratchpad": scratchpad,
    }
