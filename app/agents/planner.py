"""Planner agent: decompose a goal into an ordered, typed plan.

Asks the LLM for a JSON array of steps, each tagged with the worker that
should handle it. Parsing is defensive — a malformed response degrades to
a single research step rather than crashing the graph.
"""
from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable

from app.agents.state import AgentState, Step
from app.core import llm

WORKER_TYPES = ("research", "coding", "sql", "browser")

ChatFn = Callable[[list[dict]], Awaitable[str]]

_PLANNER_SYSTEM = (
    "You are a planning agent. Break the user's goal into a short ordered "
    "list of concrete steps. Reply with ONLY a JSON array; each element is "
    '{"description": str, "agent": one of ["research","coding","sql","browser"]}. '
    "Use the fewest steps that fully accomplish the goal. No prose."
)

_JSON_ARRAY_RE = re.compile(r"\[.*\]", re.DOTALL)


def _coerce_step(index: int, raw: dict) -> Step:
    agent = str(raw.get("agent", "research")).lower()
    if agent not in WORKER_TYPES:
        agent = "research"
    return Step(
        id=index,
        description=str(raw.get("description", "")).strip() or "(no description)",
        agent=agent,
        status="pending",
    )


def parse_plan(raw: str, goal: str) -> list[Step]:
    """Parse the LLM's JSON plan; fall back to one research step."""
    match = _JSON_ARRAY_RE.search(raw or "")
    if match:
        try:
            data = json.loads(match.group(0))
            steps = [
                _coerce_step(i, item)
                for i, item in enumerate(data)
                if isinstance(item, dict)
            ]
            if steps:
                return steps
        except (json.JSONDecodeError, TypeError):
            pass
    # Fallback: a single research step covering the whole goal.
    return [Step(id=0, description=goal, agent="research", status="pending")]


async def plan_goal(goal: str, chat_fn: ChatFn | None = None) -> list[Step]:
    """Produce a plan for the goal using the LLM (or an injected chat fn)."""
    chat_fn = chat_fn or llm.chat
    messages = [
        {"role": "system", "content": _PLANNER_SYSTEM},
        {"role": "user", "content": f"Goal: {goal}"},
    ]
    raw = await chat_fn(messages)
    return parse_plan(raw, goal)


async def planner_node(state: AgentState) -> AgentState:
    """Graph node: fill state['plan'] from the goal."""
    goal = state.get("goal", "")
    plan = await plan_goal(goal)
    scratchpad = list(state.get("scratchpad", []))
    scratchpad.append(
        {"node": "planner", "content": f"planned {len(plan)} step(s)"}
    )
    return {"plan": plan, "cursor": 0, "scratchpad": scratchpad}
