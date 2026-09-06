"""PhD search pipeline: sources -> dedup -> hard filter -> eligibility -> match -> rank."""

from __future__ import annotations

import asyncio
from collections import Counter

from app.phd.filtering import dedup, passes_hard
from app.phd.match import score
from app.phd.models import PhdIntent, PhdOpportunity, SourceStatus, StudentProfile
from app.phd.sources.base import PhdSource
from app.phd.sources.catalog_source import CatalogSource
from app.scholarships.eligibility import evaluate

SOURCES: list[PhdSource] = [CatalogSource()]


def build_checklist(opp: PhdOpportunity) -> list[dict]:
    """Honest checklist: typical PhD items (labeled) + any source-stated requirement."""
    items = [
        {"item": "Curriculum Vitae (CV)", "kind": "typical"},
        {"item": "Academic transcripts", "kind": "typical"},
        {"item": "Research proposal / statement of purpose", "kind": "typical"},
        {"item": "Letters of recommendation", "kind": "typical"},
    ]
    lang = (opp.language_requirements or "").lower()
    if opp.min_ielts or "ielts" in lang or "toefl" in lang:
        items.append({"item": "English proficiency (IELTS/TOEFL)", "kind": "required"})
    items.append({"item": "Verify the full document list on the official page", "kind": "note"})
    return items


async def run_search(
    intent: PhdIntent,
    profile: StudentProfile | None = None,
    resume: dict | None = None,
    limit: int = 100,
) -> tuple[list[PhdOpportunity], list[SourceStatus], int]:
    profile = profile or StudentProfile()
    results = await asyncio.gather(*(s.search(intent) for s in SOURCES), return_exceptions=True)
    raw: list[PhdOpportunity] = []
    statuses: list[SourceStatus] = []
    for src, res in zip(SOURCES, results, strict=False):
        if isinstance(res, Exception):
            statuses.append(SourceStatus(source=src.name, status="error", note="unavailable"))
        else:
            raw.extend(res)
            statuses.append(
                SourceStatus(source=src.name, status="ok", count=len(res), note="connected")
            )

    valid = [o for o in dedup(raw) if passes_hard(o, intent)]
    for o in valid:
        o.eligibility_status, o.eligibility_checks = evaluate(o, profile)
        o.eligibility_reasons = [
            c.explanation or f"{c.requirement}: {c.status.title()}"
            for c in o.eligibility_checks
            if c.status != "NOT_APPLICABLE"
        ]
        o.application_checklist = build_checklist(o)
        m = score(o, intent, resume)
        o.match_score, o.match_breakdown, o.match_reason = m["score"], m["breakdown"], m["reason"]
    valid.sort(key=lambda x: x.match_score or 0, reverse=True)
    return valid[:limit], statuses, len(raw)


def summarize(opps: list[PhdOpportunity]) -> dict[str, int]:
    funded = {"fully_funded", "funded", "salaried", "scholarship"}
    return {
        "total": len(opps),
        "funded": sum(1 for o in opps if o.funding_type in funded),
        "eligible": sum(1 for o in opps if o.eligibility_status in ("eligible", "likely")),
        "positions": sum(
            1 for o in opps if o.opportunity_type in ("funded_phd_position", "research_position")
        ),
    }


def facets(opps: list[PhdOpportunity]) -> list[dict]:
    return [{"country": k, "count": v} for k, v in Counter(o.country for o in opps).most_common()]
