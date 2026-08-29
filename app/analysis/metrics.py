"""Report-quality metrics (Phase 13): score an analysis on evidence discipline.

These are evaluation metrics for the eval/observability layer — how well a
report is grounded in evidence — not user-facing scores. They operate on the raw
(claims, findings, sources) so the same rubric can score both the evidence-first
pipeline and a naive baseline for the ablation study.
"""
from __future__ import annotations

import re

from app.analysis.artifact import (
    AnalysisArtifact,
    ArtifactClaim,
    ArtifactFinding,
    ArtifactSource,
    Verification,
)

_FIG = re.compile(r"\d+(?:\.\d+)?\s?%|\$\s?\d")


def score(
    claims: list[ArtifactClaim], findings: list[ArtifactFinding], sources: list[ArtifactSource],
) -> dict:
    """Evidence-discipline metrics in [0,1] (higher is better, except where noted)."""
    nc = len(claims) or 1
    nf = len(findings) or 1
    by_id = {c.id: c for c in claims}
    grounded = [c for c in claims if c.source_ids]
    verified = [c for c in claims if c.verification == Verification.VERIFIED]
    conflicting = [c for c in claims if c.verification == Verification.CONFLICTING]
    fig_unsourced = [c for c in claims if not c.source_ids and _FIG.search(c.statement)]

    def cited(f: ArtifactFinding) -> bool:
        return any((by_id.get(cid) and by_id[cid].source_ids) for cid in f.evidence_ids)

    rel = [s.reliability for s in sources]
    return {
        "citation_coverage": round(sum(cited(f) for f in findings) / nf, 3),
        "claim_grounding": round(len(grounded) / nc, 3),
        "verified_rate": round(len(verified) / nc, 3),
        "unsupported_figure_rate": round(len(fig_unsourced) / nc, 3),  # lower is better
        "contradictions_flagged": len(conflicting),
        "avg_source_reliability": round(sum(rel) / len(rel), 3) if rel else 0.0,
        "n_claims": len(claims), "n_findings": len(findings), "n_sources": len(sources),
    }


def score_artifact(artifact: AnalysisArtifact) -> dict:
    return score(artifact.claims, artifact.findings, artifact.sources)
