"""Source relevance gate — keep only sources actually about the research question.

The search layer can return topically-unrelated pages (a glossary, or an
off-topic article that merely shares a word). Counting those as evidence and
citing them is a correctness bug, not a cosmetic one: a report on "RAG vs
fine-tuning vs structured memory" must never cite a page on Japanese conjugation
or The Rite of Spring.

This module scores every candidate source against the research question from its
title + snippet, and the pipeline drops any *assessable* source below a
threshold before it can enter the evidence set, the scorecard, or the
bibliography. The score is a transparent lexical relevance in [0, 1] — the
Otsuka-Ochiai (binary-cosine) overlap of content terms, lifted when a named
entity from the question appears in the source. It is offline, deterministic and
explainable: no model, no network, no fake precision.

A source with no assessable text (only a bare domain) is *kept* — absence of
metadata is not evidence of irrelevance, and we never silently drop a link we
simply could not read.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

# Default gate. Calibrated (see tests/test_relevance.py) so on-topic academic /
# encyclopedic sources pass while unrelated pages (0 shared salient terms) fail.
RELEVANCE_MIN = 0.12

_WORD = re.compile(r"[a-z][a-z0-9+#.-]{1,}")

# Common english + research-instruction words carry no topic signal.
_STOP = {
    "the", "a", "an", "and", "or", "for", "of", "to", "in", "on", "with", "that",
    "this", "these", "those", "is", "are", "be", "as", "by", "at", "from", "it",
    "its", "into", "over", "than", "then", "such", "can", "will", "may", "must",
    "should", "which", "when", "where", "how", "why", "what", "who", "not", "no",
    "evaluate", "compare", "comparison", "analyse", "analyze", "assess", "review",
    "research", "examine", "recommend", "design", "approach", "approaches", "using",
    "based", "system", "systems", "give", "giving", "versus", "vs", "study",
    "overview", "introduction", "glossary", "list", "wikipedia", "article",
    "three", "two", "different", "various", "general", "across", "between",
}


def _terms(text: str) -> list[str]:
    return [w for w in _WORD.findall((text or "").lower())
            if w not in _STOP and len(w) > 2]


@dataclass
class Question:
    """The pre-tokenised research question used to score every source."""

    terms: set[str]
    entity_words: list[set[str]]   # content words of each named entity


def build_question(objective: str, entities: list[str],
                   dimensions: list[str] | None = None) -> Question:
    terms = set(_terms(objective))
    for d in dimensions or []:
        terms.update(_terms(d))
    ent_words = []
    for e in entities:
        w = set(_terms(e))
        if w:
            terms.update(w)
            ent_words.append(w)
    return Question(terms=terms, entity_words=ent_words)


def is_assessable(title: str, snippet: str, publisher: str = "") -> bool:
    """True when there is real text to judge (a title beyond the domain, or a snippet)."""
    t = (title or "").strip().lower()
    dom = (publisher or "").strip().lower()
    has_title = bool(t) and t != dom and t != dom.removeprefix("www.")
    return has_title or bool((snippet or "").strip())


def score(title: str, snippet: str, question: Question) -> tuple[float, str]:
    """Return (relevance in [0,1], human-readable basis) for a source."""
    src = set(_terms(title)) | set(_terms(snippet))
    if not src or not question.terms:
        return 0.0, "no shared content terms"
    shared = question.terms & src
    # Otsuka-Ochiai coefficient: |A∩B| / sqrt(|A|·|B|) — cosine over binary vectors.
    cos = len(shared) / math.sqrt(len(question.terms) * len(src))

    # A named entity from the question appearing in the source is a strong signal.
    entity_hit = any(ew and len(ew & src) / len(ew) >= 0.5
                     for ew in question.entity_words)
    rel = max(cos, 0.6) if entity_hit else cos
    rel = round(min(rel, 1.0), 3)

    top = ", ".join(sorted(shared)[:6]) or "none"
    basis = (f"binary-cosine {cos:.2f} over shared terms [{top}]"
             + ("; matches a named entity" if entity_hit else ""))
    return rel, basis
