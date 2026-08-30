"""Evidence-weighted scoring: scores must trace to supporting/contradicting claims."""
from app.analysis.pipeline import build_analysis_artifact
from app.analysis.scoring import _polarity, score_artifact
from app.missions.models import Mission, Task
from app.missions.state import MissionStatus, TaskStatus


def test_polarity_handles_local_negation():
    assert _polarity("fast low latency inference and strong accuracy") == 1
    assert _polarity("expensive to train and does not scale") == -1
    assert _polarity("retrieval adds latency and compute overhead") == -1
    assert _polarity("stores persistent facts") == 0   # no polarity cue


def _task(i, d, r):
    return Task(id=i, mission_id=1, description=d, status=TaskStatus.DONE,
                depends_on=[], result=r, created_at=0.0, updated_at=0.0)


def _artifact():
    m = Mission(id=1, objective="Compare RAG, Fine-tuning, and Structured Memory for LLM memory",
                status=MissionStatus.COMPLETED, priority=0, deadline=None,
                created_at=0.0, updated_at=0.0, meta={})
    tasks = [
        _task(1, "RAG", "RAG keeps knowledge fresh and grounded improving relevance. "
              "But retrieval adds latency and compute overhead. https://arxiv.org/abs/1"),
        _task(2, "Fine-tuning", "Fine-tuning gives fast low latency inference but is "
              "expensive to train and does not scale. https://example.com/ft"),
    ]
    return build_analysis_artifact(m, tasks)


def test_scores_are_evidence_derived_with_counts():
    sc = score_artifact(_artifact())
    assert sc.entities and sc.criteria
    cell = sc.cell("RAG", "Efficiency")
    assert cell is not None
    # RAG's efficiency claim is negative (latency/overhead) -> contradicting, low score
    assert cell.contradicting >= 1
    assert cell.score < 2.5
    assert cell.confidence in {"High", "Medium", "Low"}


def test_score_bounded_and_neutral_without_evidence():
    sc = score_artifact(_artifact())
    for c in sc.cells:
        assert 0.0 <= c.score <= 5.0
        if c.supporting == 0 and c.contradicting == 0:
            assert c.score == 2.5 and c.confidence == "Low"
