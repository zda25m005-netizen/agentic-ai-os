"""Claim extraction: research text + its sources -> atomic ArtifactClaims.

Deterministic and LLM-free so it is testable and never invents content — it only
segments what the research already produced and links each claim to the sources
that were gathered with it. Epistemic status is classified from linguistic cues
(hedging -> Inference, imperative -> Recommendation, otherwise Fact/Observation)
so the system never labels a hedged guess as a fact. Verification here is
deliberately conservative (sourced -> Partially verified); genuine cross-source
corroboration that can promote a claim to VERIFIED is Phase 4-5.
"""
from __future__ import annotations

import re

from app.analysis.artifact import ArtifactClaim, StatementType, Verification

_URL = re.compile(r"https?://\S+")
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
_SOURCES_BLOCK = re.compile(r"\n+\s*sources?\s*:\s*(?:\n.*)?$", re.IGNORECASE | re.DOTALL)

_HEDGE = ("may ", "might ", "could ", "likely", "suggests", "indicates", "implies",
          "appears", "potentially", "probably", "expected to", "seems", "tends to",
          "can be", "would ")
_RECO = ("should ", "recommend", "we suggest", "prefer ", "avoid ", "must ", "ought to",
         "is advised", "consider ")
_CATEGORY = {
    "architecture": ("architecture", "pipeline", "retriev", "index", "embedding", "store"),
    "performance": ("latency", "throughput", "accuracy", "recall", "precision", "speed"),
    "cost": ("cost", "price", "expensive", "cheap", "budget", "compute"),
    "reliability": ("fail", "error", "robust", "reliab", "drift", "stale"),
    "ecosystem": ("ecosystem", "adoption", "community", "developer", "support"),
}


def strip_noise(text: str) -> str:
    """Remove a trailing 'Sources:' block and bare URLs (kept in the source list)."""
    return _URL.sub("", _SOURCES_BLOCK.sub("", text or "")).strip()


def classify_statement(sentence: str, has_source: bool) -> StatementType:
    low = sentence.lower()
    if any(k in low for k in _RECO):
        return StatementType.RECOMMENDATION
    if any(k in low for k in _HEDGE):
        return StatementType.INFERENCE
    return StatementType.FACT if has_source else StatementType.OBSERVATION


def _category(sentence: str) -> str:
    low = sentence.lower()
    for cat, keys in _CATEGORY.items():
        if any(k in low for k in keys):
            return cat
    return ""


def _entity(sentence: str, entities: list[str]) -> str:
    low = sentence.lower()
    for e in entities:
        if e and e.lower() in low:
            return e
    return ""


def _is_claim(sentence: str) -> bool:
    s = sentence.strip()
    if not (16 <= len(s) <= 400):
        return False
    if s.endswith("?") or s.startswith(("-", "*", "#", "|")):
        return False
    return len(s.split()) >= 4          # needs to be a real sentence, not a heading


def extract_claims(
    text: str, source_ids: list[str], entities: list[str] | None = None, start: int = 1,
) -> list[ArtifactClaim]:
    """Segment `text` into atomic claims, each linked to `source_ids`."""
    entities = entities or []
    has_source = bool(source_ids)
    verification = Verification.PARTIALLY_VERIFIED if has_source else Verification.UNVERIFIED
    confidence = "Medium" if len(source_ids) >= 2 else ("Low" if source_ids else "Low")

    claims: list[ArtifactClaim] = []
    seen: set[str] = set()
    idx = start
    for sent in _SENT_SPLIT.split(strip_noise(text)):
        s = sent.strip()
        if not _is_claim(s):
            continue
        key = re.sub(r"\W+", " ", s.lower()).strip()
        if key in seen:
            continue
        seen.add(key)
        claims.append(ArtifactClaim(
            id=f"C{idx}", statement=s, statement_type=classify_statement(s, has_source),
            entity=_entity(s, entities), category=_category(s), source_ids=list(source_ids),
            evidence=s, verification=verification, confidence=confidence,
        ))
        idx += 1
    return claims
