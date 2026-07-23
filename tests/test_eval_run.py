import pytest

from app.rag import embeddings, vectorstore
from eval import run
from eval.dataset import CorpusDoc, QAItem


@pytest.fixture
def client():
    return vectorstore.get_client(location=":memory:")


@pytest.fixture(autouse=True)
def fake_embeddings(monkeypatch):
    # Constant vector => every doc is retrievable (top_k covers the corpus).
    async def fake_embed(texts):
        return [[1.0, 0.0, 0.0] for _ in texts]

    monkeypatch.setattr(embeddings, "embed", fake_embed)


CORPUS = [
    CorpusDoc(source="a.pdf", text="Revenue grew 12% in the third quarter."),
    CorpusDoc(source="b.pdf", text="The primary language is Python."),
]
QA = [
    QAItem("q1", "How much did revenue grow?", "12%", "a.pdf"),
    QAItem("q2", "What is the primary language?", "Python", "b.pdf"),
]


async def test_build_indexes_populates_both_stores(client):
    bm25 = await run.build_indexes(CORPUS, client, collection="eval_documents")
    assert len(bm25) >= 2
    assert client.collection_exists("eval_documents")


async def test_run_eval_scores_a_perfect_run(client):
    bm25 = await run.build_indexes(CORPUS, client, collection="eval_documents")

    async def answer_fn(messages):
        # Answer contains both gold answers and cites block [1].
        return "Revenue grew 12% and the language is Python [1]."

    report = await run.run_eval(QA, client, bm25, answer_fn=answer_fn)
    assert report.n == 2
    assert report.recall_at_k == 1.0
    assert report.answer_match == 1.0
    assert report.citation_accuracy == 1.0
    assert report.llm_judge is None  # no judge supplied


async def test_run_eval_with_judge(client):
    bm25 = await run.build_indexes(CORPUS, client, collection="eval_documents")

    async def answer_fn(messages):
        return "12% and Python [1]."

    async def judge_fn(messages):
        return "YES"

    report = await run.run_eval(QA, client, bm25, answer_fn=answer_fn, judge_fn=judge_fn)
    assert report.llm_judge == 1.0


def test_format_report_md_contains_metrics():
    report = run.EvalReport(
        n=15, recall_at_k=0.87, answer_match=0.80, citation_accuracy=0.93, llm_judge=0.85
    )
    md = run.format_report_md(report)
    assert "Retrieval recall@5" in md
    assert "87%" in md
    assert "LLM-judge" in md
