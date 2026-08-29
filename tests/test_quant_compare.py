"""Quantitative + comparison engines: compute from real numbers, evidence-linked."""
from app.analysis.artifact import AnalysisArtifact, ArtifactClaim, StatementType, Verification
from app.analysis.compare import build_comparisons
from app.analysis.quant import derived_comparisons, extract_metrics, growth_rate, ratio


def test_extract_metrics_with_units_and_source():
    m = extract_metrics("Retrieval latency 120 ms and index cost $300.", ["S1"], entity="RAG")
    assert any(x.unit == "ms" and x.value == 120.0 and "latency" in x.name for x in m)
    assert any(x.unit == "USD" and x.value == 300.0 and "cost" in x.name for x in m)
    assert all(x.source_ids == ["S1"] and x.derivation == "reported" for x in m)


def test_growth_and_ratio_record_formula():
    g = growth_rate(100, 121)
    assert g.value == 21.0 and g.unit == "%" and "computed:" in g.derivation
    assert growth_rate(0, 10) is None
    r = ratio(9, 3, "speedup")
    assert r.value == 3.0 and r.unit == "x" and "9/3" in r.derivation


def test_derived_cross_entity_percentage():
    metrics = [
        __import__("app.analysis.artifact", fromlist=["Metric"]).Metric(
            "throughput", 200, "tokens", "A", ["S1"], "reported"),
        __import__("app.analysis.artifact", fromlist=["Metric"]).Metric(
            "throughput", 100, "tokens", "B", ["S2"], "reported"),
    ]
    d = derived_comparisons(metrics)
    vals = {(x.entity, x.value) for x in d}
    assert ("A", 100.0) in vals and ("B", 0.0) in vals   # A is 100% above the lowest (B)
    assert all("computed:" in x.derivation for x in d)


def test_no_numbers_no_metrics():
    assert extract_metrics("RAG retrieves documents at query time.", ["S1"]) == []


def _art() -> AnalysisArtifact:
    a = AnalysisArtifact(objective="Compare RAG and Fine-tuning",
                         entities=["RAG", "Fine-tuning"], dimensions=["architecture"])
    a.add_source("https://arxiv.org/abs/1")
    a.claims = [
        ArtifactClaim("C1", "RAG retrieves external documents at query time.",
                      StatementType.FACT, "RAG", "architecture", ["S1"],
                      verification=Verification.VERIFIED, confidence="High"),
        ArtifactClaim("C2", "Fine-tuning bakes knowledge into weights.",
                      StatementType.FACT, "Fine-tuning", "architecture", ["S1"],
                      verification=Verification.PARTIALLY_VERIFIED, confidence="Medium"),
    ]
    return a


def test_comparison_matrix_is_evidence_linked_not_numeric():
    a = _art()
    comps = build_comparisons(a)
    assert len(comps) == 1 and comps[0].dimension == "architecture"
    cell = comps[0].entities["RAG"]
    assert cell["evidence_ids"] == ["C1"] and cell["confidence"] == "High"
    assert "retrieves external documents" in cell["assessment"]
    # no arbitrary numeric score is invented for the cell
    assert "score" not in cell


def test_comparison_omits_entities_without_evidence():
    a = _art()
    a.entities = ["RAG", "Fine-tuning", "Structured Memory"]   # no claims for the 3rd
    comps = build_comparisons(a)
    assert "Structured Memory" not in comps[0].entities
