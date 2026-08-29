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

from app.analysis.artifact import AnalysisArtifact, Verification
from app.analysis.claims import extract_claims, strip_noise
from app.analysis.compare import build_comparisons
from app.analysis.quant import derived_comparisons, extract_metrics
from app.analysis.reason import generate_findings
from app.analysis.verify import verify
from app.missions.models import Mission, Task

_URL = re.compile(r"https?://[^\s)\]]+")
_MTYPE = {
    " vs ": "COMPARISON", "compare": "COMPARISON", "comparison": "COMPARISON",
    "job": "JOB_MARKET", "hiring": "JOB_MARKET",
    "market": "MARKET_ANALYSIS",
    "architecture": "TECHNICAL_ANALYSIS", "algorithm": "TECHNICAL_ANALYSIS",
    "technical": "TECHNICAL_ANALYSIS", "approaches": "TECHNICAL_ANALYSIS",
}


def _mission_type(objective: str) -> str:
    o = objective.lower()
    for key, mtype in _MTYPE.items():
        if key in o:
            return mtype
    return "RESEARCH"


_LEAD_VERB = re.compile(
    r"^(compare|evaluate|analyse|analyze|assess|review|research|examine|contrast|"
    r"investigate|explore)\s+", re.I)


def _split_entities(text: str) -> list[str]:
    parts = re.split(r",|\band\b|\bvs\.?\b|\bversus\b", text, flags=re.I)
    out = []
    for p in parts:
        e = re.sub(r"\(.*?\)", "", p).strip(" .:;")
        e = _LEAD_VERB.sub("", e)                 # drop a leading imperative verb
        e = re.sub(r"\s+for\s+.*$", "", e, flags=re.I)   # drop a trailing scope clause
        e = re.sub(r"\s{2,}", " ", e).strip()
        if 1 < len(e) <= 40 and e.lower() not in {"the", "a", "an"}:
            out.append(e)
    return out


def parse_objective(objective: str) -> tuple[list[str], list[str], str]:
    """Best-effort objective understanding: (entities, dimensions, mission_type)."""
    mtype = _mission_type(objective)
    entities: list[str] = []
    if ":" in objective:                          # "... : A, B, C"
        entities = _split_entities(objective.rsplit(":", 1)[-1])
    if not entities and re.search(r"\bvs\.?\b|\bversus\b", objective, re.I):
        entities = _split_entities(objective)
    entities = [e for e in entities if e][:5]
    return entities, [], mtype


def build_analysis_artifact(mission: Mission, tasks: list[Task]) -> AnalysisArtifact:
    """Run the evidence-first pipeline and return a complete Analysis Artifact."""
    entities, dimensions, mtype = parse_objective(mission.objective)
    art = AnalysisArtifact(objective=mission.objective, mission_type=mtype,
                           entities=entities, dimensions=dimensions)

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

    verify(art)
    art.metrics.extend(derived_comparisons(art.metrics))
    generate_findings(art)
    build_comparisons(art)

    # honest limitations + uncertainties from the actual evidence state
    if not art.sources:
        art.limitations.append(
            "No external references were available; conclusions are indicative only.")
    if any(c.verification == Verification.CONFLICTING for c in art.claims):
        art.uncertainties.append(
            "Sources differ on some points; conflicting claims are flagged, not resolved.")
    if not art.metrics:
        art.uncertainties.append(
            "Quantitative comparison was not possible from the available evidence.")
    return art
