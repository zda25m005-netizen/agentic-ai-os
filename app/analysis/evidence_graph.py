"""Research Evidence Graph — the explicit chain from question to decision.

Every step of the analysis is a node with real edges: the research question fans
out into claims, each claim is backed by the sources that support it, claims roll
up into findings, findings and the scored criteria produce the evidence-weighted
scores, and the scores drive the decision. Making this graph explicit is what
lets the report *show its work* — the same object underlies the pipeline's
reasoning and the diagram printed in the methodology section.

    RESEARCH QUESTION -> CLAIMS -> SOURCES -> FINDINGS -> SCORES -> DECISION

Pure and deterministic; built from the artifact, the evidence scorecard and the
derived decision.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.analysis.artifact import AnalysisArtifact, Verification
from app.analysis.scoring import EvidenceScorecard


@dataclass
class EvidenceGraph:
    question: str
    counts: dict = field(default_factory=dict)
    edges: list[tuple[str, str]] = field(default_factory=list)   # (from_id, to_id)

    def edge_count(self) -> int:
        return len(self.edges)


def build_graph(art: AnalysisArtifact, esc: EvidenceScorecard | None = None) -> EvidenceGraph:
    edges: list[tuple[str, str]] = []
    for c in art.claims:
        for sid in c.source_ids:
            edges.append((c.id, sid))
    for f in art.findings:
        for cid in f.evidence_ids:
            edges.append((f.id, cid))
    counts = {
        "claims": len(art.claims),
        "sources": len(art.sources),
        "findings": len(art.findings),
        "verified": sum(c.verification == Verification.VERIFIED for c in art.claims),
        "partial": sum(c.verification == Verification.PARTIALLY_VERIFIED for c in art.claims),
        "conflicting": sum(c.verification == Verification.CONFLICTING for c in art.claims),
        "options": len(esc.entities) if esc else len(art.entities),
        "criteria": len(esc.criteria) if esc else 0,
    }
    return EvidenceGraph(question=art.objective, counts=counts, edges=edges)


def _center(s: str, width: int = 74) -> str:
    s = s[: width - 2]
    pad = max(0, (width - len(s)) // 2)
    return " " * pad + s


def render_ascii(graph: EvidenceGraph, decision_summary: str = "",
                 confidence: str = "", dropped: int = 0) -> str:
    """A monospaced pipeline diagram filled with the graph's real counts."""
    c = graph.counts
    q = graph.question.strip()
    q = (q[:52] + "...") if len(q) > 55 else q
    verif = (f"{c['verified']} verified / {c['partial']} partial / "
             f"{c['conflicting']} conflicting")
    src = f"{c['sources']} kept"
    if dropped:
        src += f", {dropped} off-topic dropped by relevance gate"
    dec = decision_summary.strip()
    dec = (dec[:52] + "...") if len(dec) > 55 else (dec or "recommendation")
    conf = f"  [confidence: {confidence}]" if confidence else ""
    lines = [
        _center("RESEARCH QUESTION"),
        _center(q),
        _center("|"),
        _center("v"),
        _center(f"CLAIMS EXTRACTED: {c['claims']}"),
        _center(f"({verif})"),
        _center("|"),
        _center("v"),
        _center(f"SOURCES: {src}"),
        _center("|"),
        _center("v"),
        _center(f"EVIDENCE SYNTHESIS -> FINDINGS: {c['findings']}"),
        _center("|"),
        _center("v"),
        _center(f"EVIDENCE-WEIGHTED SCORES: {c['options']} options x {c['criteria']} criteria"),
        _center("|"),
        _center("v"),
        _center("DECISION" + conf),
        _center(dec),
    ]
    return "\n".join(lines)
