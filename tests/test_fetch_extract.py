"""Full-page fetch + extract: HTML -> clean text, snippet enrichment (offline)."""
import app.tools.fetch_extract as fe


def test_html_to_text_strips_chrome_keeps_paragraphs():
    html = """
    <html><head><title>T</title><style>.x{}</style></head>
    <body>
      <nav>Home About Contact</nav>
      <script>var x = 1;</script>
      <article>
        <h1>Retrieval-Augmented Generation</h1>
        <p>RAG combines a retriever with a language model to ground generation in
           external documents, which improves factual accuracy for knowledge tasks.</p>
        <p>It scales to large corpora but adds retrieval latency at inference time.</p>
      </article>
      <footer>Copyright 2026</footer>
    </body></html>
    """
    text = fe.html_to_text(html)
    assert "RAG combines a retriever" in text
    assert "scales to large corpora" in text
    assert "var x = 1" not in text            # script stripped
    assert "Home About Contact" not in text   # nav dropped (too short / chrome)


def test_html_to_text_respects_char_cap():
    html = "<p>" + ("word " * 5000) + "</p>"
    assert len(fe.html_to_text(html, max_chars=500)) <= 500


async def test_enrich_sources_upgrades_snippet(monkeypatch):
    async def fake_fetch(url, **kw):
        return "FULL " + ("content " * 100) if "good" in url else ""
    monkeypatch.setattr(fe, "fetch_and_extract", fake_fetch)
    src = [{"url": "https://good.com/a", "snippet": "short snippet"},
           {"url": "https://bad.com/b", "snippet": "keep me"}]
    out = await fe.enrich_sources(src, limit=8)
    assert out[0]["snippet"].startswith("FULL") and out[0].get("full_text")
    assert out[1]["snippet"] == "keep me"     # failed fetch leaves original intact


async def test_enrich_never_raises(monkeypatch):
    async def boom(url, **kw):
        raise RuntimeError("network down")
    monkeypatch.setattr(fe, "fetch_and_extract", boom)
    src = [{"url": "https://x.com", "snippet": "s"}]
    out = await fe.enrich_sources(src)
    assert out and out[0]["snippet"] == "s"
