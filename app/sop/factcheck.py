"""Heuristic, conservative fact-check of SOP content against the applicant's data.

Flags claims that the profile/resume does not support as 'needs_verification' or
'unsupported' — it never silently deletes them, and never asserts a claim is false.
"""

from __future__ import annotations

import re

from app.sop.models import FactCheckResult, FactClaim


def check(content: str, profile: dict | None, resume: dict | None) -> FactCheckResult:
    profile = profile or {}
    resume = resume or {}
    claims: list[FactClaim] = []
    low = content.lower()

    for m in re.findall(r"\[information needed[^\]]*\]", content, re.I):
        claims.append(
            FactClaim(
                text=m, status="unsupported", note="Placeholder — provide this fact or remove it."
            )
        )

    if re.search(r"\b(publish|publication|paper|journal|conference)\b", low) and not resume.get(
        "publications"
    ):
        claims.append(
            FactClaim(
                text="Mentions publications/papers",
                status="needs_verification",
                note="No publications found in your profile/résumé.",
            )
        )
    if re.search(r"\bgpa\b|\bcgpa\b", low) and profile.get("gpa") is None:
        claims.append(
            FactClaim(
                text="Mentions a GPA",
                status="needs_verification",
                note="GPA is not in your profile.",
            )
        )
    if re.search(r"\b(award|prize|medal|rank\s*1|gold medal)\b", low) and not resume.get(
        "certifications"
    ):
        claims.append(
            FactClaim(
                text="Mentions an award/prize",
                status="needs_verification",
                note="No award found in your profile/résumé.",
            )
        )

    for s in resume.get("skills", []):
        if re.search(rf"\b{re.escape(s)}\b", content, re.I):
            claims.append(
                FactClaim(text=f"Skill: {s}", status="verified", note="Present in your résumé.")
            )
    deg = profile.get("degree") or ""
    if deg and re.search(rf"\b{re.escape(deg)}\b", low):
        claims.append(
            FactClaim(text=f"Degree: {deg}", status="verified", note="Matches your profile.")
        )

    v = sum(1 for c in claims if c.status == "verified")
    n = sum(1 for c in claims if c.status == "needs_verification")
    u = sum(1 for c in claims if c.status == "unsupported")
    return FactCheckResult(claims=claims, verified=v, needs_verification=n, unsupported=u)
