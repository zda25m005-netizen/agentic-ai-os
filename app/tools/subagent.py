"""Sub-agent tool: delegate a sub-goal to a fresh run of the agent graph.

This makes the system recursive — a worker step can spin up a whole
Planner -> Executor -> Critic run on a narrower goal and fold the result
back in. `run_agent` is imported lazily to avoid an import cycle
(graph -> executor -> tools -> graph).
"""
from __future__ import annotations

from app.tools.registry import tool


@tool(
    name="delegate",
    description="Delegate a self-contained sub-goal to a nested agent run.",
    parameters={
        "type": "object",
        "properties": {
            "subgoal": {"type": "string", "description": "A focused sub-task to solve"},
        },
        "required": ["subgoal"],
    },
)
async def delegate(subgoal: str) -> str:
    """Tool handler: run the agent graph on the sub-goal, return its answer."""
    from app.agents.graph import run_agent  # lazy import breaks the cycle

    state = await run_agent(subgoal)
    return state.get("answer", "") or "(no result)"
