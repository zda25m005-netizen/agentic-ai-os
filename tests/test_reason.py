"""Finding generation: grounded observations from verified claims."""
from app.analysis.artifact import AnalysisArtifact, ArtifactClaim, StatementType, Verification
from app.analysis.reason import generate_findings


def _art() -> AnalysisArtifact:
    a = AnalysisArtifact(objective="Compare RAG and Fine-tuning", entities=["RAG", "Fine-tuning"])
    a.add_source("https://arxiv.org/abs/2005.11401")
    a.add_source("https://en.wikipedia.org/wiki/Retrieval-augmented_generation")
    a.claims = [
        ArtifactClaim("C1", "RAG retrieves documents at query time.", StatementType.FACT,
                      "RAG", "architecture", ["S1", "S2"],
                      verification=Verification.VERIFIED, confidence="High"),
        ArtifactClaim("C2", "RAG keeps knowledge fresh without retraining.",
                      StatementType.OBSERVATION, "RAG", "architecture", ["S2"],
                      verification=Verification.PARTIALLY_VERIFIED, confidence="Medium"),
        ArtifactClaim("C3", "Fine-tuning changes model weights.", StatementType.FACT,
                      "Fine-tuning", "architecture", ["S1"],
                      verification=Verification.PARTIALLY_VERIFIED, confidence="Medium"),
        ArtifactClaim("C4", "RAG is always superior.", StatementType.INFERENCE, "RAG",
                      verification=Verification.UNVERIFIED, confidence="Low"),
        ArtifactClaim("C5", "This claim has no source.", StatementType.OBSERVATION, "RAG",
                      "misc", [], verification=Verification.UNVERIFIED),
    ]
    return a


def test_findings_only_from_evidence_backed_factual_claims():
    findings = generate_findings(_art())
    # C4 (inference) and C5 (no source) must not seed findings
    ev = {e for f in findings for e in f.evidence_ids}
    assert "C4" not in ev and "C5" not in ev
    assert "C1" in ev and "C3" in ev


def test_verified_topic_ranks_first_and_is_high_confidence():
    findings = generate_findings(_art())
    assert findings[0].confidence == "High"           # RAG/architecture has a VERIFIED claim
    assert "RAG retrieves documents" in findings[0].observation
    assert findings[0].evidence_ids                    # grounded in real claims


def test_interpretation_left_for_llm():
    findings = generate_findings(_art())
    # the deterministic step never invents interpretation/implication
    assert all(f.interpretation == "" and f.implication == "" for f in findings)


def test_findings_attached_to_artifact_and_bounded():
    a = _art()
    findings = generate_findings(a, max_findings=1)
    assert a.findings is findings and len(findings) == 1
