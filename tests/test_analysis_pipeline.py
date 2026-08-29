"""Evidence-first assembly: mission -> complete Analysis Artifact."""
from app.analysis.artifact import Verification
from app.analysis.pipeline import build_analysis_artifact, parse_objective
from app.missions.models import Mission, Task
from app.missions.state import MissionStatus, TaskStatus


def _task(i, desc, result):
    return Task(id=i, mission_id=1, description=desc, status=TaskStatus.DONE,
                depends_on=[], result=result, created_at=0.0, updated_at=0.0)


def _mission(obj):
    return Mission(id=1, objective=obj, status=MissionStatus.COMPLETED, priority=0,
                   deadline=None, created_at=0.0, updated_at=0.0, meta={})


def test_parse_objective_entities_and_type():
    ents, _dims, mtype = parse_objective(
        "Evaluate approaches to LLM memory: Vector Retrieval, Fine-Tuning, Structured Memory")
    assert ents == ["Vector Retrieval", "Fine-Tuning", "Structured Memory"]
    assert mtype == "TECHNICAL_ANALYSIS"
    ents2, _d, mt2 = parse_objective("Compare NVIDIA vs AMD")
    assert "NVIDIA" in ents2 and "AMD" in ents2 and mt2 == "COMPARISON"


def test_pipeline_assembles_full_artifact():
    m = _mission("Compare RAG and Fine-tuning for LLM memory")
    tasks = [
        _task(1, "RAG",
              "Vector retrieval fetches documents at query time. It keeps knowledge fresh. "
              "Sources:\nhttps://arxiv.org/abs/2005.11401\nhttps://en.wikipedia.org/wiki/RAG"),
        _task(2, "Fine-tuning",
              "Fine-tuning bakes knowledge into model weights. It is costly to update. "
              "Sources:\nhttps://en.wikipedia.org/wiki/Fine-tuning_(deep_learning)"),
    ]
    art = build_analysis_artifact(m, tasks)
    assert len(art.sources) == 3                       # deduped across tasks
    assert art.claims and all(c.id.startswith("C") for c in art.claims)
    # verification ran: claims backed by 2 independent publishers are VERIFIED
    assert any(c.verification == Verification.VERIFIED for c in art.claims)
    assert art.findings and art.findings[0].evidence_ids
    # no fabricated numbers -> uncertainty is stated honestly
    assert any("Quantitative" in u for u in art.uncertainties)
    # raw task text never leaks: the LLM view is structured
    ctx = art.to_llm_context()
    assert set(ctx) >= {"sources", "claims", "findings", "limitations"}


def test_zero_source_pipeline_is_honest():
    art = build_analysis_artifact(_mission("Explain X"), [_task(1, "t", "No links here at all.")])
    assert art.sources == []
    assert any("No external references" in x for x in art.limitations)
    assert all(c.verification == Verification.UNVERIFIED for c in art.claims)
