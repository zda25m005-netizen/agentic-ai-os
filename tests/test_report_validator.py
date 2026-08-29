"""Report validator: blocks unsupported reports; repair fixes what it can."""
from app.analysis.artifact import AnalysisArtifact, ArtifactFinding, Metric
from app.analysis.pipeline import build_analysis_artifact
from app.analysis.to_report import artifact_to_report
from app.analysis.validate import repair_report, validate_report
from app.exec.report import Finding, Report, ReportSection, SourceRecord
from app.missions.models import Mission, Task
from app.missions.state import MissionStatus, TaskStatus


def _task(i, d, r):
    return Task(id=i, mission_id=1, description=d, status=TaskStatus.DONE,
                depends_on=[], result=r, created_at=0.0, updated_at=0.0)


def _good_report() -> Report:
    m = Mission(id=1, objective="Compare RAG vs Fine-tuning", status=MissionStatus.COMPLETED,
                priority=0, deadline=None, created_at=0.0, updated_at=0.0, meta={})
    art = build_analysis_artifact(m, [
        _task(1, "RAG", "RAG retrieves external documents at query time. "
              "Sources:\nhttps://arxiv.org/abs/1\nhttps://en.wikipedia.org/wiki/RAG")])
    return artifact_to_report(art)


def test_good_report_passes():
    assert validate_report(_good_report()).ok


def test_unsupported_figure_is_blocked_then_repaired():
    r = Report(title="x", findings=[Finding("F", "Accuracy is 95%.", "Analytical")],
               limitations=["l"])
    res = validate_report(r)
    assert not res.ok and any("unsupported figure" in e for e in res.errors)
    repair_report(r)
    assert "95%" not in r.findings[0].body
    assert validate_report(r).ok


def test_empty_and_duplicate_sections_blocked_and_repaired():
    r = Report(title="x", findings=[Finding("F", "Body.", "Medium")], limitations=["l"],
               sections=[ReportSection("A", []),           # empty
                         ReportSection("B", ["text"]),
                         ReportSection("B", ["dup"])])      # duplicate heading
    res = validate_report(r)
    assert any("empty section" in e for e in res.errors)
    assert any("duplicate" in e for e in res.errors)
    repair_report(r)
    assert [s.heading for s in r.sections] == ["B"]
    assert validate_report(r).ok


def test_missing_limitations_and_malformed_url_blocked():
    r = Report(title="x", findings=[Finding("F", "Body.", "Medium")],
               source_records=[SourceRecord(1, "notaurl")])
    res = validate_report(r)
    assert any("Limitations" in e for e in res.errors)
    assert any("malformed source url" in e for e in res.errors)


def test_artifact_number_without_source_blocked():
    art = AnalysisArtifact(objective="x")
    art.metrics = [Metric("latency", 120, "ms", "A", [], "reported")]   # no source_ids
    art.findings = [ArtifactFinding("F1", "obs", evidence_ids=["C1"], confidence="High")]
    r = Report(title="x", findings=[Finding("F", "Body.", "Medium")], limitations=["l"])
    res = validate_report(r, artifact=art)
    assert any("number without a source" in e for e in res.errors)


def test_no_findings_blocked():
    assert not validate_report(Report(title="x", limitations=["l"])).ok
