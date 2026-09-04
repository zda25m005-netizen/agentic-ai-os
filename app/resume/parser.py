"""Turn resume text into a normalized, structured profile via the LLM.

The extraction is grounded strictly in the resume text — the prompt forbids
inventing anything, and missing fields come back empty/null rather than guessed.
Sending resume text to the model is the user's explicit, consented choice (the
upload action); nothing is sent otherwise.
"""

from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable

ChatFn = Callable[[list[dict]], Awaitable[str]]

PROFILE_KEYS = (
    "skills",
    "job_titles",
    "experience_years",
    "education",
    "projects",
    "certifications",
    "industries",
    "locations",
    "languages",
    "summary",
)

_SYS = (
    "You extract a structured candidate profile from resume text. "
    "Return ONLY a JSON object with these keys: "
    "skills (array of strings), job_titles (array), experience_years (number or null — "
    "total years of professional experience), education (array of strings), projects (array), "
    "certifications (array), industries (array), locations (array), languages (array), "
    "summary (a 1-2 sentence string). "
    "Ground every value strictly in the resume text. If something is not present, use [] or null. "
    "Do NOT invent skills, employers, dates, or numbers. Return only the JSON, no prose."
)

_OBJ = re.compile(r"\{.*\}", re.DOTALL)


class ResumeParseError(RuntimeError):
    """Raised when the resume cannot be analyzed into a profile."""


def _coerce_list(value) -> list[str]:
    if isinstance(value, list):
        out, seen = [], set()
        for v in value:
            s = str(v).strip()
            if s and s.lower() not in seen:
                seen.add(s.lower())
                out.append(s)
        return out[:40]
    return []


def _coerce_years(value) -> float | None:
    if isinstance(value, int | float):
        return round(float(value), 1) if 0 <= value <= 60 else None
    if isinstance(value, str):
        m = re.search(r"\d+(?:\.\d+)?", value)
        if m:
            n = float(m.group(0))
            return n if 0 <= n <= 60 else None
    return None


def normalize_profile(data: dict) -> dict:
    """Coerce the LLM output into the canonical profile shape (never fabricated)."""
    prof = {
        "skills": _coerce_list(data.get("skills")),
        "job_titles": _coerce_list(data.get("job_titles")),
        "experience_years": _coerce_years(data.get("experience_years")),
        "education": _coerce_list(data.get("education")),
        "projects": _coerce_list(data.get("projects")),
        "certifications": _coerce_list(data.get("certifications")),
        "industries": _coerce_list(data.get("industries")),
        "locations": _coerce_list(data.get("locations")),
        "languages": _coerce_list(data.get("languages")),
        "summary": (str(data.get("summary")).strip()[:600] if data.get("summary") else ""),
    }
    return prof


def profile_is_sparse(profile: dict) -> bool:
    """True when almost nothing usable was extracted (UI shows a soft warning)."""
    return (
        not profile["skills"] and not profile["job_titles"] and profile["experience_years"] is None
    )


async def _default_chat(text: str) -> str:
    from app.core import llm

    return await llm.chat(
        [{"role": "system", "content": _SYS}, {"role": "user", "content": text}],
        temperature=0.0,
    )


async def parse_profile(text: str, chat_fn: ChatFn | None = None) -> dict:
    """Extract a normalized profile from resume text. Raises on failure."""
    text = (text or "").strip()
    if len(text) < 30:
        raise ResumeParseError("The resume has too little extractable text to analyze.")
    fn = chat_fn or _default_chat
    try:
        raw = await fn(text[:12000])
    except Exception as exc:  # LLM not configured / network / provider error
        raise ResumeParseError(f"Resume analysis is unavailable: {exc}") from exc
    m = _OBJ.search(raw or "")
    if not m:
        raise ResumeParseError("Could not read a structured profile from this resume.")
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError as exc:
        raise ResumeParseError("Could not parse the extracted profile.") from exc
    if not isinstance(data, dict):
        raise ResumeParseError("Unexpected profile format.")
    return normalize_profile(data)
