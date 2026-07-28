import pytest

from app.rag import embeddings, vectorstore
from eval import ablation, run


@pytest.fixture
def client():
    return vectorstore.get_client(location=":memory:")


@pytest.fixture(autouse=True)
def fake_embeddings(monkeypatch):
    async def fake_embed(texts):
        return [[float(len(t) % 11), float(len(t) % 7), 1.0] for t in texts]

    monkeypatch.setattr(embeddings, "embed", fake_embed)


def test_ablation_dataset_loads():
    corpus = ablation.load_ablation_corpus()
    qa = ablation.load_ablation_qa()
    assert len(corpus) >= 10
    assert len(qa) >= 10
    sources = {d.source for d in corpus}
    assert all(item.expected_source in sources for item in qa)


async def test_run_ablation_reports_all_modes(client):
    corpus, qa = ablation.load_ablation_corpus(), ablation.load_ablation_qa()
    bm25 = await run.build_indexes(corpus, client, collection=ablation.ABLATION_COLLECTION)
    results = await ablation.run_ablation(qa, client, bm25, top_k=3)

    assert set(results) == {"vector", "bm25", "hybrid"}
    for mode, score in results.items():
        assert 0.0 <= score <= 1.0, mode


async def test_bm25_recovers_exact_codes(client):
    corpus, qa = ablation.load_ablation_corpus(), ablation.load_ablation_qa()
    bm25 = await run.build_indexes(corpus, client, collection=ablation.ABLATION_COLLECTION)
    results = await ablation.run_ablation(qa, client, bm25, top_k=3)
    assert results["bm25"] > 0.0


async def test_run_ablation_includes_rerank_when_provided(client):
    corpus, qa = ablation.load_ablation_corpus(), ablation.load_ablation_qa()
    bm25 = await run.build_indexes(corpus, client, collection=ablation.ABLATION_COLLECTION)

    async def perfect_rerank(query, hits):
        return list(reversed(hits))

    results = await ablation.run_ablation(
        qa, client, bm25, top_k=3, rerank_fn=perfect_rerank
    )
    assert "rerank" in results
    assert 0.0 <= results["rerank"] <= 1.0


def test_format_ablation_table_multi_k():
    md = ablation.format_ablation_table(
        {1: {"vector": 0.5, "bm25": 0.6, "hybrid": 0.8, "rerank": 0.9},
         3: {"vector": 0.7, "bm25": 0.7, "hybrid": 0.9, "rerank": 1.0}}
    )
    assert "Recall@1" in md and "Recall@3" in md
    assert "Vector only" in md and "Hybrid (RRF)" in md
    assert "Hybrid + reranker" in md
    assert "80%" in md
