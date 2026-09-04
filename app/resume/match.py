"""Candidate <-> job matching. Deterministic, evidence-based, domain-agnostic.

Runs only AFTER the query's hard constraints have removed invalid jobs. The
resume can reorder valid jobs and explain fit; it can never pull an
excluded (wrong role/country/experience) job back in.
"""

from __future__ import annotations

import re

_GENERIC = {
    "senior",
    "junior",
    "lead",
    "staff",
    "principal",
    "intern",
    "engineer",
    "manager",
    "analyst",
    "specialist",
    "associate",
    "assistant",
    "the",
    "and",
    "of",
    "a",
    "an",
}


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-zA-Z][a-zA-Z+#]{1,}", (text or "").lower()) if len(t) > 2}


def score_candidate(
    profile: dict,
    *,
    job_skills: list[str],
    job_title: str,
    job_exp_min: int | None = None,
    job_exp_max: int | None = None,
    job_country: str | None = None,
) -> dict:
    """Return {score, breakdown, matched_skills, missing_skills, reason}."""
    pskills = {s.lower() for s in profile.get("skills", [])}
    matched = [s for s in job_skills if s.lower() in pskills]
    missing = [s for s in job_skills if s.lower() not in pskills]
    skills_score = (len(matched) / len(job_skills)) if job_skills else 0.6

    # role: overlap between the candidate's own titles and this job's title
    ptitle_tokens: set[str] = set()
    for t in profile.get("job_titles", []):
        ptitle_tokens |= _tokens(t)
    jt = _tokens(job_title)
    signif_overlap = (ptitle_tokens & jt) - _GENERIC
    role_score = 1.0 if signif_overlap else (0.7 if ptitle_tokens & jt else 0.5)

    # experience compatibility
    py = profile.get("experience_years")
    if py is None:
        exp_score = 0.7
    elif job_exp_min is not None and py < job_exp_min:
        exp_score = 0.4  # under-qualified
    elif job_exp_max is not None and py > job_exp_max:
        exp_score = 0.8  # over-qualified but still relevant
    else:
        exp_score = 1.0

    # location (soft — the query already hard-filtered location)
    plocs = " ".join(profile.get("locations", [])).lower()
    loc_score = 1.0 if (job_country and job_country.lower() in plocs) else 0.7

    edu_score = 0.85 if profile.get("education") else 0.7

    breakdown = {
        "skills": round(skills_score, 2),
        "role": round(role_score, 2),
        "experience": round(exp_score, 2),
        "location": round(loc_score, 2),
        "education": round(edu_score, 2),
    }
    score = (
        0.40 * skills_score
        + 0.25 * role_score
        + 0.20 * exp_score
        + 0.10 * loc_score
        + 0.05 * edu_score
    )

    # evidence-based reason (never "perfect for you")
    bits: list[str] = []
    if matched:
        bits.append("Matches " + ", ".join(matched[:3]))
    if py is not None:
        bits.append(f"{py:g} yrs experience")
    if not bits:
        bits.append("Role and location fit; skills not directly listed on resume")
    reason = "; ".join(bits) + "."

    return {
        "score": round(score, 3),
        "breakdown": breakdown,
        "matched_skills": matched,
        "missing_skills": missing[:6],
        "reason": reason,
    }


def suggested_roles(profile: dict, limit: int = 5) -> list[str]:
    """Roles to recommend, taken from the candidate's OWN titles (domain-agnostic,
    never assumed to be tech). Empty when the resume lists no titles."""
    out, seen = [], set()
    for t in profile.get("job_titles", []):
        cleaned = re.sub(r"\s+", " ", t).strip(" -–,")
        key = cleaned.lower()
        if cleaned and key not in seen and len(cleaned) <= 60:
            seen.add(key)
            out.append(cleaned)
        if len(out) >= limit:
            break
    return out
