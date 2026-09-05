"""Deterministic natural-language -> ScholarshipIntent parser.

The LLM is intentionally NOT used for hard constraints. Country/degree/field/
funding/intake are extracted with explicit vocabularies so filtering downstream
is deterministic and reproducible.
"""

from __future__ import annotations

import re

from app.scholarships.models import FilterSpec, ScholarshipIntent

COUNTRIES: dict[str, list[str]] = {
    "Switzerland": ["switzerland", "swiss"],
    "Germany": ["germany", "german", "deutschland"],
    "Norway": ["norway", "norwegian"],
    "United Kingdom": ["united kingdom", " uk ", "u.k.", "britain", "england", "scotland"],
    "United States": ["united states", " usa ", " us ", "u.s.", "america"],
    "Canada": ["canada", "canadian"],
    "Australia": ["australia", "australian"],
    "Netherlands": ["netherlands", "holland", "dutch"],
    "Sweden": ["sweden", "swedish"],
    "Finland": ["finland", "finnish"],
    "France": ["france", "french"],
    "Italy": ["italy", "italian"],
    "Denmark": ["denmark", "danish"],
    "Austria": ["austria", "austrian"],
    "Belgium": ["belgium", "belgian"],
    "Ireland": ["ireland", "irish"],
    "Japan": ["japan", "japanese"],
    "South Korea": ["south korea", "korea", "korean"],
    "Singapore": ["singapore"],
    "New Zealand": ["new zealand"],
    "Europe": ["europe", "european", "eu "],
}

_DEGREES: list[tuple[str, re.Pattern]] = [
    ("phd", re.compile(r"\b(phd|ph\.d|doctoral|doctorate|dphil)\b", re.I)),
    ("postdoc", re.compile(r"\b(post[- ]?doc(toral)?)\b", re.I)),
    (
        "master",
        re.compile(r"\b(master'?s?|msc|m\.sc|ma\b|m\.a|graduate|postgraduate|mba|llm)\b", re.I),
    ),
    (
        "bachelor",
        re.compile(r"\b(bachelor'?s?|undergrad(uate)?|bsc|b\.sc|ba\b|b\.a|b\.tech|btech)\b", re.I),
    ),
    ("diploma", re.compile(r"\b(diploma|certificate)\b", re.I)),
]

_FUNDING: list[tuple[str, re.Pattern]] = [
    (
        "fully_funded",
        re.compile(
            r"\b(fully[- ]?funded|full funding|fully financed|tuition\s*\+\s*stipend)\b", re.I
        ),
    ),
    ("stipend", re.compile(r"\b(stipend|living allowance|monthly allowance)\b", re.I)),
    ("tuition", re.compile(r"\b(tuition (waiver|only|free)|fee waiver)\b", re.I)),
    ("partial", re.compile(r"\b(partial(ly)?[- ]?funded|partial funding)\b", re.I)),
]

FIELD_SYNONYMS: dict[str, list[str]] = {
    "ai": ["artificial intelligence", "ai", "machine learning", "ml", "deep learning"],
    "cs": ["computer science", "cs", "software", "computing", "informatics"],
    "data_science": ["data science", "data analytics", "big data", "data scientist"],
    "engineering": ["engineering", "mechanical", "civil", "chemical", "aerospace", "robotics"],
    "electronics": ["electronics", "electrical", "ece", "vlsi", "embedded"],
    "business": ["business", "mba", "business administration"],
    "finance": ["finance", "financial", "fintech", "accounting"],
    "economics": ["economics", "econ"],
    "management": ["management", "supply chain", "operations management"],
    "medicine": ["medicine", "medical", "biomedical", "public health", "nursing", "pharmacy"],
    "law": ["law", "legal", "llm"],
    "social_sciences": [
        "social science",
        "sociology",
        "psychology",
        "political science",
        "international relations",
        "human resources",
        "hr",
        "public policy",
    ],
    "natural_sciences": [
        "physics",
        "chemistry",
        "biology",
        "mathematics",
        "maths",
        "math",
        "natural science",
    ],
    "humanities": ["humanities", "history", "philosophy", "literature", "linguistics"],
    "arts": ["arts", "art", "design", "music", "architecture"],
}
FIELD_DISPLAY = {
    "ai": "Artificial Intelligence",
    "cs": "Computer Science",
    "data_science": "Data Science",
    "engineering": "Engineering",
    "electronics": "Electronics",
    "business": "Business",
    "finance": "Finance",
    "economics": "Economics",
    "management": "Management",
    "medicine": "Medicine",
    "law": "Law",
    "social_sciences": "Social Sciences",
    "natural_sciences": "Natural Sciences",
    "humanities": "Humanities",
    "arts": "Arts",
}

_DEMONYMS = {
    "indian": "India",
    "chinese": "China",
    "pakistani": "Pakistan",
    "bangladeshi": "Bangladesh",
    "nigerian": "Nigeria",
    "kenyan": "Kenya",
    "german": "Germany",
    "american": "United States",
    "british": "United Kingdom",
    "french": "France",
    "nepali": "Nepal",
    "sri lankan": "Sri Lanka",
    "vietnamese": "Vietnam",
    "indonesian": "Indonesia",
    "egyptian": "Egypt",
    "brazilian": "Brazil",
}


def field_tags_for(text: str) -> list[str]:
    tags: list[str] = []
    low = f" {text.lower()} "
    for tag, phrases in FIELD_SYNONYMS.items():
        for p in phrases:
            if re.search(rf"\b{re.escape(p)}\b", low, re.I):
                tags.append(tag)
                break
    return tags


def parse_query(raw: str) -> ScholarshipIntent:
    q = (raw or "").strip()
    low = f" {q.lower()} "

    countries = [c for c, al in COUNTRIES.items() if any(a in low for a in al)]

    degree = next((d for d, rx in _DEGREES if rx.search(q)), None)
    funding = next((f for f, rx in _FUNDING if rx.search(q)), None)

    tags = field_tags_for(q)
    field_display = FIELD_DISPLAY.get(tags[0]) if tags else None

    nationality = None
    for demo, country in _DEMONYMS.items():
        if re.search(rf"\b{re.escape(demo)}\b", low):
            nationality = country
            break

    m = re.search(r"\b(20[2-3]\d)\b", q)
    intake = m.group(1) if m else None
    no_ielts = bool(re.search(r"\b(without|no)\s+ielts\b|\bno[- ]?ielts\b", low))

    stype = None
    for label, kw in [
        ("government", "government"),
        ("university", "university"),
        ("research", "research"),
        ("fellowship", "fellowship"),
        ("exchange", "exchange"),
    ]:
        if kw in low:
            stype = label
            break

    return ScholarshipIntent(
        raw=q,
        field=field_display,
        field_tags=tags,
        countries=countries,
        degree=degree,
        funding=funding,
        nationality=nationality,
        intake=intake,
        scholarship_type=stype,
        no_ielts=no_ielts,
    )


def intent_from_filters(f: FilterSpec) -> ScholarshipIntent:
    """Build intent from explicit, individually-removable filters (authoritative)."""
    tags = field_tags_for(f.field) if f.field else []
    return ScholarshipIntent(
        raw=f.field or "",
        field=(FIELD_DISPLAY.get(tags[0]) if tags else f.field),
        field_tags=tags,
        countries=list(f.countries or []),
        degree=f.degree,
        funding=f.funding,
        nationality=f.nationality,
        intake=f.intake,
        scholarship_type=f.scholarship_type,
        no_ielts=f.no_ielts,
    )
