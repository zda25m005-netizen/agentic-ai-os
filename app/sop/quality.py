"""Deterministic SOP quality analysis (computed metrics, not opaque AI scores)."""

from __future__ import annotations

import re

from app.sop.models import QualityReport, SopRequirements

_SECTIONS = {
    "Motivation": ["motivat", "drawn to", "driven", "inspired", "why i"],
    "Academic background": ["degree", "bachelor", "master", "coursework", "studied", "academic"],
    "Research interests": ["research", "interest", "focus on", "area of"],
    "Why this program": ["program", "curriculum", "this course", "offering"],
    "Why this university": ["university", "faculty", "lab", "research group", "institute"],
    "Career goals": ["goal", "aspire", "future", "career", "aim to", "long-term"],
}
_GENERIC = [
    "passionate",
    "always been interested",
    "hardworking",
    "since childhood",
    "world-class",
    "dream",
    "honed my skills",
    "from a young age",
    "cutting-edge",
]


def analyze(content: str, requirements: SopRequirements) -> QualityReport:
    words = content.split()
    wc, cc = len(words), len(content)
    low = content.lower()
    coverage = [
        {"section": k, "covered": any(kw in low for kw in kws)} for k, kws in _SECTIONS.items()
    ]
    if requirements.questions:
        for q in requirements.questions:
            toks = [t for t in re.findall(r"[a-zA-Z]{4,}", q.lower())][:4]
            coverage.append(
                {"section": q[:48], "covered": any(t in low for t in toks) if toks else False}
            )

    generic = [g for g in _GENERIC if g in low]
    proper = len(re.findall(r"\b[A-Z][a-zA-Z]{2,}\b", content))
    digits = len(re.findall(r"\d", content))
    specificity = round(min(1.0, (proper + digits) / max(1, wc) * 2.5), 2)

    sents = [s.strip().lower() for s in re.split(r"[.!?]", content) if len(s.strip()) > 15]
    seen: set[str] = set()
    rep: list[str] = []
    for s in sents:
        if s in seen:
            rep.append(s[:60] + "…")
        seen.add(s)

    wl = requirements.word_limit
    return QualityReport(
        word_count=wc,
        char_count=cc,
        word_limit=wl,
        over_limit=bool(wl and wc > wl),
        coverage=coverage,
        specificity=specificity,
        generic_flags=generic,
        repetition_flags=rep,
    )
