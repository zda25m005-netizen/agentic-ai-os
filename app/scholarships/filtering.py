"""Deterministic hard filtering + deduplication (runs after retrieval)."""

from __future__ import annotations

import re

from app.scholarships.match import _country_match
from app.scholarships.models import Scholarship, ScholarshipIntent


def passes_hard(sch: Scholarship, intent: ScholarshipIntent) -> bool:
    if intent.countries and not _country_match(sch, intent):
        return False
    if intent.degree and intent.degree not in sch.degree_levels:
        return False
    if (
        intent.field_tags
        and "all" not in sch.fields
        and not (set(intent.field_tags) & set(sch.fields))
    ):
        return False
    if intent.funding:
        if intent.funding == "fully_funded":
            if sch.funding_type != "fully_funded":
                return False
        elif sch.funding_type not in (intent.funding, "fully_funded"):
            return False
    if intent.scholarship_type and sch.scholarship_type != intent.scholarship_type:
        return False
    return True


def dedup(schs: list[Scholarship]) -> list[Scholarship]:
    by_key: dict[tuple[str, str], Scholarship] = {}
    for s in schs:
        key = (s.provider.lower().strip(), re.sub(r"\s+", " ", s.title.lower()).strip())
        keep = by_key.get(key)
        if keep is None:
            by_key[key] = s
            continue
        for src in s.sources:
            if src not in keep.sources:
                keep.sources.append(src)
        if s.apply_direct and not keep.apply_direct:
            keep.application_url = s.application_url
            keep.apply_direct = True
    return list(by_key.values())
