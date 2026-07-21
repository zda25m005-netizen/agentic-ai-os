import pytest

from app.rag import embeddings, retriever, vectorstore
from app.rag.vectorstore import SearchHit


@pytest.fixture
def client():
    return vectorstore.get_client(location=":memory:")


@pytest.fixture(autouse=True)
def fake_embeddings(monkeypatch):
    async def fake_embed(texts):
        # Simple deterministic embedding: length-based signature.
        return [[float(len(t) % 7), 1.0, 0.0] for t in texts]

    monkeypatch.setattr(embeddings, "embed", fake_embed)


async def test_retrieve_empty_query_returns_nothing(client):
    assert await retriever.retrieve("   ", client) == []


async def test_retrieve_returns_hits(client):
    vectorstore.ensure_collection(client, "documents", dim=3)
    vectorstore.upsert(
        client,
        "documents",
        vectors=[[1.0, 1.0, 0.0], [5.0, 1.0, 0.0]],
        payloads=[{"text": "aa", "source": "a.pdf"}, {"text": "bbbbb", "source": "b.pdf"}],
    )
    hits = await retriever.retrieve("query", client, limit=2)
    assert len(hits) == 2
    assert all(isinstance(h, SearchHit) for h in hits)


def test_build_context_numbers_sources():
    hits = [
        SearchHit(id="1", score=0.9, payload={"text": "first", "source": "a.pdf"}),
        SearchHit(id="2", score=0.8, payload={"text": "second", "source": "b.pdf"}),
    ]
    ctx = retriever.build_context(hits)
    assert "[1] (source: a.pdf)" in ctx
    assert "[2] (source: b.pdf)" in ctx
    assert "first" in ctx and "second" in ctx


def test_build_messages_grounds_the_prompt():
    hits = [SearchHit(id="1", score=0.9, payload={"text": "Paris.", "source": "geo.pdf"})]
    messages = retriever.build_messages("What is the capital?", hits)
    assert messages[0]["role"] == "system"
    assert "ONLY the context" in messages[0]["content"]
    assert "What is the capital?" in messages[1]["content"]
    assert "Paris." in messages[1]["content"]
