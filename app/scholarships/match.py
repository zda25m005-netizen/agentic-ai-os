"""Explainable scholarship match score (deterministic weighting).

Runs only on scholarships that already PASSED the hard filters, so it reorders
valid results and explains fit — it never resurrects an excluded scholarship.
"""

from __future__ import annotations

from app.scholarships.models import Scholarship, ScholarshipIntent

_ELIG_SCORE = {"eligible": 1.0, "likely": 0.8, "unclear": 0.6, "not_eligible": 0.15}
WEIGHTS = {
    "field": 0.22,
    "country": 0.18,
    "degree": 0.15,
    "funding": 0.15,
    "eligibility": 0.15,
    "intake": 0.05,
    "profile": 0.10,
}


def _field_score(sch: Scholarship, intent: ScholarshipIntent) -> float:
    if not intent.field_tags:
        return 0.8
    if "all" in sch.fields:
        return 0.85  # open to any field, incl. the requested one
    return 1.0 if set(intent.field_tags) & set(sch.fields) else 0.0


def score(sch: Scholarship, intent: ScholarshipIntent, profile: dict | None) -> dict:
    parts: dict[str, float] = {}
    parts["field"] = _field_score(sch, intent)
    parts["country"] = 1.0 if (not intent.countries or _country_match(sch, intent)) else 0.0
    parts["degree"] = 1.0 if (not intent.degree or intent.degree in sch.degree_levels) else 0.4
    if intent.funding:
        parts["funding"] = (
            1.0
            if sch.funding_type == intent.funding
            else (0.7 if sch.funding_type == "fully_funded" else 0.3)
        )
    else:
        parts["funding"] = 0.9 if sch.funding_type == "fully_funded" else 0.7
    parts["eligibility"] = _ELIG_SCORE.get(sch.eligibility_status or "unclear", 0.6)
    parts["intake"] = (
        1.0 if (not intent.intake or "annual" in sch.intake or intent.intake in sch.intake) else 0.7
    )

    profile_reason = None
    if profile:
        pskills = {s.lower() for s in profile.get("skills", [])}
        pfields = " ".join(profile.get("industries", []) + profile.get("job_titles", [])).lower()
        aligned = bool(intent.field_tags) and any(
            t.replace("_", " ") in pfields for t in intent.field_tags
        )
        parts["profile"] = 0.9 if (aligned or pskills) else 0.6
        if aligned:
            profile_reason = "Aligns with your background"
    else:
        parts["profile"] = 0.6

    total = sum(WEIGHTS[k] * v for k, v in parts.items())
    breakdown = {k: round(v, 2) for k, v in parts.items()}

    bits: list[str] = []
    if intent.field and parts["field"] >= 0.85:
        bits.append(f"{intent.field} eligible")
    if intent.countries and parts["country"] == 1.0:
        bits.append(sch.country)
    if intent.funding and sch.funding_type == intent.funding:
        bits.append("funding matches")
    elif sch.funding_type == "fully_funded":
        bits.append("fully funded")
    if profile_reason:
        bits.append(profile_reason)
    reason = "; ".join(bits) + "." if bits else "Matches your search criteria."

    return {"score": round(total, 3), "breakdown": breakdown, "reason": reason}


def _country_match(sch: Scholarship, intent: ScholarshipIntent) -> bool:
    wanted = set(intent.countries)
    if "Europe" in wanted:
        from app.scholarships.eligibility import EU

        if sch.country in EU or "multi-country" in sch.country.lower() or set(sch.countries) & EU:
            return True
    return bool(wanted & set(sch.countries)) or sch.country in wanted
