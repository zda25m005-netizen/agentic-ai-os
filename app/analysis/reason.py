"""Finding generation: evidence-backed claims -> structured findings.

A finding follows Evidence -> Observation -> Interpretation -> Implication. The
system builds the grounded part deterministically: it groups *evidence-backed*
factual claims by topic, synthesises the strongest ones into an OBSERVATION, and
records the exact claim IDs as evidence plus a confidence earned from
verification. Interpretation and implication are intentionally left blank here —
they are the LLM's job in the synthesis step (Phase 9), and it may only reason
over these observations, never invent new facts. Ordering surfaces the
best-supported topics first.
"""
from __future__ import annotations

from app.analysis.artifact import (
    AnalysisArtifact,
    ArtifactClaim,
    ArtifactFinding,
    StatementType,
    Verification,
)

_GROUNDED = {StatementType.FACT, StatementType.OBSERVATION}
_VERIF_RANK = {Verification.VERIFIED: 3, Verification.PARTIALLY_VERIFIED: 2,
               Verification.CONFLICTING: 1, Verification.UNVERIFIED: 0}
_CONF_RANK = {"High": 3, "Medium": 2, "Low": 1, "Analytical": 1}


def _topic(c: ArtifactClaim) -> str:
    return f"{c.entity}|{c.category}".strip("|") or c.id


def _rank(c: ArtifactClaim) -> tuple[int, int]:
    return (_VERIF_RANK.get(c.verification, 0), _CONF_RANK.get(c.confidence, 1))


def _observation(claims: list[ArtifactClaim]) -> str:
    ordered = sorted(claims, key=_rank, reverse=True)
    obs = ordered[0].statement.strip()
    # add a second, distinct supporting claim if it adds content and stays concise
    for c in ordered[1:]:
        if c.statement.strip() != obs and len(obs) + len(c.statement) < 300:
            obs = f"{obs} {c.statement.strip()}"
            break
    return obs


def _confidence(claims: list[ArtifactClaim]) -> str:
    best = max((_VERIF_RANK.get(c.verification, 0) for c in claims), default=0)
    return {3: "High", 2: "Medium"}.get(best, "Low")


def generate_findings(artifact: AnalysisArtifact, max_findings: int = 6) -> list[ArtifactFinding]:
    """Build grounded finding skeletons from evidence-backed factual claims."""
    groups: dict[str, list[ArtifactClaim]] = {}
    for c in artifact.claims:
        if c.source_ids and c.statement_type in _GROUNDED \
                and c.verification != Verification.CONFLICTING:
            groups.setdefault(_topic(c), []).append(c)

    def support(claims: list[ArtifactClaim]) -> tuple:
        best_verif = max((_VERIF_RANK.get(c.verification, 0) for c in claims), default=0)
        return (best_verif, len(claims), max(artifact.reliability_of(c) for c in claims))

    ranked = sorted(groups.values(), key=support, reverse=True)[:max_findings]
    findings: list[ArtifactFinding] = []
    for i, claims in enumerate(ranked, 1):
        findings.append(ArtifactFinding(
            id=f"F{i}",
            observation=_observation(claims),
            interpretation="",   # filled by the LLM synthesis step, over this evidence only
            implication="",
            evidence_ids=[c.id for c in claims],
            confidence=_confidence(claims),
        ))
    artifact.findings = findings
    return findings
