from datetime import UTC, datetime

import httpx
import pytest

from app.rag.vectorstore import SearchHit
from app.tools import clock, http_tool, rag_search, wikipedia
from app.tools.registry import default_registry


async def test_rag_search_returns_passages(monkeypatch):
    import app.core.llm as llm_mod
    monkeypatch.setattr(llm_mod, "is_configured", lambda: True)
    monkeypatch.setattr(rag_search.vectorstore, "get_client", lambda *a, **k: object())

    async def fake_retrieve(query, client, collection="documents", limit=3):
        return [SearchHit(id="1", score=0.9,
                          payload={"text": "Revenue grew 12%.", "source": "q3.pdf"})]

    monkeypatch.setattr(rag_search.retriever, "retrieve", fake_retrieve)
    out = await rag_search.rag_search("revenue")
    assert "Revenue grew 12%" in out
    assert "q3.pdf" in out


async def test_rag_search_requires_config(monkeypatch):
    import app.core.llm as llm_mod
    monkeypatch.setattr(llm_mod, "is_configured", lambda: False)
    out = await rag_search.rag_search("x")
    assert out.startswith("error")


def test_now_iso_uses_injected_clock():
    fixed = datetime(2030, 1, 2, 3, 4, 5, tzinfo=UTC)
    assert clock.now_iso(lambda: fixed) == "2030-01-02T03:04:05+00:00"


async def test_current_datetime_handler_is_iso():
    out = await clock.current_datetime()
    assert "T" in out and out.endswith("+00:00")


def test_is_allowed_url_public():
    assert http_tool.is_allowed_url("https://example.com/data")


def test_is_allowed_url_blocks_internal():
    assert not http_tool.is_allowed_url("http://localhost:8000")
    assert not http_tool.is_allowed_url("http://127.0.0.1/")
    assert not http_tool.is_allowed_url("http://10.0.0.5/")
    assert not http_tool.is_allowed_url("ftp://example.com")


async def test_http_get_rejects_internal():
    out = await http_tool.http_get("http://127.0.0.1/secret")
    assert out.startswith("error")


async def test_http_get_fetches(monkeypatch):
    class T(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            return httpx.Response(200, text="hello page")

    real = httpx.AsyncClient
    monkeypatch.setattr(http_tool.httpx, "AsyncClient",
                        lambda **k: real(**{**k, "transport": T()}))
    out = await http_tool.http_get("https://example.com")
    assert "hello page" in out


def test_parse_summary():
    data = {"title": "Python", "extract": "A programming language."}
    assert wikipedia.parse_summary(data) == "Python: A programming language."


def test_parse_summary_empty():
    assert wikipedia.parse_summary({"title": "X", "extract": ""}) == "No summary found."


async def test_wikipedia_handler(monkeypatch):
    class T(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            return httpx.Response(200, json={"title": "Ada Lovelace",
                                             "extract": "A mathematician."})

    real = httpx.AsyncClient
    monkeypatch.setattr(wikipedia.httpx, "AsyncClient",
                        lambda **k: real(**{**k, "transport": T()}))
    out = await wikipedia.wikipedia("Ada Lovelace")
    assert "Ada Lovelace" in out and "mathematician" in out


@pytest.mark.parametrize("name", ["rag_search", "current_datetime", "http_get", "wikipedia"])
def test_bonus_tools_registered(name):
    assert name in default_registry.names()
