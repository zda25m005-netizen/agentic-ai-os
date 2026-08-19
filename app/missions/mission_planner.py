"""Decompose an Objective into a DAG of subgoals (LLM-backed, defensive).

Each subgoal may depend on earlier ones (by index), forming an acyclic graph the
runtime executes in order. Sanitization keeps only backward dependencies, which
guarantees the result is acyclic; a malformed response falls back to a sensible
research → analyze → report plan.
"""
from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from app.core import llm
from app.missions.objective import Objective

ChatFn = Callable[[list[dict]], Awaitable[str]]
ROLES = ("researcher", "analyst", "executor")

_SYSTEM = (
    "You are a mission planner. Given an objective, output ONLY a JSON array of "
    "subgoals in execution order. Each element: {description (str), depends_on "
    "(list of integer indices of EARLIER subgoals), role (one of 'researcher', "
    "'analyst', 'executor')}. Use the fewest subgoals that achieve the objective."
)
_ARR_RE = re.compile(r"\[.*\]", re.DOTALL)


@dataclass
class SubgoalSpec:
    description: str
    depends_on: list[int] = field(default_factory=list)  # indices of earlier subgoals
    role: str = "researcher"


def _parse_arr(raw: str) -> list:
    m = _ARR_RE.search(raw or "")
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def validate_dag(specs: list[SubgoalSpec]) -> None:
    """Raise if any subgoal depends on a non-earlier index (would allow cycles)."""
    for i, s in enumerate(specs):
        for d in s.depends_on:
            if not (0 <= d < i):
                raise ValueError(f"subgoal {i} depends on invalid/forward index {d}")


def _sanitize(raw_specs: list) -> list[SubgoalSpec]:
    """Coerce raw JSON into SubgoalSpecs, keeping only backward deps (acyclic)."""
    specs: list[SubgoalSpec] = []
    for i, item in enumerate(raw_specs):
        if not isinstance(item, dict):
            continue
        desc = str(item.get("description", "")).strip()
        if not desc:
            continue
        role = item.get("role") if item.get("role") in ROLES else "researcher"
        deps = [d for d in item.get("depends_on", []) if isinstance(d, int) and 0 <= d < i]
        specs.append(SubgoalSpec(description=desc, depends_on=deps, role=role))
    return specs


def _fallback(objective: Objective) -> list[SubgoalSpec]:
    return [
        SubgoalSpec(f"Research and establish a baseline for: {objective.summary}",
                    [], "researcher"),
        SubgoalSpec("Analyze findings and detect notable changes", [0], "analyst"),
        SubgoalSpec("Compile results and prepare a report", [1], "executor"),
    ]


async def plan_objective(objective: Objective, chat_fn: ChatFn | None = None) -> list[SubgoalSpec]:
    """Return an acyclic list of SubgoalSpecs for the objective."""
    chat_fn = chat_fn or llm.chat
    user = f"Objective: {objective.summary}\nSuccess criteria: {objective.success_criteria}"
    raw = await chat_fn([
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": user},
    ])
    specs = _sanitize(_parse_arr(raw)) or _fallback(objective)
    validate_dag(specs)  # invariant (sanitize guarantees it)
    return specs
