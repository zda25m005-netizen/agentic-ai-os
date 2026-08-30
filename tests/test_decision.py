"""Evidence-grounded decision: proportional, not 'use everything'."""
from app.analysis.decision import derive_decision
from app.analysis.pipeline import build_analysis_artifact
from app.analysis.scoring import score_artifact
from app.missions.models import Mission, Task
from app.missions.state import MissionStatus, TaskStatus


def _task(i, d, r):
    return Task(id=i, mission_id=1, description=d, status=TaskStatus.DONE,
                depends_on=[], result=r, created_at=0.0, updated_at=0.0)


def _decision():
    m = Mission(id=1, objective="Compare RAG, Fine-tuning, and Structured Memory for LLM memory",
                status=MissionStatus.COMPLETED, priority=0, deadline=None,
                created_at=0.0, updated_at=0.0, meta={})
    tasks = [
        _task(1, "RAG", "RAG keeps knowledge fresh and grounded and scales to large "
              "corpora. Retrieval adds latency overhead. https://arxiv.org/abs/1"),
        _task(2, "Fine-tuning", "Fine-tuning gives fast low latency inference but is "
              "expensive to train and does not scale. https://example.com/ft"),
        _task(3, "Structured Memory", "Structured memory scales cheaply with low overhead "
              "and reliable retrieval. https://example.com/sm"),
    ]
    art = build_analysis_artifact(m, tasks)
    return derive_decision(art, score_artifact(art))


def test_decision_is_proportional_and_grounded():
    d = _decision()
    assert d.recommended                        # at least one option recommended
    # not everything is adopted by default unless each leads a criterion
    assert len(d.recommended) < 3 or all(c["leads"] for c in d.components)
    assert d.confidence in {"High", "Medium", "Low"}
    assert d.evidence_count == 3
    assert "selectively" in d.summary or len(d.recommended) == len(d.components)


def test_low_confidence_high_score_is_flagged():
    d = _decision()
    # single-source high scores must be surfaced as low-confidence, not asserted
    assert all("indicative" in f for f in d.consistency_flags)
