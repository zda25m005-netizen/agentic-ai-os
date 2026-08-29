"""Claim verification: cross-source corroboration + contradiction detection.

Genuine research depth comes from *not* trusting a single source. This module
groups claims by topic (entity + category), checks how many **independent**
sources (distinct publishers) support a topic, and flags contradictions where
sources disagree. Claims are then promoted/demoted:

    >= 2 independent agreeing sources        -> VERIFIED
    1 source                                 -> PARTIALLY_VERIFIED
    sources disagree                         -> CONFLICTING  (never hidden)
    no source                                -> UNVERIFIED

Sources also receive a corroboration factor that feeds the reliability model.
All heuristics are conservative and transparent; contradictions are surfaced,
not buried, so the report can honestly say "sources differ on this point".
"""
from __future__ import annotations

import re

from app.analysis.artifact import (
    AnalysisArtifact,
    ArtifactClaim,
    ArtifactSource,
    Verification,
)

_NEG = (" not ", " no ", " never", "cannot", "can't", "isn't", "doesn't", "won't",
        "n't ", " lacks ", " without ", " fails")
_ANTONYMS = (
    ("increase", "decrease"), ("higher", "lower"), ("faster", "slower"),
    ("better", "worse"), ("cheaper", "expensive"), ("improve", "degrade"),
    ("gains", "loses"), ("rises", "falls"), ("more ", "less "),
)


def _domains(claim: ArtifactClaim, by_id: dict[str, ArtifactSource]) -> set[str]:
    return {by_id[s].publisher for s in claim.source_ids if s in by_id and by_id[s].publisher}


def _has_neg(text: str) -> bool:
    return any(k in f" {text.lower()} " for k in _NEG)


def _contradicts(a: str, b: str) -> bool:
    """Conservative: opposing polarity on overlapping content, or antonym pairs."""
    la, lb = a.lower(), b.lower()
    for x, y in _ANTONYMS:
        if (x in la and y in lb) or (y in la and x in lb):
            return True
    if _has_neg(la) != _has_neg(lb):
        # only a contradiction if the two claims are actually about the same thing
        ta = set(re.findall(r"[a-z]{5,}", la))
        tb = set(re.findall(r"[a-z]{5,}", lb))
        if ta and len(ta & tb) / len(ta) >= 0.4:
            return True
    return False


def _topic_key(c: ArtifactClaim) -> str:
    base = f"{c.entity}|{c.category}".strip("|")
    return base or f"__solo__{c.id}"   # ungrouped claims never falsely corroborate


def verify(artifact: AnalysisArtifact) -> dict:
    """Promote/demote claims by corroboration and flag contradictions (mutates)."""
    by_id = {s.id: s for s in artifact.sources}
    groups: dict[str, list[ArtifactClaim]] = {}
    for c in artifact.claims:
        groups.setdefault(_topic_key(c), []).append(c)

    contradictions: list[tuple[str, str]] = []
    verified = partial = conflicting = unverified = 0
    corroborating: set[str] = set()   # source ids that participate in real corroboration
    conflicted_src: set[str] = set()

    for group in groups.values():
        conflict_ids: set[str] = set()
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                if _contradicts(group[i].statement, group[j].statement):
                    conflict_ids.update({group[i].id, group[j].id})
                    contradictions.append((group[i].id, group[j].id))
        agreeing = [c for c in group if c.id not in conflict_ids]
        indep = set().union(*[_domains(c, by_id) for c in agreeing]) if agreeing else set()

        for c in group:
            if c.id in conflict_ids:
                c.verification = Verification.CONFLICTING
                c.confidence = "Low"
                conflicting += 1
                conflicted_src.update(c.source_ids)
            elif len(indep) >= 2 and c.source_ids:
                c.verification = Verification.VERIFIED
                c.confidence = "High"
                verified += 1
                corroborating.update(c.source_ids)
            elif c.source_ids:
                c.verification = Verification.PARTIALLY_VERIFIED
                c.confidence = "Medium" if artifact.reliability_of(c) >= 0.8 else "Low"
                partial += 1
            else:
                c.verification = Verification.UNVERIFIED
                c.confidence = "Low"
                unverified += 1

    # feed corroboration back into source reliability
    for s in artifact.sources:
        if s.id in conflicted_src:
            s.rescore(0.75)
        elif s.id in corroborating:
            s.rescore(1.0)
        else:
            s.rescore(0.9)          # sole/limited corroboration

    return {
        "verified": verified, "partially_verified": partial,
        "conflicting": conflicting, "unverified": unverified,
        "contradictions": contradictions,
        "note": "Verification is a transparent heuristic over independent-source "
                "agreement; contradictions are surfaced, not hidden.",
    }
