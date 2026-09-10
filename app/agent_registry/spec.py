"""Generate a proposed agent specification from a natural-language description.

Deterministic by default (works with no LLM): the description is matched to the closest
built-in template to seed tools/purpose/character, and schedule/approval are inferred from
explicit cues in the text. When an LLM is configured, `generate_spec` can refine the draft,
but always falls back to the deterministic draft — so the create flow never depends on a model.

This proposes a spec for the user to edit; it does not persist anything and invents no
capabilities beyond the real templates/tools already in the system.
"""

from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable

from app.agent_registry.characters import suggest_character_for_work
from app.agent_registry.templates import TEMPLATE_MAP

ChatFn = Callable[[list[dict]], Awaitable[str]]

# keyword -> template id (first match wins, in this order)
_ROUTES: list[tuple[str, str]] = [
    (r"\b(phd|doctoral|doctorate)\b", "phd-finder"),
    (r"\b(scholarship|scholarships|bursary)\b", "scholarship-finder"),
    (r"\b(resume|cv)\b", "resume-optimizer"),
    (r"\b(statement of purpose|sop|personal statement)\b", "sop-builder"),
    (r"\b(interview|interviews)\b", "interview-coach"),
    (r"\b(job|jobs|hiring|opening|openings|vacanc|career page|opportunit)", "job-search"),
    (r"\b(email|inbox|reply|replies)\b", "email-assistant"),
    (r"\b(sales|prospect|prospects|lead|leads|outreach)\b", "sales-research"),
    (r"\b(dataset|datasets|csv|spreadsheet|analy[sz])", "data-analyst"),
    (r"\b(research|paper|papers|literature|arxiv|cite|citation)", "research"),
]

_DEFAULT_NAME = {
    "job-search": "Job Scout",
    "phd-finder": "PhD Scout",
    "scholarship-finder": "Scholarship Scout",
    "resume-optimizer": "Resume Optimizer",
    "sop-builder": "SOP Builder",
    "interview-coach": "Interview Coach",
    "research": "Research Assistant",
    "data-analyst": "Data Analyst",
    "sales-research": "Sales Scout",
    "email-assistant": "Email Assistant",
}


def _match_template(text: str) -> str:
    t = text.lower()
    for pattern, tid in _ROUTES:
        if re.search(pattern, t):
            return tid
    return "research"


def _infer_schedule(text: str) -> dict:
    t = text.lower()
    if re.search(r"\b(every hour|hourly)\b", t):
        return {"cadence": "hourly"}
    if re.search(r"\b(every morning|each morning|daily|every day|each day)\b", t):
        return {"cadence": "daily", "time": "08:00"}
    m = re.search(r"\bevery (monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", t)
    if m:
        return {"cadence": "weekly", "day": m.group(1)}
    if re.search(r"\b(weekly|every week)\b", t):
        return {"cadence": "weekly", "day": "monday"}
    return {}


def _infer_approval(text: str) -> dict:
    t = text.lower()
    cues = r"\b(approv|before sending|ask me before|confirm before|with my permission)"
    if re.search(cues, t):
        return {"require_approval": True}
    return {}


def deterministic_spec(description: str) -> dict:
    """Build a proposed spec from the description using template matching + cue detection."""
    desc = (description or "").strip()
    tid = _match_template(desc)
    tpl = TEMPLATE_MAP[tid]
    schedule = _infer_schedule(desc)
    approval = _infer_approval(desc) or dict(tpl.get("approval_policy") or {})
    return {
        "name": _DEFAULT_NAME.get(tid, tpl["name"]),
        "description": desc[:280] or tpl["description"],
        "purpose": tpl["purpose"],
        "instructions": desc,
        "tools": list(tpl.get("tools") or []),
        "memory_config": dict(tpl.get("memory_config") or {}),
        "schedule": schedule,
        "approval_policy": approval,
        "personality": tpl.get("personality", "Friendly"),
        "suggested_character_id": suggest_character_for_work(
            desc, personality=tpl.get("personality", ""), fallback=tpl.get("character_id", "nova")
        ),
        "template_id": tid,
        "generated_by": "deterministic",
    }


_LLM_SYSTEM = (
    "You turn a user's description into an AI agent specification. Reply with ONLY a JSON "
    "object with keys: name, purpose, instructions, tools (array of strings), schedule "
    "(object), approval_policy (object), personality (one of Focused/Friendly/Analytical/"
    "Curious/Concise/Creative). Use only realistic tools. Do not invent capabilities."
)


async def generate_spec(
    description: str, chat_fn: ChatFn | None = None, *, use_llm: bool = False
) -> dict:
    """Return a proposed spec. Deterministic unless use_llm and a chat_fn is given; on any
    LLM error, returns the deterministic draft (never fails the create flow)."""
    draft = deterministic_spec(description)
    if not (use_llm and chat_fn):
        return draft
    try:
        raw = await chat_fn(
            [
                {"role": "system", "content": _LLM_SYSTEM},
                {"role": "user", "content": description[:2000]},
            ]
        )
        m = re.search(r"\{.*\}", raw or "", re.DOTALL)
        data = json.loads(m.group(0)) if m else {}
        if not isinstance(data, dict) or not data.get("name"):
            return draft
        # merge LLM refinements onto the deterministic draft (draft supplies the rest)
        for k in (
            "name",
            "purpose",
            "instructions",
            "tools",
            "schedule",
            "approval_policy",
            "personality",
        ):
            if data.get(k):
                draft[k] = data[k]
        draft["generated_by"] = "llm"
        return draft
    except Exception:
        return draft
