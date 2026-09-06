"""PhD source-adapter interface."""

from __future__ import annotations

from app.phd.models import PhdIntent, PhdOpportunity


class PhdSource:
    name: str = "source"

    async def search(self, intent: PhdIntent) -> list[PhdOpportunity]:
        raise NotImplementedError
