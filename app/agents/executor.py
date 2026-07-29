"""Executor node: run the current plan step with tools, routed by agent type.

Each step runs through the tool-use loop, so a worker can call any
registered tool (web search, python, sql, rag, files, ...) to complete its
task — not just describe it. The node runs ONE step per invocation and
advances the cursor so the Day 26 loop can re-enter until the plan is done.
"""
from __future__ import annotations

import app.tools  # noqa: F401  (import registers all tools into the registry)
from app.agents.state import AgentState, Step
from app.agents.tool_loop import ChatRawFn, run_with_tools
from app.tools.registry import ToolRegistry

AGENT_PROMPTS = {
    "research": "You are a research agent. Complete the step by providing the "
    "specific information requested. Use tools (web_search, rag_search, "
    "wikipedia) when they help; otherwise answer directly. Be concise.",
    "coding": "You are a coding agent. Complete the step; use the python_exec "
    "or calculator tool to run code, then state the result. Be concise.",
    "sql": "You are a data agent. Use the sql_query or analyze_csv tool to "
    "answer from data, then summarize the result. Be concise.",
    "browser": "You are a browsing agent. Use web_search or http_get to gather "
    "current information, then answer concisely.",
}


def is_done(state: AgentState) -> bool:
    """True when every planned step has been executed."""
    return state.get("cursor", 0) >= len(state.get("plan", []))


async def execute_step(
    step: Step,
    chat_raw: ChatRawFn | None = None,
    registry: ToolRegistry | None = None,
) -> str:
    """Run a single step via the tool-use loop with its worker prompt."""
    system = AGENT_PROMPTS.get(step.get("agent", "research"), AGENT_PROMPTS["research"])
    system += " Respond in plain text only — no LaTeX, markdown math, or code fences."
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": step.get("description", "")},
    ]
    return await run_with_tools(messages, registry=registry, chat_raw=chat_raw)


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
