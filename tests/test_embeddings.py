import httpx
import pytest

from app.core.llm import LLMNotConfigured
from app.rag import embeddings


class FakeTransport(httpx.AsyncBaseTransport):
    """Fake the /embeddings endpoint; return a 3-dim vector per input."""

    def __init__(self):
        self.requests: list[dict] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        import json

        payload = json.loads(request.content)
        self.requests.append(payload)
        data = [
            {"index": i, "embedding": [float(i), 0.5, -0.5]}
            for i in range(len(payload["input"]))
        ]
        return httpx.Response(200, json={"data": data})


@pytest.fixture
def fake_api(monkeypatch):
    transport = FakeTransport()
    real_client = httpx.AsyncClient

    def client_factory(**kwargs):
        kwargs["transport"] = transport
        return real_client(**kwargs)

    monkeypatch.setattr(embeddings, "is_configured", lambda: True)
    monkeypatch.setattr(embeddings.httpx, "AsyncClient", client_factory)
    return transport


async def test_embed_returns_vector_per_text(fake_api):
    vectors = await embeddings.embed(["hello", "world"])
    assert len(vectors) == 2
    assert all(len(v) == 3 for v in vectors)


async def test_embed_empty_list_short_circuits(fake_api):
    assert await embeddings.embed([]) == []
    assert fake_api.requests == []


async def test_embed_batches_large_inputs(fake_api):
    texts = [f"text {i}" for i in range(embeddings.MAX_BATCH_SIZE + 5)]
    vectors = await embeddings.embed(texts)
    assert len(vectors) == len(texts)
    assert len(fake_api.requests) == 2  # two batches

    first, second = fake_api.requests
    assert len(first["input"]) == embeddings.MAX_BATCH_SIZE
    assert len(second["input"]) == 5


async def test_embed_one(fake_api):
    v = await embeddings.embed_one("solo")
    assert v == [0.0, 0.5, -0.5]


async def test_embed_requires_config(monkeypatch):
    monkeypatch.setattr(embeddings, "is_configured", lambda: False)
    with pytest.raises(LLMNotConfigured):
        await embeddings.embed(["hi"])
