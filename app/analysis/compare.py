"""Comparison engine: structured entity x dimension matrix from evidence.

For comparison missions this builds a matrix where each cell is a QUALITATIVE,
evidence-linked assessment (the strongest claim about that entity on that
dimension) with its claim IDs and an earned confidence. It deliberately does NOT
emit arbitrary numeric scores like "NVIDIA = 9.5" — quantitative values only come
from the quant engine's real numbers. Cells only appear where evidence exists.
"""
from __future__ import annotations

from app.analysis.artifact import (
    AnalysisArtifact,
    ArtifactClaim,
    Comparison,
    Verification,
)

_VERIF_RANK = {Verification.VERIFIED: 3, Verification.PARTIALLY_VERIFIED: 2,
               Verification.CONFLICTING: 1, Verification.UNVERIFIED: 0}
_CONF = {3: "High", 2: "Medium"}


def _matches(claim: ArtifactClaim, dimension: str) -> bool:
    d = dimension.lower()
    return (claim.category and claim.category.lower() in d) or d in claim.statement.lower()


def build_comparisons(
    artifact: AnalysisArtifact, dimensions: list[str] | None = None,
) -> list[Comparison]:
    """Assemble a qualitative, evidence-linked comparison matrix (mutates artifact)."""
    entities = artifact.entities or sorted({c.entity for c in artifact.claims if c.entity})
    dims = dimensions or artifact.dimensions or sorted(
        {c.category for c in artifact.claims if c.category})
    comparisons: list[Comparison] = []
    for dim in dims:
        cells: dict[str, dict] = {}
        for ent in entities:
            claims = [c for c in artifact.claims
                      if c.entity == ent and c.source_ids and _matches(c, dim)]
            if not claims:
                continue
            top = max(claims, key=lambda c: _VERIF_RANK.get(c.verification, 0))
            best = max(_VERIF_RANK.get(c.verification, 0) for c in claims)
            cells[ent] = {
                "assessment": top.statement,
                "evidence_ids": [c.id for c in claims],
                "confidence": _CONF.get(best, "Low"),
            }
        if cells:
            comparisons.append(Comparison(dimension=dim, entities=cells))
    artifact.comparisons = comparisons
    return comparisons
