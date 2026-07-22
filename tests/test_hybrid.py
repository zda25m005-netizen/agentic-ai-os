import pytest

from app.rag import embeddings, retriever, vectorstore
from app.rag.bm25 import BM25Index
from app.rag.hybrid import reciprocal_rank_fusion
from app.rag.vectorstore import SearchHit


def _hit(id_: str, score: float = 1.0) -> SearchHit:
    return SearchHit(id=id_, score=score, payload={"id": id_})


def test_rrf_boosts_documents_in_both_lists():
    dense = [_hit("a"), _hit("b"), _hit("c")]
    sparse = [_hit("c"), _hit("d"), _hit("a")]
    fused = reciprocal_rank_fusion([dense, sparse], limit=4)
    ids = [h.id for h in fused]
    # 'a' (ranks 1 & 3) and 'c' (ranks 3 & 1) appear in both → top two.
    assert set(ids[:2]) == {"a", "c"}


def test_rrf_handles_empty_lists():
    assert reciprocal_rank_fusion([[], []]) == []
    only = reciprocal_rank_fusion([[_hit("x")], []], limit=5)
    assert [h.id for h in only] == ["x"]


def test_rrf_respects_limit():
    dense = [_hit(str(i)) for i in range(10)]
    fused = reciprocal_rank_fusion([dense], limit=3)
    assert len(fused) == 3


@pytest.fixture
def client():
    return vectorstore.get_client(location=":memory:")


@pytest.fixture(autouse=True)
def fake_embeddings(monkeypatch):
    async def fake_embed(texts):
        return [[float(len(t) % 5), 1.0, 0.0] for t in texts]

    monkeypatch.setattr(embeddings, "embed", fake_embed)


async def test_hybrid_retrieve_combines_sources(client):
    # Shared ids across vector store and BM25 index.
    vectorstore.ensure_collection(client, "documents", dim=3)
    ids = ["11111111-1111-1111-1111-111111111111",
           "22222222-2222-2222-2222-222222222222"]
    vectorstore.upsert(
        client,
        "documents",
        vectors=[[1.0, 1.0, 0.0], [3.0, 1.0, 0.0]],
        payloads=[{"text": "alpha", "source": "a"}, {"text": "SKU-99", "source": "b"}],
        ids=ids,
    )
    bm25 = BM25Index()
    bm25.add(ids[0], "alpha content here", {"source": "a"})
    bm25.add(ids[1], "invoice SKU-99 shipped", {"source": "b"})

    hits = await retriever.hybrid_retrieve("SKU-99", client, bm25, limit=2)
    assert hits
    assert all(isinstance(h, SearchHit) for h in hits)
    # The BM25 exact match id should surface in the fused results.
    assert ids[1] in [h.id for h in hits]


async def test_hybrid_retrieve_empty_query(client):
    assert await retriever.hybrid_retrieve("  ", client, BM25Index()) == []
