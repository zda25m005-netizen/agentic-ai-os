"""Map an Analysis Artifact -> the existing Report IR (Phase 10).

This is the deterministic bridge from the evidence graph to the report schema.
Every rendered element traces to the artifact: findings carry the source numbers
of their evidence claims, the comparison matrix is the evidence-linked
comparison engine's output, and the quantitative table shows each number's
derivation. No content is invented here; the optional LLM synthesis step
(Phase 12) only fills interpretation/implication/summary over this structure.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime

from app.analysis.artifact import AnalysisArtifact, ArtifactClaim, ArtifactFinding
from app.analysis.decision import derive_decision
from app.analysis.evidence_graph import build_graph, render_ascii
from app.analysis.scoring import EvidenceScorecard, _polarity, score_artifact
from app.exec.report import (
    Finding,
    Report,
    ReportSection,
    Scorecard,
    SourceRecord,
    Table,
)

_CONF_ORDER = {"High": 3, "Medium": 2, "Low": 1}


def _evidence_scorecard(artifact: AnalysisArtifact) -> tuple[
        Scorecard | None, list[dict], list[dict], dict]:
    """Evidence-weighted scorecard + per-cell breakdown + rationale + final decision."""
    esc: EvidenceScorecard = score_artifact(artifact)
    if not (esc.entities and esc.cells):
        return None, [], [], {}
    decision = derive_decision(artifact, esc).as_dict()
    ref_of = {s.id: i + 1 for i, s in enumerate(artifact.sources)}
    scorecard = Scorecard(
        dimensions=esc.criteria, entities=esc.entities, scores=esc.matrix(),
        methodology="Evidence-weighted: each 0-5 score is derived from supporting vs "
                    "contradicting claims across sources (transparent heuristic, not a "
                    "measured statistic).")
    evidence_scores = [{
        "entity": c.entity, "criterion": c.criterion, "score": c.score,
        "supporting": c.supporting, "contradicting": c.contradicting,
        "confidence": c.confidence, "rationale": c.rationale,
        "refs": sorted({ref_of[s] for s in c.source_ids if s in ref_of}),
    } for c in esc.cells]
    scoring_rationale = []
    for cr in esc.criteria:
        cells = [c for c in esc.cells if c.criterion == cr]
        sup = sum(c.supporting for c in cells)
        con = sum(c.contradicting for c in cells)
        conf = min((c.confidence for c in cells), key=lambda x: _CONF_ORDER.get(x, 1)) \
            if cells else "Low"
        scoring_rationale.append({
            "criterion": cr,
            "reason": f"Scores derived from {sup} supporting vs {con} contradicting "
                      f"evidence claim(s) mapped to this criterion across the options.",
            "confidence": conf})
    return scorecard, evidence_scores, scoring_rationale, decision


def _finding_title(f: ArtifactFinding, claim_by_id: dict[str, ArtifactClaim]) -> str:
    for cid in f.evidence_ids:
        c = claim_by_id.get(cid)
        if c and c.entity:
            return c.entity[:80]
    for cid in f.evidence_ids:
        c = claim_by_id.get(cid)
        if c and c.category:
            return c.category.title()[:80]
    return "Finding"


def _finding_body(f: ArtifactFinding) -> str:
    parts = [f.observation.strip()]
    if f.interpretation.strip():
        parts.append(f.interpretation.strip())
    if f.implication.strip():
        parts.append(f.implication.strip())
    return " ".join(p for p in parts if p)


def _evidence_failures(artifact: AnalysisArtifact) -> list[dict]:
    """Grounded failure modes: negative-polarity claims per option (mechanism = the claim).

    Only the mechanism is asserted (it is a real claim); probability/impact/etc. are
    left blank rather than fabricated. The LLM layer enriches these when present.
    """
    ewords = {e: {w for w in re.findall(r"[a-z0-9]+", e.lower()) if len(w) > 2}
              for e in artifact.entities}
    rows: list[dict] = []
    per_entity: dict[str, int] = {}
    for c in artifact.claims:
        ent = next((e for e in artifact.entities
                    if (c.entity and c.entity.lower() == e.lower())
                    or (ewords[e] and sum(w in c.statement.lower() for w in ewords[e])
                        / len(ewords[e]) >= 0.5)), "")
        if not ent or _polarity(c.statement) >= 0 or per_entity.get(ent, 0) >= 4:
            continue
        per_entity[ent] = per_entity.get(ent, 0) + 1
        words = c.statement.split()
        label = " ".join(words[:7]) + ("..." if len(words) > 7 else "")
        rows.append({"option": ent, "failure": label, "mechanism": c.statement.strip(),
                     "probability": "", "impact": "", "detection": "",
                     "mitigation": "", "residual_risk": ""})
    return rows


def artifact_to_report(artifact: AnalysisArtifact, *, date: str = "",
                       status: str = "Completed") -> Report:
    """Build a Report IR grounded entirely in the artifact's evidence graph."""
    date = date or datetime.now(UTC).strftime("%d %B %Y")
    src_ref = {s.id: i + 1 for i, s in enumerate(artifact.sources)}
    source_records = [
        SourceRecord(ref=i + 1, url=s.url, publisher=s.publisher,
                     stype=s.source_type.title(), credibility=s.credibility,
                     freshness=s.freshness(), citation=s.citation(),
                     relevance=s.relevance)
        for i, s in enumerate(artifact.sources)
    ]
    claim_by_id = {c.id: c for c in artifact.claims}

    # Claim-level evidence matrix (source-backed claims, most-verified first).
    _vrank = {"Verified": 0, "Partially verified": 1, "Conflicting": 2, "Unverified": 3}
    evidence_matrix = [{
        "claim": c.statement.strip()[:200],
        "refs": sorted({src_ref[s] for s in c.source_ids if s in src_ref}),
        "verification": c.verification.value,
        "confidence": c.confidence,
    } for c in sorted(artifact.claims, key=lambda c: _vrank.get(c.verification.value, 3))
        if c.source_ids][:12]

    findings: list[Finding] = []
    for f in artifact.findings:
        refs = sorted({
            src_ref[sid] for cid in f.evidence_ids
            if (c := claim_by_id.get(cid)) for sid in c.source_ids if sid in src_ref
        })
        findings.append(Finding(
            title=_finding_title(f, claim_by_id), body=_finding_body(f),
            confidence=f.confidence, source_refs=refs))

    sections: list[ReportSection] = []
    if artifact.comparisons:
        ents = artifact.entities or sorted(
            {e for cmp in artifact.comparisons for e in cmp.entities})
        cols = ["Dimension", *ents]
        rows = [[cmp.dimension] + [cmp.entities.get(e, {}).get("assessment", "-")[:140]
                                   for e in ents] for cmp in artifact.comparisons]
        sections.append(ReportSection("Comparison Matrix", [], table=Table(
            cols, rows, "Qualitative, evidence-linked comparison (each cell traces to claims).")))

    if artifact.metrics:
        rows = [[m.name, f"{m.value:g}", m.unit, m.entity or "-", m.derivation[:70]]
                for m in artifact.metrics]
        sections.append(ReportSection("Quantitative Analysis", [], table=Table(
            ["Metric", "Value", "Unit", "Entity", "Basis"], rows,
            "Values are reported from sources or computed with the stated formula.")))

    limitations = list(artifact.limitations) + list(artifact.uncertainties) + [
        "Interpretive statements reflect analysis of the available material, "
        "not measured facts."]

    scorecard, evidence_scores, scoring_rationale, decision = _evidence_scorecard(artifact)
    # A recommendation must be as confident as the evidence — no more.
    for flag in decision.get("consistency_flags", []):
        limitations.append(flag)

    # Research Evidence Graph: the explicit question -> claims -> sources -> findings
    # -> scores -> decision chain, rendered as a diagram in the methodology section.
    graph = build_graph(artifact, score_artifact(artifact))
    evidence_graph = "```\n" + render_ascii(
        graph, decision_summary=decision.get("summary", ""),
        confidence=decision.get("confidence", ""),
        dropped=artifact.dropped_sources) + "\n```"

    return Report(
        title=artifact.objective, subtitle="Analytical Report",
        report_type=artifact.mission_type,
        meta={"date": date, "sources": len(artifact.sources), "status": status},
        findings=findings, sections=sections, source_records=source_records,
        sources=[s.url for s in artifact.sources], limitations=limitations,
        scorecard=scorecard, evidence_scores=evidence_scores,
        scoring_rationale=scoring_rationale, decision=decision,
        evidence_graph=evidence_graph, evidence_matrix=evidence_matrix,
        failure_analysis=_evidence_failures(artifact),
    )
