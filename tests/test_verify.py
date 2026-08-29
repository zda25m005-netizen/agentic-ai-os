"""Verification: corroboration promotes claims, contradictions are flagged."""
from app.analysis.artifact import AnalysisArtifact, ArtifactClaim, StatementType, Verification
from app.analysis.verify import _contradicts, verify


def _art() -> AnalysisArtifact:
    a = AnalysisArtifact(objective="Compare RAG and Fine-tuning", entities=["RAG"])
    a.add_source("https://arxiv.org/abs/2005.11401")          # S1 arxiv.org
    a.add_source("https://en.wikipedia.org/wiki/Retrieval-augmented_generation")  # S2 wikipedia
    a.add_source("https://reuters.com/tech/rag")              # S3 reuters
    return a


def test_two_independent_sources_verify_a_claim():
    a = _art()
    a.claims = [
        ArtifactClaim("C1", "RAG retrieves documents at query time.",
                      StatementType.FACT, "RAG", "architecture", ["S1", "S2"]),
    ]
    summary = verify(a)
    assert a.claims[0].verification == Verification.VERIFIED
    assert a.claims[0].confidence == "High"
    assert summary["verified"] == 1


def test_single_source_is_partial_only():
    a = _art()
    a.claims = [ArtifactClaim("C1", "RAG retrieves documents.", StatementType.FACT,
                              "RAG", "architecture", ["S2"])]
    verify(a)
    assert a.claims[0].verification == Verification.PARTIALLY_VERIFIED


def test_no_source_is_unverified():
    a = _art()
    a.claims = [ArtifactClaim("C1", "RAG is always best.", StatementType.INFERENCE, "RAG")]
    verify(a)
    assert a.claims[0].verification == Verification.UNVERIFIED


def test_contradiction_is_flagged_not_hidden():
    a = _art()
    a.claims = [
        ArtifactClaim("C1", "RAG retrieval latency is higher than fine-tuning.",
                      StatementType.FACT, "RAG", "performance", ["S1"]),
        ArtifactClaim("C2", "RAG retrieval latency is lower than fine-tuning.",
                      StatementType.FACT, "RAG", "performance", ["S3"]),
    ]
    summary = verify(a)
    assert summary["conflicting"] == 2
    assert all(c.verification == Verification.CONFLICTING for c in a.claims)
    assert summary["contradictions"]


def test_corroboration_rescoring_of_sources():
    a = _art()
    a.claims = [ArtifactClaim("C1", "RAG retrieves documents.", StatementType.FACT,
                              "RAG", "architecture", ["S1", "S2"])]
    verify(a)
    # S1 & S2 corroborated the claim -> corroboration 1.0; S3 unused -> 0.9
    assert a.source_by_id("S1").corroboration == 1.0
    assert a.source_by_id("S3").corroboration == 0.9


def test_contradicts_helper():
    assert _contradicts("Latency is higher for RAG.", "Latency is lower for RAG.")
    assert _contradicts("RAG does not scale to large corpora.",
                        "RAG scales to large corpora effectively.")
    assert not _contradicts("RAG is fresh.", "Fine-tuning changes weights.")
