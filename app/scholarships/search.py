"""Scholarship search pipeline.

intent -> source adapters (parallel) -> normalize -> dedup -> HARD FILTER ->
eligibility -> resume match -> rank. Hard constraints are deterministic and run
before ranking; the resume only personalizes order.
"""

from __future__ import annotations

import asyncio

from app.scholarships.eligibility import eligibility_status
from app.scholarships.filtering import dedup, passes_hard
from app.scholarships.match import score
from app.scholarships.models import Scholarship, ScholarshipIntent, SourceStatus
from app.scholarships.sources.base import ScholarshipSource
from app.scholarships.sources.catalog_source import CatalogSource

SOURCES: list[ScholarshipSource] = [CatalogSource()]


async def run_search(
    intent: ScholarshipIntent, profile: dict | None = None, limit: int = 100
) -> tuple[list[Scholarship], list[SourceStatus], int]:
    results = await asyncio.gather(*(s.search(intent) for s in SOURCES), return_exceptions=True)
    raw: list[Scholarship] = []
    statuses: list[SourceStatus] = []
    for src, res in zip(SOURCES, results, strict=False):
        if isinstance(res, Exception):
            statuses.append(SourceStatus(source=src.name, status="error", note="unavailable"))
        else:
            raw.extend(res)
            statuses.append(
                SourceStatus(source=src.name, status="ok", count=len(res), note="connected")
            )

    deduped = dedup(raw)
    valid = [s for s in deduped if passes_hard(s, intent)]
    for s in valid:
        s.eligibility_status, s.eligibility_reasons = eligibility_status(s, intent)
        m = score(s, intent, profile)
        s.match_score, s.match_breakdown, s.match_reason = m["score"], m["breakdown"], m["reason"]
    valid.sort(key=lambda x: x.match_score or 0, reverse=True)
    return valid[:limit], statuses, len(raw)


def summarize(scholarships: list[Scholarship]) -> dict[str, int]:
    return {
        "total": len(scholarships),
        "fully_funded": sum(1 for s in scholarships if s.funding_type == "fully_funded"),
        "eligible": sum(1 for s in scholarships if s.eligibility_status in ("eligible", "likely")),
        "with_deadline": sum(1 for s in scholarships if s.deadline),
    }
