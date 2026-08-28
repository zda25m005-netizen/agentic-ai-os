"""Analysis Artifact schema: sources, claims, findings, quality (evidence-first)."""
from app.analysis import (
    AnalysisArtifact,
    ArtifactClaim,
    ArtifactFinding,
    StatementType,
    Verification,
)
from app.analysis.artifact import Metric, confidence_from_evidence


def _artifact() -> AnalysisArtifact:
    a = AnalysisArtifact(objective="Evaluate RAG vs Fine-tuning", entities=["RAG", "Fine-tuning"])
    s1 = a.add_source("https://arxiv.org/abs/2005.11401", "RAG paper")
    s2 = a.add_source("https://en.wikipedia.org/wiki/Retrieval-augmented_generation")
    assert a.add_source("https://arxiv.org/abs/2005.11401") == s1  # dedup
    a.claims = [
        ArtifactClaim("C1", "RAG retrieves external documents at query time.",
                      StatementType.FACT, "RAG", "architecture", [s1, s2],
                      verification=Verification.VERIFIED, confidence="High"),
        ArtifactClaim("C2", "RAG may increase inference latency.",
                      StatementType.INFERENCE, "RAG", "performance", [s2],
                      verification=Verification.PARTIALLY_VERIFIED, confidence="Medium"),
        ArtifactClaim("C3", "RAG is always better.", StatementType.INFERENCE, "RAG",
                      verification=Verification.UNVERIFIED, confidence="Low"),
    ]
    a.metrics = [Metric("latency", 120, "ms", "RAG", [s1], "reported")]
    a.findings = [ArtifactFinding("F1", "RAG grounds answers in fetched documents.",
                                  "This reduces hallucination on fresh facts.",
                                  "Prefer RAG where freshness matters.", ["C1"], "High")]
    return a


def test_source_typing_and_reliability():
    a = _artifact()
    s = a.source_by_id("S1")
    assert s.source_type == "academic" and s.reliability >= 0.9
    assert "heuristic" in s.reliability_basis           # never fake precision
    assert a.source_by_id("S2").source_type in {"company", "news", "other"}


def test_statement_types_kept_distinct():
    a = _artifact()
    kinds = {c.statement_type for c in a.claims}
    assert StatementType.FACT in kinds and StatementType.INFERENCE in kinds


def test_quality_metrics_are_bounded_and_honest():
    q = _artifact().quality()
    for v in q.values():
        if isinstance(v, float):
            assert 0.0 <= v <= 1.0
    assert q["evidence_coverage"] == round(2 / 3, 2)     # 2 of 3 claims sourced
    assert q["claim_verification"] == round(1 / 3, 2)    # 1 of 3 verified
    assert q["reasoning_depth"] == 1.0                   # the finding has interp+implication
    assert "not calibrated" in q["note"]


def test_to_llm_context_exposes_structure_not_free_text():
    ctx = _artifact().to_llm_context()
    assert {s["id"] for s in ctx["sources"]} == {"S1", "S2"}
    assert ctx["claims"][0]["verification"] == "Verified"
    assert ctx["findings"][0]["implication"]              # reasoning chain present


def test_confidence_from_evidence():
    assert confidence_from_evidence([0.95, 0.8], 2) == "High"
    assert confidence_from_evidence([0.95], 1) == "Medium"
    assert confidence_from_evidence([0.5], 1) == "Low"
    assert confidence_from_evidence([], 0) == "Low"
