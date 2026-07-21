import pytest

from app.rag import vectorstore


@pytest.fixture
def client():
    return vectorstore.get_client(location=":memory:")


def test_ensure_collection_is_idempotent(client):
    vectorstore.ensure_collection(client, "docs", dim=3)
    vectorstore.ensure_collection(client, "docs", dim=3)  # no error second time
    assert client.collection_exists("docs")


def test_upsert_and_search_returns_nearest(client):
    vectorstore.ensure_collection(client, "docs", dim=3)
    ids = vectorstore.upsert(
        client,
        "docs",
        vectors=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        payloads=[{"t": "x"}, {"t": "y"}, {"t": "z"}],
    )
    assert len(ids) == 3

    hits = vectorstore.search(client, "docs", query_vector=[0.9, 0.1, 0.0], limit=1)
    assert len(hits) == 1
    assert hits[0].payload["t"] == "x"
    assert 0.0 <= hits[0].score <= 1.0


def test_upsert_uses_supplied_ids(client):
    vectorstore.ensure_collection(client, "docs", dim=2)
    ids = vectorstore.upsert(
        client,
        "docs",
        vectors=[[1.0, 0.0]],
        payloads=[{"t": "a"}],
        ids=["11111111-1111-1111-1111-111111111111"],
    )
    assert ids == ["11111111-1111-1111-1111-111111111111"]


def test_upsert_length_mismatch_raises(client):
    vectorstore.ensure_collection(client, "docs", dim=2)
    with pytest.raises(ValueError):
        vectorstore.upsert(client, "docs", vectors=[[1.0, 0.0]], payloads=[])


def test_search_respects_limit(client):
    vectorstore.ensure_collection(client, "docs", dim=2)
    vectorstore.upsert(
        client,
        "docs",
        vectors=[[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]],
        payloads=[{"i": 0}, {"i": 1}, {"i": 2}],
    )
    hits = vectorstore.search(client, "docs", query_vector=[1.0, 0.0], limit=2)
    assert len(hits) == 2
