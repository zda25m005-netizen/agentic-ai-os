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

# Split on hyphens so "fine-tuning" == "fine tuning" and "long-term" == "long term";
# keeps tokenisation consistent between entities, titles and URL slugs.
_WORD = re.compile(r"[a-z][a-z0-9+#.]{1,}")

# Common english + research-instruction words carry no topic signal.
_STOP = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "for",
    "of",
    "to",
    "in",
    "on",
    "with",
    "that",
    "this",
    "these",
    "those",
    "is",
    "are",
    "be",
    "as",
    "by",
    "at",
    "from",
    "it",
    "its",
    "into",
    "over",
    "than",
    "then",
    "such",
    "can",
    "will",
    "may",
    "must",
    "should",
    "which",
    "when",
    "where",
    "how",
    "why",
    "what",
    "who",
    "not",
    "no",
    "evaluate",
    "compare",
    "comparison",
    "analyse",
    "analyze",
    "assess",
    "review",
    "research",
    "examine",
    "recommend",
    "design",
    "approach",
    "approaches",
    "using",
    "based",
    "system",
    "systems",
    "give",
    "giving",
    "versus",
    "vs",
    "study",
    "overview",
    "introduction",
    "glossary",
    "list",
    "wikipedia",
    "article",
    "three",
    "two",
    "different",
    "various",
    "general",
    "across",
    "between",
}


def _terms(text: str) -> list[str]:
    return [w for w in _WORD.findall((text or "").lower()) if w not in _STOP and len(w) > 2]


@dataclass
class Question:
    """The pre-tokenised research question used to score every source."""

    terms: set[str]
    entity_words: list[set[str]]  # content words of each named entity
    acronyms: list[str] = None  # short uppercase entities (e.g. "RAG")

    def __post_init__(self) -> None:
        if self.acronyms is None:
            self.acronyms = []


def build_question(
    objective: str, entities: list[str], dimensions: list[str] | None = None
) -> Question:
    terms = set(_terms(objective))
    for d in dimensions or []:
        terms.update(_terms(d))
    ent_words, acronyms = [], []
    for e in entities:
        w = set(_terms(e))
        if w:
            terms.update(w)
            ent_words.append(w)
        bare = e.strip()
        if 2 <= len(bare) <= 6 and bare.isupper() and bare.isalpha():
            acronyms.append(bare.lower())
    return Question(terms=terms, entity_words=ent_words, acronyms=acronyms)


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
    # A single-word entity matches on its word; a multi-word entity ("Structured
    # Memory") needs >=2 of its words present, so a page that merely shares one word
    # ("Virtual memory", "Semi-structured data") is NOT treated as an entity match.
    def _ent_match(ew: set[str]) -> bool:
        shared = len(ew & src)
        return shared >= 2 if len(ew) >= 2 else (shared >= 1 and len(ew) == 1)

    entity_hit = any(ew and _ent_match(ew) for ew in question.entity_words)
    # Acronym match: the acronym appears as a standalone token anywhere ("...(RAG)..."
    # in an abstract), or its expansion shows up as consecutive-word initials in the
    # TITLE ("Retrieval Augmented Generation" -> RAG). Token match is reliable; initials
    # are title-only to avoid chance hits in long snippets.
    if not entity_hit and question.acronyms:
        tokens = set(src)
        initials = "".join(w[0] for w in _WORD.findall((title or "").lower()))
        entity_hit = any(a in tokens or a in initials for a in question.acronyms)
    # Entity match is a strong signal. Otherwise trust the content cosine: a page that
    # shares only a generic word ("memory" in an OS article) scores low once its full
    # text is considered, while a real paper that shares several terms clears the gate.
    # The one guard we keep is for *title-only* sources (no snippet fetched): there, a
    # single incidentally-shared word is not enough, so cap it below the gate.
    if entity_hit:
        rel = max(cos, 0.6)
    elif len(shared) < 2 and len(_terms(snippet)) < 8:
        rel = min(cos, 0.10)  # thin/title-only + one shared word -> not relevant
    else:
        rel = cos
    rel = round(min(rel, 1.0), 3)

    top = ", ".join(sorted(shared)[:6]) or "none"
    basis = f"binary-cosine {cos:.2f} over shared terms [{top}]" + (
        "; matches a named entity" if entity_hit else ""
    )
    return rel, basis
