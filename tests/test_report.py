"""Report builder (mission -> structured report) + professional PDF renderer."""
from app.exec.pdf import is_valid_pdf, page_count
from app.exec.report import Finding, Report, ReportSection, Table
from app.exec.report_builder import _detect_type, _extract_sources, build_report
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
    assert _detect_type("Summarize the news") == "RESEARCH_REPORT"


def test_sources_extracted_not_invented():
    tasks = [_task(1, "a", "See https://nvidia.com/ai and https://amd.com."),
             _task(2, "b", "no links here")]
    assert _extract_sources(tasks) == ["https://nvidia.com/ai", "https://amd.com."]
    # a mission with no links -> no sources (honest)
    assert _extract_sources([_task(3, "c", "plain text")]) == []


def test_build_report_from_real_tasks():
    m = _mission("Compare NVIDIA, AMD and Intel AI strategy",
                 meta={"usage": {"tokens": 2740, "usd": 0.0061}})
    tasks = [_task(1, "Research NVIDIA strategy", "NVIDIA leads via CUDA. https://nvidia.com"),
             _task(2, "Research AMD strategy", "AMD competes on price with MI300."),
             _task(3, "Compare", "", status=TaskStatus.PENDING)]
    r = build_report(m, tasks)
    assert r.report_type == "COMPETITIVE_ANALYSIS"
    assert r.meta["mission_id"] == 42 and r.meta["sources"] == 1
    assert len(r.findings) == 2          # only DONE tasks with results
    assert any(s.table for s in r.sections)  # scope table present
    assert "2740 tokens" in r.methodology


def test_build_report_handles_empty_mission():
    r = build_report(_mission("Do something"), [])
    assert r.sections and r.sources == []  # honest fallback, no fake sources


# --- renderer ---

def test_render_report_valid_pdf():
    r = Report(
        title="AI Compute Landscape", subtitle="NVIDIA vs AMD vs Intel",
        meta={"mission_id": 42, "date": "28 August 2026", "sources": 3},
        executive_summary="NVIDIA maintains the strongest position. " * 20,
        findings=[Finding("Ecosystem depth", "CUDA adoption is broad. " * 10)],
        sections=[
            ReportSection("NVIDIA", ["Strong ecosystem. " * 30]),
            ReportSection("Comparison", [], table=Table(
                ["Dimension", "NVIDIA", "AMD"], [["Ecosystem", "Deep", "Growing"]],
                "Table 1 — comparison.")),
        ],
        methodology="Synthesized from mission results.",
        sources=["https://example.com/a", "https://example.com/b"],
    )
    pdf = render_report(r)
    assert is_valid_pdf(pdf)
    assert page_count(pdf) >= 2          # cover + content
    assert b"Helvetica-Bold" in pdf      # professional headings
    assert b"Page 2 of" in pdf           # footer page numbers


def test_render_end_to_end_from_mission():
    m = _mission("Compare NVIDIA and AMD", meta={"usage": {"tokens": 100, "usd": 0.01}})
    tasks = [_task(1, "Research", "NVIDIA leads. " * 40 + "https://nvidia.com")]
    pdf = render_report(build_report(m, tasks))
    assert is_valid_pdf(pdf) and page_count(pdf) >= 2
