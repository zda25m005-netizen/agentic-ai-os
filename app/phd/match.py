"""Explainable PhD match score + country matching (deterministic)."""

from __future__ import annotations

from app.phd.models import PhdIntent, PhdOpportunity
from app.scholarships.eligibility import EU

_ELIG = {"eligible": 1.0, "likely": 0.8, "unclear": 0.6, "insufficient": 0.55, "not_eligible": 0.15}
WEIGHTS = {
    "research": 0.28,
    "country": 0.18,
    "funding": 0.18,
    "eligibility": 0.16,
    "profile": 0.12,
    "timing": 0.08,
}


def country_match(opp: PhdOpportunity, intent: PhdIntent) -> bool:
    wanted = set(intent.countries)
    if not wanted:
        return True
    if "Europe" in wanted and (
        opp.country in EU or "multi-country" in opp.country.lower() or set(opp.countries) & EU
    ):
        return True
    return bool(wanted & set(opp.countries)) or opp.country in wanted


def _funding_score(opp: PhdOpportunity, intent: PhdIntent) -> float:
    base = {
        "fully_funded": 1.0,
        "salaried": 0.95,
        "funded": 0.9,
        "scholarship": 0.85,
        "partial": 0.6,
        "self_funded": 0.3,
        "unknown": 0.5,
    }.get(opp.funding_type, 0.5)
    if intent.funding and opp.funding_type == intent.funding:
        base = 1.0
    return base


def score(opp: PhdOpportunity, intent: PhdIntent, profile: dict | None) -> dict:
    parts: dict[str, float] = {}
    if intent.field_tags:
        parts["research"] = (
            0.85
            if "all" in opp.fields
            else (1.0 if set(intent.field_tags) & set(opp.fields) else 0.0)
        )
    else:
        parts["research"] = 0.8
    parts["country"] = 1.0 if country_match(opp, intent) else 0.0
    parts["funding"] = _funding_score(opp, intent)
    parts["eligibility"] = _ELIG.get(opp.eligibility_status or "unclear", 0.6)
    parts["timing"] = (
        1.0
        if (not intent.intake or "rolling" in opp.intake or intent.intake in opp.intake)
        else 0.7
    )

    reason_profile = None
    if profile:
        pfields = " ".join(profile.get("industries", []) + profile.get("job_titles", [])).lower()
        aligned = bool(intent.field_tags) and any(
            t.replace("_", " ") in pfields for t in intent.field_tags
        )
        parts["profile"] = 0.9 if (aligned or profile.get("skills")) else 0.6
        if aligned:
            reason_profile = "Research area overlaps with your background"
    else:
        parts["profile"] = 0.6

    total = sum(WEIGHTS[k] * v for k, v in parts.items())
    bits: list[str] = []
    if intent.field and parts["research"] >= 0.85:
        bits.append(f"{intent.field} research fit")
    if intent.countries and parts["country"] == 1.0:
        bits.append(opp.country)
    if opp.funding_type in ("fully_funded", "salaried", "funded"):
        bits.append(opp.funding_type.replace("_", " "))
    if reason_profile:
        bits.append(reason_profile)
    reason = "; ".join(bits) + "." if bits else "Matches your search."
    return {
        "score": round(total, 3),
        "breakdown": {k: round(v, 2) for k, v in parts.items()},
        "reason": reason,
    }
