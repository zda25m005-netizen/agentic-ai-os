"""Rich analytical report: builder (deterministic + LLM synthesis) + renderer."""
import json

from app.exec.latex.render import render_tex
from app.exec.pdf import is_valid_pdf, page_count
from app.exec.report import (
    EvidenceCoverage,
    Finding,
    Metric,
    Report,
    ReportSection,
    Scorecard,
    Table,
)
from app.exec.report_builder import (
    _detect_type,
    _extract_sources,
    build_report,
    build_report_llm,
)
from app.exec.report_pdf import render_report
from app.missions.models import Mission, Task
from app.missions.state import MissionStatus, TaskStatus


def _task(i, desc, result, status=TaskStatus.DONE):
    return Task(id=i, mission_id=1, description=desc, status=status,
                depends_on=[], result=result, created_at=0.0, updated_at=0.0)


def _mission(obj, meta=None):
    return Mission(id=42, objective=obj, status=MissionStatus.COMPLETED, priority=0,
                   deadline=None, created_at=0.0, updated_at=0.0, meta=meta or {})


# --- builder ---

def test_report_type_detection():
    assert _detect_type("Compare NVIDIA vs AMD") == "COMPETITIVE_ANALYSIS"
    assert _detect_type("Find AI/ML jobs in Germany") == "JOB_MARKET_REPORT"
    assert _detect_type("Research transformer architectures") == "TECHNICAL_ANALYSIS"


def test_sources_extracted_not_invented():
    tasks = [_task(1, "a", "See https://nvidia.com/ai and https://amd.com."),
             _task(2, "b", "no links")]
    assert _extract_sources(tasks) == ["https://nvidia.com/ai", "https://amd.com."]
    assert _extract_sources([_task(3, "c", "plain text")]) == []


def test_findings_confidence_and_coverage():
    # Confidence is now *earned*: two sources incl. a High-credibility one -> High;
    # a single company source -> not High; no source -> Analytical.
    m = _mission("Compare A and B")
    tasks = [_task(1, "Research A", "A wins. https://arxiv.org/abs/1 and https://a.com"),
             _task(2, "Research B", "B is analytical only")]     # no source -> Analytical
    r = build_report(m, tasks)
    conf = {f.confidence for f in r.findings}
    assert "High" in conf and "Analytical" in conf
    assert r.coverage.sources_analyzed == 2
    assert r.coverage.claims_supported == 1 and r.coverage.assessments == 1
    assert 0 <= r.coverage.coverage_pct <= 100
    assert r.limitations  # always honest limitations


def test_source_register_and_traceability():
    m = _mission("Compare A and B")
    tasks = [_task(1, "Research A", "A. https://arxiv.org/abs/1 https://nvidia.com/x")]
    r = build_report(m, tasks)
    # bibliography built with metadata
    assert len(r.source_records) == 2
    reg = {s.url: s for s in r.source_records}
    assert reg["https://arxiv.org/abs/1"].stype == "Academic"
    assert reg["https://arxiv.org/abs/1"].credibility == "High"
    assert reg["https://arxiv.org/abs/1"].freshness in {
        "Recent", "Current", "Background", "Unknown"}
    # each finding traces back to its numbered sources
    assert r.findings[0].source_refs == [1, 2]
    # freshness distribution is present
    assert set(r.freshness) == {"Recent", "Current", "Background", "Unknown"}
    assert sum(r.freshness.values()) == 2
    # renders to a valid PDF
    pdf = render_report(r)
    assert is_valid_pdf(pdf) and page_count(pdf) >= 1


def test_zero_source_register_is_honest():
    r = build_report(_mission("Explain X"), [_task(1, "Analyze", "no links here")])
    assert r.source_records == []
    assert r.findings[0].source_refs == []
    assert is_valid_pdf(render_report(r))


def test_unsupported_figures_are_scrubbed():
    # fabricated percentages/currency with no source are REMOVED (not shown as fact)
    m = _mission("Compare A and B")
    tasks = [_task(1, "Accuracy", "A hits 95% accuracy, B hits 92%."),
             _task(2, "Cost", "B is cheapest at $300."),
             _task(3, "Scale", "A scales best across corpora.")]
    r = build_report(m, tasks)
    assert "95%" not in r.findings[0].body and "92%" not in r.findings[0].body
    assert "$300" not in r.findings[1].body
    assert "scales best" in r.findings[2].body            # untouched (no figures)
    assert r.integrity["unverified_figures"] == 0         # nothing left to flag
    assert any("quantitative figures" in x for x in r.limitations)  # caveat present
    assert is_valid_pdf(render_report(r))


def test_source_backed_figures_are_kept():
    m = _mission("Compare A and B")
    r = build_report(m, [_task(1, "Accuracy", "A hits 95%. https://arxiv.org/abs/1")])
    # figure is kept because the finding is source-backed (not scrubbed)
    assert "95%" in r.findings[0].body
    assert r.findings[0].unverified_figures is False


def test_all_evidence_metrics_are_consistent():
    # coverage, integrity, and overall confidence must agree (no contradictions)
    m = _mission("Compare RAG and Fine-tuning for LLM memory")
    tasks = [_task(1, "RAG", "RAG retrieval is fresh. https://en.wikipedia.org/wiki/RAG"),
             _task(2, "Fine-tuning", "Fine-tuning bakes knowledge into weights.")]
    r = build_report(m, tasks)
    ig, cov = r.integrity, r.coverage
    assert ig["sources_analyzed"] == cov.sources_analyzed
    assert ig["claims_supported"] == cov.claims_supported
    assert ig["coverage_pct"] == cov.coverage_pct
    assert ig["claims_supported"] + ig["unsupported"] == ig["claims_extracted"]
    # overall confidence can't be High unless something is actually source-backed
    if ig["claims_supported"] == 0:
        assert ig["overall_confidence"] == "Analytical"
    # per-finding confidence is never High without source refs
    for f in r.findings:
        if not f.source_refs:
            assert f.confidence == "Analytical"


async def test_llm_synthesis_merges_snapshot_and_scorecard():
    async def fake(_messages):
        return json.dumps({
            "snapshot": [{"label": "Market Leader", "value": "NVIDIA"}],
            "findings": [{"title": "Ecosystem moat", "body": "CUDA is broad.",
                          "confidence": "High"}],
            "scorecard": {"dimensions": ["Hardware", "Software"],
                          "entities": ["NVIDIA", "AMD"],
                          "scores": {"NVIDIA": [5, 5], "AMD": [4, 3]}},
            "limitations": ["No quantitative market figures were available."],
        })
    m = _mission("Compare NVIDIA and AMD")
    r = await build_report_llm(m, [_task(1, "Research", "stuff https://x.com")], fake)
    assert r.snapshot[0].value == "NVIDIA"
    assert r.scorecard and r.scorecard.scores["NVIDIA"] == [5, 5]
    # The LLM asserted "High", but confidence is now EARNED from the evidence graph:
    # this finding isn't linked to a source, so it is downgraded to Analytical and
    # every metric stays consistent (no "confident but unsupported" contradiction).
    assert r.findings[0].confidence == "Analytical"
    assert r.integrity["claims_supported"] == 0
    assert r.integrity["overall_confidence"] == "Analytical"
    assert r.coverage.claims_supported == r.integrity["claims_supported"]


async def test_llm_recommendation_and_rationale():
    async def fake(_messages):
        return json.dumps({
            "recommendation": "Adopt a hybrid: Router -> Structured store + Vector "
                              "retrieval -> Composer -> LLM.",
            "decision_rationale": [
                {"requirement": "Stable prefs", "decision": "Structured store",
                 "reason": "Deterministic retrieval"},
                {"requirement": "Semantic memory", "decision": "Vector DB",
                 "reason": "Similarity retrieval"},
            ],
        })
    r = await build_report_llm(_mission("Design LLM memory"), [_task(1, "t", "r")], fake)
    assert "hybrid" in r.recommendation
    assert len(r.decision_rationale) == 2
    assert r.decision_rationale[0]["decision"] == "Structured store"
    pdf = render_report(r)
    assert is_valid_pdf(pdf)


async def test_llm_structured_report_sections():
    async def fake(_messages):
        return json.dumps({
            "problem_definition": "Long-term memory lets agents recall context.",
            "approaches": [
                {"name": "Vector Retrieval (RAG)", "how_it_works": "Embed and retrieve.",
                 "advantages": ["Fresh"], "disadvantages": ["Chunking"],
                 "failure_modes": ["Stale index"], "mitigations": ["Reranker"]},
                {"name": "Fine-Tuning", "how_it_works": "Bake into weights.",
                 "advantages": ["Behaviour change"], "disadvantages": ["Costly"]},
            ],
            "comparative_analysis": "RAG leads on freshness; fine-tuning on behaviour.",
            "failure_analysis": [
                {"failure": "Stale retrieval", "impact": "Outdated answers",
                 "mitigation": "Re-index"}],
        })
    m = _mission("Evaluate RAG vs Fine-Tuning for LLM memory")
    r = await build_report_llm(m, [_task(1, "t", "r")], fake)
    assert r.problem_definition
    assert len(r.approaches) == 2
    assert r.approaches[0]["name"] == "Vector Retrieval (RAG)"
    assert r.approaches[0]["advantages"] == ["Fresh"]
    assert r.comparative_analysis and len(r.failure_analysis) == 1
    # structured approaches replace the generic task-result sections in the render
    tex = render_tex(r)
    assert r"\section{Vector Retrieval (RAG)}" in tex
    assert "How it works" in tex and "Failure Mode Analysis" in tex
    assert is_valid_pdf(render_report(r))


def test_summary_grammar_no_double_verb():
    from app.exec.report_builder import _default_summary
    s = _default_summary("Evaluate three approaches to LLM memory", 3)
    assert s.startswith("This report evaluates three approaches")
    assert "analyzes evaluate" not in s
    s2 = _default_summary("Compare NVIDIA and AMD", 2)
    assert s2.startswith("This report compares NVIDIA and AMD")


async def test_llm_framework_and_risk_matrix():
    async def fake(_messages):
        return json.dumps({
            "evaluation_framework": [
                {"criterion": "Accuracy", "definition": "Correctness of recall"},
                {"criterion": "Freshness", "definition": "How current the info is"}],
            "failure_analysis": [
                {"failure": "Retrieval miss", "probability": "Medium", "impact": "High",
                 "mitigation": "Hybrid retrieval"}],
        })
    r = await build_report_llm(_mission("Evaluate RAG vs Fine-tuning"),
                               [_task(1, "t", "r")], fake)
    assert len(r.evaluation_framework) == 2
    assert r.evaluation_framework[0]["criterion"] == "Accuracy"
    assert r.failure_analysis[0]["probability"] == "Medium"
    tex = render_tex(r)
    assert "Evaluation Framework" in tex and "Probability" in tex


async def test_llm_bad_response_falls_back():
    async def bad(_messages):
        return "not json"
    r = await build_report_llm(_mission("x"), [_task(1, "t", "r")], bad)
    assert isinstance(r, Report) and r.findings  # deterministic base preserved


# --- renderer ---

def test_render_full_report_valid_pdf():
    r = Report(
        title="AI Compute Landscape", subtitle="NVIDIA vs AMD vs Intel",
        meta={"mission_id": 42, "date": "28 August 2026", "sources": 3},
        snapshot=[Metric("Market Leader", "NVIDIA"), Metric("Challenger", "AMD"),
                  Metric("Risk", "Ecosystem lock-in")],
        executive_summary="NVIDIA leads. " * 20,
        findings=[Finding("Ecosystem moat", "CUDA is broad. " * 8, "High", ["https://x.com"]),
                  Finding("Challenger", "AMD closing gap. " * 8, "Medium")],
        scorecard=Scorecard(["Hardware", "Software", "Ecosystem"], ["NVIDIA", "AMD", "Intel"],
                            {"NVIDIA": [5, 5, 5], "AMD": [4, 3, 3], "Intel": [3, 3, 2]}),
        coverage=EvidenceCoverage(24, 41, 9),
        sections=[ReportSection("NVIDIA", ["Strong. " * 30]),
                  ReportSection("Comparison", [], Table(["D", "N", "A"], [["x", "y", "z"]], "T1"))],
        methodology="Synthesized from mission results.",
        limitations=["Scores are qualitative analyst assessments."],
        sources=["https://a.com", "https://b.com"],
    )
    pdf = render_report(r)
    assert is_valid_pdf(pdf)
    assert page_count(pdf) >= 2
    assert b"Helvetica-Bold" in pdf and b"Page 2 of" in pdf


def test_render_end_to_end_from_mission():
    m = _mission("Compare NVIDIA and AMD", meta={"usage": {"tokens": 100, "usd": 0.01}})
    pdf = render_report(build_report(m, [_task(1, "Research", "NVIDIA leads. " * 40)]))
    assert is_valid_pdf(pdf) and page_count(pdf) >= 2
