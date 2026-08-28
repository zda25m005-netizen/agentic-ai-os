"""Rich analytical report: builder (deterministic + LLM synthesis) + renderer."""
import json

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
    assert r.trail.sources_used == 2 and r.trail.areas
    assert r.limitations  # always honest limitations


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
    assert r.findings[0].confidence == "High"


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
