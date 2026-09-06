"""Deterministic hard filtering + dedup for PhD opportunities."""

from __future__ import annotations

import re

from app.phd.match import country_match
from app.phd.models import PhdIntent, PhdOpportunity

_FUNDING_OK = {
    # a salaried PhD position is fully financed, so it satisfies "fully funded"
    "fully_funded": {"fully_funded", "salaried"},
    "salaried": {"salaried", "fully_funded"},
    "funded": {"funded", "fully_funded", "salaried", "scholarship"},
    "scholarship": {"scholarship", "fully_funded"},
    "partial": {"partial", "funded", "fully_funded"},
    "self_funded": {"self_funded"},
}


def passes_hard(opp: PhdOpportunity, intent: PhdIntent) -> bool:
    if intent.countries and not country_match(opp, intent):
        return False
    if (
        intent.field_tags
        and "all" not in opp.fields
        and not (set(intent.field_tags) & set(opp.fields))
    ):
        return False
    if intent.funding and opp.funding_type not in _FUNDING_OK.get(
        intent.funding, {opp.funding_type}
    ):
        return False
    if intent.opportunity_type and opp.opportunity_type != intent.opportunity_type:
        return False
    return True


def dedup(opps: list[PhdOpportunity]) -> list[PhdOpportunity]:
    by_key: dict[tuple[str, str], PhdOpportunity] = {}
    for o in opps:
        key = (o.institution.lower().strip(), re.sub(r"\s+", " ", o.title.lower()).strip())
        keep = by_key.get(key)
        if keep is None:
            by_key[key] = o
            continue
        for s in o.sources:
            if s not in keep.sources:
                keep.sources.append(s)
        if o.apply_direct and not keep.apply_direct:
            keep.official_application_url = o.official_application_url
            keep.apply_direct = True
    return list(by_key.values())
