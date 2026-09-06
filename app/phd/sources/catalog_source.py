"""Curated PhD catalog source (real programs/portals). Retrieve broad, filter strict."""

from __future__ import annotations

from app.phd.catalog import catalog
from app.phd.models import PhdIntent, PhdOpportunity
from app.phd.sources.base import PhdSource


class CatalogSource(PhdSource):
    name = "Curated · official"

    async def search(self, intent: PhdIntent) -> list[PhdOpportunity]:
        return [o.model_copy(deep=True) for o in catalog()]
