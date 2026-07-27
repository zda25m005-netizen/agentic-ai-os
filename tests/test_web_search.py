import httpx
import pytest

from app.tools import web_search as ws

SAMPLE = {
    "Heading": "Python",
    "AbstractText": "Python is a high-level programming language.",
    "AbstractURL": "https://en.wikipedia.org/wiki/Python",
    "RelatedTopics": [
        {"Text": "Guido van Rossum - creator of Python",
         "FirstURL": "https://example.com/guido"},
        {"Text": "", "FirstURL": ""},
        {"Text": "PyPI - the Python Package Index",
         "FirstURL": "https://pypi.org"},
    ],
}


def test_parse_ddg_includes_abstract_first():
    results = ws.parse_ddg(SAMPLE, max_results=3)
    assert results[0]["snippet"].startswith("Python is a high-level")
    assert results[0]["url"].endswith("Python")


def test_parse_ddg_skips_empty_and_respects_limit():
    results = ws.parse_ddg(SAMPLE, max_results=2)
    assert len(results) == 2
    assert all(r["snippet"] for r in results)


def test_format_results_numbered():
    out = ws.format_results(ws.parse_ddg(SAMPLE, max_results=2))
    assert out.startswith("1. ")
    assert "2. " in out


def test_format_results_empty():
    assert ws.format_results([]) == "No results found."


@pytest.fixture
def fake_ddg(monkeypatch):
    class FakeTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            return httpx.Response(200, json=SAMPLE)

    real_client = httpx.AsyncClient

    def factory(**kwargs):
        kwargs["transport"] = FakeTransport()
        return real_client(**kwargs)

    monkeypatch.setattr(ws.httpx, "AsyncClient", factory)


async def test_web_search_handler(fake_ddg):
    out = await ws.web_search("python", max_results=2)
    assert "Python is a high-level" in out
    assert out.startswith("1. ")


async def test_web_search_handles_http_error(monkeypatch):
    class FailTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            raise httpx.ConnectError("boom")

    real_client = httpx.AsyncClient

    def factory(**kwargs):
        kwargs["transport"] = FailTransport()
        return real_client(**kwargs)

    monkeypatch.setattr(ws.httpx, "AsyncClient", factory)
    out = await ws.web_search("anything")
    assert out.startswith("error")


def test_web_search_registered():
    from app.tools.registry import default_registry
    assert "web_search" in default_registry.names()
