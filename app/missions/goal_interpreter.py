"""Turn a raw user goal into a structured Objective (LLM-backed, defensive).

Parsing is defensive: malformed LLM output degrades to a sensible one-shot
objective rather than crashing. `chat_fn` is injectable, so this is unit-tested
with a fake — no network in CI.
"""
from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable

from app.core import llm
from app.missions.objective import HORIZONS, Objective

ChatFn = Callable[[list[dict]], Awaitable[str]]

_SYSTEM = (
    "You convert a user's goal into a structured objective. Reply with ONLY a "
    "JSON object with keys: summary (str), success_criteria (list of str), "
    "constraints (list of str), notify_conditions (list of str), deadline_days "
    "(int or null), horizon (one of 'one_shot', 'monitoring', 'investigation'). "
    "Infer a sensible horizon: recurring watches are 'monitoring', dig-until-"
    "resolved tasks are 'investigation', single answers are 'one_shot'."
)
_OBJ_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_obj(raw: str) -> dict:
    m = _OBJ_RE.search(raw or "")
    if not m:
        return {}
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _as_str_list(v) -> list[str]:
    if isinstance(v, list):
        return [str(x) for x in v if str(x).strip()]
    return []


async def interpret_goal(goal: str, chat_fn: ChatFn | None = None) -> Objective:
    """Return a structured Objective for `goal`; fall back to one-shot on failure."""
    chat_fn = chat_fn or llm.chat
    raw = await chat_fn([
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": goal},
    ])
    d = _parse_obj(raw)
    if not d.get("summary"):
        return Objective(summary=goal, success_criteria=[goal])  # safe fallback

    horizon = d.get("horizon")
    if horizon not in HORIZONS:
        horizon = "one_shot"
    deadline = d.get("deadline_days")
    deadline = int(deadline) if isinstance(deadline, (int, float)) else None

    return Objective(
        summary=str(d["summary"]),
        success_criteria=_as_str_list(d.get("success_criteria")) or [goal],
        constraints=_as_str_list(d.get("constraints")),
        notify_conditions=_as_str_list(d.get("notify_conditions")),
        deadline_days=deadline,
        horizon=horizon,
    )
