"""Map an Analysis Artifact -> the existing Report IR (Phase 10).

This is the deterministic bridge from the evidence graph to the report schema.
Every rendered element traces to the artifact: findings carry the source numbers
of their evidence claims, the comparison matrix is the evidence-linked
comparison engine's output, and the quantitative table shows each number's
derivation. No content is invented here; the optional LLM synthesis step
(Phase 12) only fills interpretation/implication/summary over this structure.
"""
from __future__ import annotations

from datetime import UTC, datetime

from app.analysis.artifact import AnalysisArtifact, ArtifactClaim, ArtifactFinding
from app.exec.report import Finding, Report, ReportSection, SourceRecord, Table


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


def artifact_to_report(artifact: AnalysisArtifact, *, date: str = "",
                       status: str = "Completed") -> Report:
    """Build a Report IR grounded entirely in the artifact's evidence graph."""
    date = date or datetime.now(UTC).strftime("%d %B %Y")
    src_ref = {s.id: i + 1 for i, s in enumerate(artifact.sources)}
    source_records = [
        SourceRecord(ref=i + 1, url=s.url, publisher=s.publisher,
                     stype=s.source_type.title(), credibility=s.credibility,
                     freshness=s.freshness(), citation=s.citation())
        for i, s in enumerate(artifact.sources)
    ]
    claim_by_id = {c.id: c for c in artifact.claims}

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

    return Report(
        title=artifact.objective, subtitle="Analytical Report",
        report_type=artifact.mission_type,
        meta={"date": date, "sources": len(artifact.sources), "status": status},
        findings=findings, sections=sections, source_records=source_records,
        sources=[s.url for s in artifact.sources], limitations=limitations,
    )
