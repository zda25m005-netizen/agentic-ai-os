"""Deterministic PhD query -> PhdIntent. Reuses scholarship country/field vocab."""

from __future__ import annotations

import re

from app.phd.models import PhdFilterSpec, PhdIntent
from app.scholarships.parser import COUNTRIES, FIELD_DISPLAY, field_tags_for

_FUNDING = [
    (
        "fully_funded",
        re.compile(r"\b(fully[- ]?funded|full funding|tuition\s*\+\s*stipend)\b", re.I),
    ),
    ("salaried", re.compile(r"\b(salaried|salary|employment|paid position)\b", re.I)),
    ("funded", re.compile(r"\b(funded|funding|stipend)\b", re.I)),
    ("scholarship", re.compile(r"\b(scholarship|fellowship)\b", re.I)),
    ("partial", re.compile(r"\b(partial(ly)?[- ]?funded)\b", re.I)),
    ("self_funded", re.compile(r"\b(self[- ]?funded)\b", re.I)),
]
_OPP = [
    ("funded_phd_position", re.compile(r"\b(phd position|doctoral position|phd vacanc)", re.I)),
    (
        "research_position",
        re.compile(r"\b(research position|research assistant|research associate)\b", re.I),
    ),
    ("fellowship", re.compile(r"\b(fellowship)\b", re.I)),
    ("doctoral_scholarship", re.compile(r"\b(doctoral scholarship|phd scholarship)\b", re.I)),
    ("phd_program", re.compile(r"\b(phd program(me)?|doctoral program(me)?|dphil)\b", re.I)),
]
_DEMONYMS = {
    "indian": "India",
    "chinese": "China",
    "pakistani": "Pakistan",
    "german": "Germany",
    "american": "United States",
    "british": "United Kingdom",
    "nigerian": "Nigeria",
    "nepali": "Nepal",
    "bangladeshi": "Bangladesh",
}


def parse_query(raw: str) -> PhdIntent:
    q = (raw or "").strip()
    low = f" {q.lower()} "
    countries = [c for c, al in COUNTRIES.items() if any(a in low for a in al)]
    funding = next((f for f, rx in _FUNDING if rx.search(q)), None)
    opp = next((o for o, rx in _OPP if rx.search(q)), None)
    tags = field_tags_for(q)
    field = FIELD_DISPLAY.get(tags[0]) if tags else None
    nationality = next((c for demo, c in _DEMONYMS.items() if re.search(rf"\b{demo}\b", low)), None)
    m = re.search(r"\b(20[2-3]\d)\b", q)
    no_fee = bool(re.search(r"\bno (application )?fee\b|\bwithout fee\b|\bfee waiver\b", low))
    return PhdIntent(
        raw=q,
        field=field,
        field_tags=tags,
        countries=countries,
        funding=funding,
        opportunity_type=opp,
        nationality=nationality,
        intake=(m.group(1) if m else None),
        no_fee=no_fee,
    )


def intent_from_filters(f: PhdFilterSpec) -> PhdIntent:
    tags = field_tags_for(f.field) if f.field else []
    return PhdIntent(
        raw=f.field or "",
        field=(FIELD_DISPLAY.get(tags[0]) if tags else f.field),
        field_tags=tags,
        countries=list(f.countries or []),
        funding=f.funding,
        opportunity_type=f.opportunity_type,
        nationality=f.nationality,
        intake=f.intake,
    )
