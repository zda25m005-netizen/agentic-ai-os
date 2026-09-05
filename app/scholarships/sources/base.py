"""Source-adapter interface."""

from __future__ import annotations

from app.scholarships.models import Scholarship, ScholarshipIntent


class ScholarshipSource:
    name: str = "source"

    async def search(self, intent: ScholarshipIntent) -> list[Scholarship]:
        raise NotImplementedError
