"""LLM-grounded SOP drafting + targeted rewrites. Never invents applicant facts."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.sop.models import SopDoc

ChatFn = Callable[[list[dict]], Awaitable[str]]


class SopError(RuntimeError):
    """Raised when generation is unavailable (e.g. LLM not configured)."""


_SYS = (
    "You draft a Statement of Purpose (SOP) for a graduate/PhD application. RULES: "
    "Use ONLY the applicant facts provided. NEVER invent projects, publications, awards, GPA, "
    "employers, internships or experience. If a needed fact is missing, insert a bracketed "
    "placeholder like [Information needed: ...] rather than inventing it. Do not invent university "
    "faculty, labs, or courses beyond the target details provided. Write flowing prose in a {style} "
    "tone. No markdown headings, no asterisks, no bullet lists. Respect the word limit if one is given."
)

_ACTIONS = {
    "concise": "Rewrite this passage to be more concise without losing meaning or inventing facts.",
    "specific": "Make this passage more specific using only facts already present; do not add new facts.",
    "academic": "Rewrite this passage in a more formal academic tone. Do not add facts.",
    "transition": "Improve the flow and transitions of this passage. Do not add facts.",
    "repetition": "Remove repetition from this passage while preserving all facts.",
    "evidence": "Tighten this passage; if it makes an unsupported claim, mark it [Information needed]. Add no facts.",
}


def _applicant_facts(profile: dict | None, resume: dict | None) -> str:
    lines: list[str] = []
    if profile:
        for key, label in [
            ("degree", "Degree"),
            ("field", "Field"),
            ("nationality", "Nationality"),
        ]:
            if profile.get(key):
                lines.append(f"{label}: {profile[key]}")
        if profile.get("gpa") is not None:
            lines.append(f"GPA: {profile['gpa']}/{profile.get('gpa_scale') or '?'}")
        if profile.get("experience_years") is not None:
            lines.append(f"Experience: {profile['experience_years']} years")
    if resume:
        for key, label in [
            ("education", "Education"),
            ("skills", "Skills"),
            ("projects", "Projects"),
            ("certifications", "Certifications"),
            ("languages", "Languages"),
            ("industries", "Industries"),
            ("job_titles", "Roles"),
        ]:
            v = resume.get(key)
            if v:
                lines.append(f"{label}: {', '.join(v) if isinstance(v, list) else v}")
        if resume.get("summary"):
            lines.append(f"Summary: {resume['summary']}")
    return "\n".join(lines) or "(no applicant facts provided — use placeholders)"


async def _default_chat(messages: list[dict]) -> str:
    from app.core import llm

    return await llm.chat(messages, temperature=0.4)


async def generate(
    doc: SopDoc, profile: dict | None, resume: dict | None, chat_fn: ChatFn | None = None
) -> str:
    t = doc.target
    r = doc.requirements
    target = (
        f"University: {t.university or '[not specified]'}\nProgram: {t.program or '[not specified]'}\n"
        f"Degree: {t.degree or ''}\nField: {t.field or '[not specified]'}\nCountry: {t.country or ''}\n"
        f"Program info: {t.opportunity_description or '(none provided)'}"
    )
    reqtext = (
        f"Word limit: {r.word_limit or 'not specified'}\nPrompt: {r.prompt or 'none'}\n"
        f"Questions to address: {'; '.join(r.questions) or 'none'}"
    )
    user = (
        f"APPLICANT FACTS:\n{_applicant_facts(profile, resume)}\n\n"
        f"TARGET PROGRAM:\n{target}\n\nSOP REQUIREMENTS:\n{reqtext}\n\n"
        f"EXTRA INSTRUCTIONS: {doc.instructions or 'none'}\n\nWrite the complete SOP now."
    )
    fn = chat_fn or _default_chat
    try:
        out = await fn(
            [
                {"role": "system", "content": _SYS.format(style=doc.style)},
                {"role": "user", "content": user},
            ]
        )
    except Exception as exc:  # noqa: BLE001
        raise SopError(f"SOP generation is unavailable: {exc}") from exc
    return (out or "").strip()


async def rewrite(text: str, action: str, chat_fn: ChatFn | None = None) -> str:
    instr = _ACTIONS.get(action, action)
    fn = chat_fn or _default_chat
    try:
        out = await fn(
            [
                {"role": "system", "content": "You edit application prose. Never invent facts."},
                {"role": "user", "content": f"{instr}\n\nPASSAGE:\n{text}"},
            ]
        )
    except Exception as exc:  # noqa: BLE001
        raise SopError(f"Rewrite is unavailable: {exc}") from exc
    return (out or "").strip()
