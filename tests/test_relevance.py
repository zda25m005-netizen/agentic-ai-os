"""Source relevance gate: off-topic sources must never enter evidence/references."""
from app.analysis.pipeline import build_analysis_artifact
from app.analysis.relevance import RELEVANCE_MIN, build_question, is_assessable, score
from app.missions.models import Mission, Task
from app.missions.state import MissionStatus, TaskStatus

_OBJ = "Evaluate and compare RAG, fine-tuning, and structured memory for LLM long-term memory"
_ENTS = ["RAG", "fine-tuning", "structured memory"]


def _q():
    return build_question(_OBJ, _ENTS)


def test_offtopic_titles_score_zero():
    q = _q()
    for junk in ("Japanese conjugation", "The Rite of Spring", "The Guardian",
                 "Glossary of artificial intelligence"):
        rel, _ = score(junk, "", q)
        assert rel < RELEVANCE_MIN, f"{junk!r} should be below the gate"


def test_ontopic_sources_pass():
    q = _q()
    rel, _ = score("Retrieval-augmented generation",
                   "RAG combines a retriever with a language model to ground "
                   "generation of text in external documents for LLM memory.", q)
    assert rel >= RELEVANCE_MIN
    # entity name alone is a strong signal
    rel2, basis = score("Fine-tuning (deep learning)", "", q)
    assert rel2 >= RELEVANCE_MIN and "entity" in basis


def test_is_assessable_needs_real_text():
    # bare domain as title -> not assessable (never dropped for missing metadata)
    assert is_assessable("en.wikipedia.org", "", "en.wikipedia.org") is False
    assert is_assessable("Japanese conjugation", "", "en.wikipedia.org") is True
    assert is_assessable("", "some snippet text", "arxiv.org") is True


def _task(i, desc, result):
    return Task(id=i, mission_id=1, description=desc, status=TaskStatus.DONE,
                depends_on=[], result=result, created_at=0.0, updated_at=0.0)


def _mission(obj, sources):
    return Mission(id=1, objective=obj, status=MissionStatus.COMPLETED, priority=0,
                   deadline=None, created_at=0.0, updated_at=0.0,
                   meta={"sources": sources})


def test_gate_drops_offtopic_source_from_artifact():
    # Two URLs cited; metadata marks one as an unrelated page.
    m = _mission(_OBJ, [
        {"url": "https://en.wikipedia.org/wiki/RAG",
         "title": "Retrieval-augmented generation",
         "snippet": "RAG retrieves external documents to ground an LLM's generation "
                    "and supports long-term memory via a retriever."},
        {"url": "https://en.wikipedia.org/wiki/The_Rite_of_Spring",
         "title": "The Rite of Spring",
         "snippet": "A ballet and orchestral concert work by Igor Stravinsky."},
    ])
    tasks = [_task(1, "Research RAG",
                   "RAG grounds generation. https://en.wikipedia.org/wiki/RAG "
                   "https://en.wikipedia.org/wiki/The_Rite_of_Spring")]
    art = build_analysis_artifact(m, tasks)
    urls = {s.url for s in art.sources}
    assert "https://en.wikipedia.org/wiki/RAG" in urls
    assert "https://en.wikipedia.org/wiki/The_Rite_of_Spring" not in urls
    # the dropped source's id must not dangle on any claim
    live_ids = {s.id for s in art.sources}
    for c in art.claims:
        assert set(c.source_ids) <= live_ids
    assert any("off-topic" in x for x in art.limitations)


def test_gate_keeps_bare_urls_without_metadata():
    # No metadata at all -> not assessable -> kept (we never drop a link we can't read).
    m = _mission("Compare RAG and Fine-tuning", [])
    tasks = [_task(1, "Research",
                   "RAG is useful. https://arxiv.org/abs/2005.11401 https://example.com/x")]
    art = build_analysis_artifact(m, tasks)
    assert len(art.sources) == 2
