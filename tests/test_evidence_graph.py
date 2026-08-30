"""Research Evidence Graph: question -> claims -> sources -> findings -> scores."""
from app.analysis.evidence_graph import build_graph, render_ascii
from app.analysis.pipeline import build_analysis_artifact
from app.analysis.scoring import score_artifact
from app.missions.models import Mission, Task
from app.missions.state import MissionStatus, TaskStatus


def _art():
    m = Mission(id=1, objective="Compare RAG and Fine-tuning for LLM memory",
                status=MissionStatus.COMPLETED, priority=0, deadline=None,
                created_at=0.0, updated_at=0.0, meta={})
    tasks = [Task(id=1, mission_id=1, description="RAG",
                  status=TaskStatus.DONE, depends_on=[],
                  result="RAG grounds generation and scales. https://arxiv.org/abs/1",
                  created_at=0.0, updated_at=0.0)]
    return build_analysis_artifact(m, tasks)


def test_graph_counts_and_edges():
    art = _art()
    g = build_graph(art, score_artifact(art))
    assert g.counts["claims"] == len(art.claims)
    assert g.counts["sources"] == len(art.sources)
    # every claim->source link is an edge
    assert g.edge_count() >= sum(len(c.source_ids) for c in art.claims)


def test_ascii_diagram_has_pipeline_stages():
    art = _art()
    txt = render_ascii(build_graph(art, score_artifact(art)),
                       decision_summary="Adopt RAG", confidence="Low", dropped=2)
    for stage in ("RESEARCH QUESTION", "CLAIMS EXTRACTED", "SOURCES", "FINDINGS",
                  "EVIDENCE-WEIGHTED SCORES", "DECISION"):
        assert stage in txt
    assert "off-topic dropped" in txt and "confidence: Low" in txt
