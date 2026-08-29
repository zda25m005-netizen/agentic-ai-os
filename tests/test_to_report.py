"""Artifact -> Report IR: evidence-grounded findings, comparison, metrics."""
from app.analysis.artifact import Metric
from app.analysis.pipeline import build_analysis_artifact
from app.analysis.to_report import artifact_to_report
from app.exec.pdf import is_valid_pdf
from app.exec.report_pdf import render_report
from app.missions.models import Mission, Task
from app.missions.state import MissionStatus, TaskStatus


def _task(i, d, r):
    return Task(id=i, mission_id=1, description=d, status=TaskStatus.DONE,
                depends_on=[], result=r, created_at=0.0, updated_at=0.0)


def _artifact():
    m = Mission(id=1, objective="Compare RAG vs Fine-tuning", status=MissionStatus.COMPLETED,
                priority=0, deadline=None, created_at=0.0, updated_at=0.0, meta={})
    tasks = [
        _task(1, "RAG", "RAG retrieves documents at query time. It keeps knowledge fresh. "
              "Sources:\nhttps://arxiv.org/abs/2005.11401\nhttps://en.wikipedia.org/wiki/RAG"),
        _task(2, "Fine-tuning", "Fine-tuning bakes knowledge into weights. "
              "Sources:\nhttps://en.wikipedia.org/wiki/Fine-tuning_(deep_learning)"),
    ]
    return build_analysis_artifact(m, tasks)


def test_findings_carry_real_source_refs():
    r = artifact_to_report(_artifact())
    assert r.findings, "expected findings from the artifact"
    verified = [f for f in r.findings if f.confidence == "High"]
    assert verified and all(f.source_refs for f in verified)     # citations trace to sources
    # refs point at real source_records
    valid_refs = {s.ref for s in r.source_records}
    for f in r.findings:
        assert all(ref in valid_refs for ref in f.source_refs)


def test_comparison_and_quant_sections_present():
    art = _artifact()
    art.metrics.append(Metric("latency", 120, "ms", "RAG", ["S1"], "reported"))
    r = artifact_to_report(art)
    headings = {s.heading for s in r.sections}
    assert "Comparison Matrix" in headings
    assert "Quantitative Analysis" in headings
    quant = next(s for s in r.sections if s.heading == "Quantitative Analysis")
    assert quant.table and "Basis" in quant.table.columns


def test_report_from_artifact_renders_valid_pdf():
    r = artifact_to_report(_artifact())
    assert r.report_type in {"COMPARISON", "RESEARCH", "TECHNICAL_ANALYSIS"}
    assert is_valid_pdf(render_report(r))


def test_zero_source_artifact_maps_honestly():
    m = Mission(id=1, objective="Explain X", status=MissionStatus.COMPLETED, priority=0,
                deadline=None, created_at=0.0, updated_at=0.0, meta={})
    art = build_analysis_artifact(m, [_task(1, "t", "No links here.")])
    r = artifact_to_report(art)
    assert r.source_records == []
    assert any("No external references" in x for x in r.limitations)
