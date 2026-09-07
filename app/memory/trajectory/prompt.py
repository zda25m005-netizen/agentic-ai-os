"""Prompt construction + action parsing for the LLM memory policy (config G).

Kept separate from the model so both are unit-testable with no ML dependencies: given a
decision state we build a compact instruction prompt, and given the model's generated text
we parse out one of the six ops (defaulting safely to NOOP when the output is unusable).
"""

from __future__ import annotations

from app.memory.trajectory.actions import OPS, MemoryOp, parse_op

SYSTEM = (
    "You are the memory controller for an AI agent. Given the agent's latest observation "
    "and the current memory state, choose exactly ONE action:\n"
    "STORE (save a new fact), RETRIEVE (load relevant memories), UPDATE (correct an "
    "existing fact), SUMMARIZE (compress memory when it is over budget), DISCARD (drop "
    "noise), or NOOP (do nothing, e.g. an exact duplicate).\n"
    "Reply with ONLY the action word."
)


def _memory_state_line(ms: dict) -> str:
    size = ms.get("size", 0)
    budget = ms.get("budget", 0)
    over = " (OVER BUDGET)" if budget and size > budget else ""
    sim = "a similar memory exists" if ms.get("has_similar") else "no similar memory"
    return f"stored items: {size}/{budget}{over}; {sim}"


def build_prompt(state: dict) -> list[dict]:
    """Build a chat-style message list for one decision (model-agnostic)."""
    user = (
        f"Observation: {state.get('observation', '')}\n"
        f"Memory state: {_memory_state_line(state.get('memory_state', {}))}\n"
        f"Actions: {', '.join(OPS)}\n"
        "Action:"
    )
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def parse_action(text: str) -> MemoryOp:
    """Parse the model's reply into a MemoryOp; default NOOP if nothing matches."""
    op = parse_op(text)
    return op if op is not None else MemoryOp.NOOP
