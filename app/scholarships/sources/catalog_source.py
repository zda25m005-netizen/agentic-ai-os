"""Curated-catalog source: real programs with official URLs.

Retrieval is intentionally broad (returns the whole curated set); the search
pipeline then applies deterministic hard filtering. This mirrors the "retrieve
broadly, display strictly" approach used by the Job Search Agent.
"""

from __future__ import annotations

from app.scholarships.catalog import catalog
from app.scholarships.models import Scholarship, ScholarshipIntent
from app.scholarships.sources.base import ScholarshipSource


class CatalogSource(ScholarshipSource):
    name = "Curated · official"

    async def search(self, intent: ScholarshipIntent) -> list[Scholarship]:
        # Return fresh copies so per-request scoring/eligibility never mutates the catalog.
        return [s.model_copy(deep=True) for s in catalog()]
