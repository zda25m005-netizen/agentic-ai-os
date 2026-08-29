"""Phases 13-15: metrics, benchmark dataset, evidence-first ablation."""
from app.analysis.ablation import _baseline, _evidence_first, format_ablation, run_ablation
from app.analysis.benchmark import load_dataset
from app.analysis.metrics import score_artifact
from app.analysis.pipeline import build_analysis_artifact

# --- Phase 13: metrics ---

def test_score_artifact_rewards_grounding():
    item = next(i for i in load_dataset() if i.id == "comparison-1")
    art = build_analysis_artifact(item.mission(), item.tasks())
    m = score_artifact(art)
    assert 0.0 <= m["claim_grounding"] <= 1.0
    assert m["claim_grounding"] > 0.5          # comparison-1 sources are linked
    assert m["citation_coverage"] > 0.0
    assert m["n_sources"] >= 2


# --- Phase 14: benchmark dataset ---

def test_benchmark_dataset_is_wellformed():
    ds = load_dataset()
    assert len(ds) >= 4
    cats = {i.category for i in ds}
    assert {"research", "comparison", "technical", "numerical"} <= cats
    for it in ds:
        assert it.objective and it.results
        assert it.mission().objective == it.objective
        assert len(it.tasks()) == len(it.results)
        assert any("http" in r for _d, r in it.results)   # every item carries sources


# --- Phase 15: ablation ---

def test_evidence_first_beats_baseline():
    res = run_ablation()
    s, b, d = res["system"], res["baseline"], res["delta"]
    # the evidence layer strictly improves grounding, citation and verification
    assert d["citation_coverage"] > 0 and s["citation_coverage"] > b["citation_coverage"]
    assert d["claim_grounding"] > 0
    assert d["verified_rate"] > 0
    # and reduces unsupported figures (baseline states numbers with no source)
    assert s["unsupported_figure_rate"] <= b["unsupported_figure_rate"]
    assert res["n_items"] == len(load_dataset())


def test_baseline_has_no_citations():
    item = next(i for i in load_dataset() if i.id == "numerical-1")
    b = _baseline(item)
    s = _evidence_first(item)
    assert b["citation_coverage"] == 0.0 and b["verified_rate"] == 0.0
    assert s["citation_coverage"] > 0.0        # evidence-first links the numbers to sources


def test_format_ablation_table():
    txt = format_ablation(run_ablation())
    assert "Baseline" in txt and "Evidence-first" in txt and "Delta" in txt
    assert "citation coverage" in txt
