from fastapi.testclient import TestClient

from app.api.main import app
from app.core import llm
from app.rag import retriever, vectorstore
from app.rag.vectorstore import SearchHit

client = TestClient(app)


def test_ask_requires_config(monkeypatch):
    monkeypatch.setattr(llm, "is_configured", lambda: False)
    r = client.post("/ask", json={"question": "hi"})
    assert r.status_code == 503


def test_ask_returns_answer_and_sources(monkeypatch):
    monkeypatch.setattr(llm, "is_configured", lambda: True)
    monkeypatch.setattr(vectorstore, "get_client", lambda *a, **k: object())

    async def fake_retrieve(query, client, collection="documents", limit=5):
        return [
            SearchHit(
                id="1",
                score=0.91,
                payload={"text": "The capital is Paris.", "source": "geo.pdf",
                         "chunk_index": 0},
            )
        ]

    async def fake_chat(messages, temperature=0.2):
        return "The capital is Paris [1]."

    monkeypatch.setattr(retriever, "retrieve", fake_retrieve)
    monkeypatch.setattr(llm, "chat", fake_chat)

    r = client.post("/ask", json={"question": "What is the capital of France?"})
    assert r.status_code == 200
    body = r.json()
    assert "Paris" in body["answer"]
    assert body["sources"][0]["source"] == "geo.pdf"
    assert body["sources"][0]["score"] == 0.91
    # The inline [1] marker was parsed into a citation.
    assert body["citations"][0]["marker"] == 1
    assert body["citations"][0]["source"] == "geo.pdf"


def test_ask_no_hits_returns_dont_know(monkeypatch):
    monkeypatch.setattr(llm, "is_configured", lambda: True)
    monkeypatch.setattr(vectorstore, "get_client", lambda *a, **k: object())

    async def empty_retrieve(query, client, collection="documents", limit=5):
        return []

    monkeypatch.setattr(retriever, "retrieve", empty_retrieve)

    r = client.post("/ask", json={"question": "unknown topic"})
    assert r.status_code == 200
    assert "don't know" in r.json()["answer"].lower()
    assert r.json()["sources"] == []
