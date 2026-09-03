"""Assemble the Analysis Artifact from a mission — the evidence-first pipeline.

Objective understanding -> per-task source + claim + metric extraction ->
verification/corroboration -> derived quantitative comparisons -> grounded
findings -> comparison matrix -> honest limitations/uncertainties. The result is
a single structured artifact that the report layer (Phase 10-12) consumes; the
LLM never sees raw task text, only this evidence graph. Fully deterministic and
network-free, so it is testable and cannot invent content.
"""

from __future__ import annotations

import re

from app.analysis.artifact import AnalysisArtifact, Verification, normalize_url
from app.analysis.claims import extract_claims, strip_noise
from app.analysis.compare import build_comparisons
from app.analysis.quant import derived_comparisons, extract_metrics
from app.analysis.reason import generate_findings
from app.analysis.relevance import (
    RELEVANCE_MIN,
    build_question,
    is_assessable,
)
from app.analysis.relevance import (
    score as relevance_score,
)
from app.analysis.verify import verify
from app.missions.models import Mission, Task

_URL = re.compile(r"https?://[^\s)\]]+")
_MTYPE = {
    " vs ": "COMPARISON",
    "compare": "COMPARISON",
    "comparison": "COMPARISON",
    "job": "JOB_MARKET",
    "hiring": "JOB_MARKET",
    "market": "MARKET_ANALYSIS",
    "architecture": "TECHNICAL_ANALYSIS",
    "algorithm": "TECHNICAL_ANALYSIS",
    "technical": "TECHNICAL_ANALYSIS",
    "approaches": "TECHNICAL_ANALYSIS",
}


def _mission_type(objective: str) -> str:
    o = objective.lower()
    for key, mtype in _MTYPE.items():
        if key in o:
            return mtype
    return "RESEARCH"


_LEAD_VERB = re.compile(
    r"^(compare|evaluate|analyse|analyze|assess|review|research|examine|contrast|"
    r"investigate|explore)\s+",
    re.I,
)


def _split_entities(text: str) -> list[str]:
    parts = re.split(r",|\band\b|\bvs\.?\b|\bversus\b", text, flags=re.I)
    out = []
    for p in parts:
        e = re.sub(r"\(.*?\)", "", p).strip(" .:;")
        e = _LEAD_VERB.sub("", e)  # drop a leading imperative verb
        e = re.sub(r"\s+for\s+.*$", "", e, flags=re.I)  # drop a trailing scope clause
        e = re.sub(r"\s{2,}", " ", e).strip()
        if 1 < len(e) <= 40 and e.lower() not in {"the", "a", "an"}:
            out.append(e)
    return out


def parse_objective(objective: str) -> tuple[list[str], list[str], str]:
    """Best-effort objective understanding: (entities, dimensions, mission_type)."""
    mtype = _mission_type(objective)
    entities: list[str] = []
    if ":" in objective:  # "... : A, B, C"
        entities = _split_entities(objective.rsplit(":", 1)[-1])
    if not entities and re.search(r"\bvs\.?\b|\bversus\b", objective, re.I):
        entities = _split_entities(objective)
    # "Compare A, B, and C for X" — split the option list after the leading verb,
    # dropping a trailing scope clause. Gated to comparison/technical missions so
    # a research objective with an "and" is not falsely split into entities.
    if not entities and mtype in {"COMPARISON", "TECHNICAL_ANALYSIS"}:
        tail = re.sub(r"\bfor\b.*$", "", objective, flags=re.I)
        cand = _split_entities(tail)
        if len(cand) >= 2:
            entities = cand
    entities = [e for e in entities if e][:5]
    return entities, [], mtype


def _apply_relevance_gate(art: AnalysisArtifact) -> None:
    """Score sources vs the objective; drop assessable off-topic ones (mutates)."""
    question = build_question(art.objective, art.entities, art.dimensions)
    dropped: list = []
    kept: list = []
    for s in art.sources:
        rel, basis = relevance_score(s.title, s.snippet, question)
        s.relevance, s.relevance_basis = rel, basis
        if is_assessable(s.title, s.snippet, s.publisher) and rel < RELEVANCE_MIN:
            dropped.append(s)
        else:
            kept.append(s)

    # Never leave an empty bibliography if any dropped source still shares some signal
    # with the question: rescue the best-scoring one or two (kept, but honestly labelled
    # low-relevance) rather than reporting "0 sources". Sources with zero shared terms
    # (truly off-topic, e.g. a Beatles page) are never rescued.
    if not kept and dropped:
        rescue = sorted(
            (s for s in dropped if (s.relevance or 0) > 0),
            key=lambda s: s.relevance or 0,
            reverse=True,
        )[:2]
        for s in rescue:
            dropped.remove(s)
            kept.append(s)

    if not dropped:
        return
    art.dropped_sources = len(dropped)
    drop_ids = {s.id for s in dropped}
    art.sources = kept
    for c in art.claims:
        c.source_ids = [x for x in c.source_ids if x not in drop_ids]
    for m in art.metrics:
        m.source_ids = [x for x in m.source_ids if x not in drop_ids]
    names = ", ".join(
        f"{(s.title or s.publisher)!r} (relevance {s.relevance:.2f})" for s in dropped[:4]
    )
    art.limitations.append(
        f"{len(dropped)} retrieved source(s) were excluded as off-topic for this "
        f"question and are not cited: {names}."
    )


def build_analysis_artifact(mission: Mission, tasks: list[Task]) -> AnalysisArtifact:
    """Run the evidence-first pipeline and return a complete Analysis Artifact."""
    entities, dimensions, mtype = parse_objective(mission.objective)
    art = AnalysisArtifact(
        objective=mission.objective, mission_type=mtype, entities=entities, dimensions=dimensions
    )

    done = [t for t in tasks if t.status.value == "done" and (t.result or "").strip()]
    next_claim = 1
    for t in done:
        urls = _URL.findall(t.result or "")
        source_ids = [art.add_source(u) for u in urls]
        claims = extract_claims(t.result or "", source_ids, entities, start=next_claim)
        # if the task targets a single entity, default un-attributed claims to it
        task_entity = next((e for e in entities if e.lower() in (t.description or "").lower()), "")
        for c in claims:
            if not c.entity and task_entity:
                c.entity = task_entity
        art.claims.extend(claims)
        next_claim += len(claims)
        art.metrics.extend(extract_metrics(strip_noise(t.result or ""), source_ids, task_entity))

    # Enrich sources with real bibliographic metadata gathered during research.
    # Match on a normalized URL so an arXiv version suffix / trailing slash still
    # attaches the retrieved title + authors (avoids bare "arxiv.org" citations).
    meta_by_url = {
        normalize_url(s.get("url")): s
        for s in ((mission.meta or {}).get("sources") or [])
        if isinstance(s, dict) and s.get("url")
    }
    for s in art.sources:
        meta = meta_by_url.get(normalize_url(s.url))
        if meta:
            s.enrich(meta)

    # Relevance gate: score every source against the research question and drop
    # assessable sources that are off-topic BEFORE they can enter the evidence
    # graph, the scorecard or the bibliography. Sources with no readable text
    # (bare domains) are kept — missing metadata is not evidence of irrelevance.
    _apply_relevance_gate(art)

    verify(art)
    art.metrics.extend(derived_comparisons(art.metrics))
    generate_findings(art)
    build_comparisons(art)

    # honest limitations + uncertainties from the actual evidence state
    if not art.sources:
        art.limitations.append(
            "No external references were available; conclusions are indicative only."
        )
    if any(c.verification == Verification.CONFLICTING for c in art.claims):
        art.uncertainties.append(
            "Sources differ on some points; conflicting claims are flagged, not resolved."
        )
    if not art.metrics:
        art.uncertainties.append(
            "Quantitative comparison was not possible from the available evidence."
        )
    return art
