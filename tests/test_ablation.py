import pytest

from app.rag import embeddings, vectorstore
from eval import ablation, run
from eval.dataset import CorpusDoc, QAItem


@pytest.fixture
def client():
    return vectorstore.get_client(location=":memory:")


@pytest.fixture(autouse=True)
def fake_embeddings(monkeypatch):
    async def fake_embed(texts):
        return [[1.0, 0.0, 0.0] for _ in texts]

    monkeypatch.setattr(embeddings, "embed", fake_embed)


CORPUS = [
    CorpusDoc(source="finance.pdf", text="Quarterly revenue grew 12 percent in Q3."),
    CorpusDoc(source="hr.pdf", text="Employees get 25 days of annual leave."),
    CorpusDoc(source="sku.pdf", text="Invoice SKU-4471 shipped to Berlin warehouse."),
]
QA = [
    QAItem("a", "How much did quarterly revenue grow?", "12 percent", "finance.pdf"),
    QAItem("b", "How many days of annual leave?", "25 days", "hr.pdf"),
    QAItem("c", "Where was SKU-4471 shipped?", "Berlin", "sku.pdf"),
]


async def test_run_ablation_reports_all_modes(client):
    bm25 = await run.build_indexes(CORPUS, client, collection="eval_documents")
    results = await ablation.run_ablation(QA, client, bm25, collection="eval_documents")

    assert set(results) == {"vector", "bm25", "hybrid"}
    for mode, score in results.items():
        assert 0.0 <= score <= 1.0, mode


async def test_bm25_finds_exact_terms(client):
    bm25 = await run.build_indexes(CORPUS, client, collection="eval_documents")
    results = await ablation.run_ablation(QA, client, bm25, collection="eval_documents")
    assert results["bm25"] > 0.0


def test_format_ablation_md():
    md = ablation.format_ablation_md(
        {"vector": 0.6, "bm25": 0.7, "hybrid": 0.9}, top_k=5
    )
    assert "Vector only" in md
    assert "BM25 only" in md
    assert "Hybrid (RRF)" in md
    assert "90%" in md
