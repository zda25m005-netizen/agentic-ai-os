"""Fetch a source page and extract its main text — for deeper, grounded evidence.

Snippets and abstracts are shallow; reading the actual page body gives the claim
extractor and the constrained LLM real content to reason over instead of a
one-liner. HTML is reduced to readable paragraph text with a dependency-free
stdlib parser (trafilatura is used when installed, for cleaner main-content
extraction); PDFs (e.g. arXiv) are read via PyMuPDF when available. Every call is
bounded (timeout + character cap) and fails soft (returns "") so enrichment can
never slow down or break a research step.
"""
from __future__ import annotations

import asyncio
import re
from html.parser import HTMLParser

import httpx

from app.tools import wikipedia

_UA = wikipedia._UA
_SKIP = {"script", "style", "noscript", "template", "svg", "head", "nav",
         "footer", "form", "aside", "button"}
_BLOCK = {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "br", "div", "tr",
          "section", "article"}


class _TextExtractor(HTMLParser):
    """Collect visible text, inserting newlines at block boundaries, skipping chrome."""

    def __init__(self) -> None:
        super().__init__()
        self._skip = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in _SKIP:
            self._skip += 1
        elif tag in _BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP and self._skip:
            self._skip -= 1
        elif tag in _BLOCK:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


def html_to_text(html: str, max_chars: int = 6000) -> str:
    """Reduce HTML to clean paragraph text, keeping only substantial lines."""
    try:
        p = _TextExtractor()
        p.feed(html or "")
        text = "".join(p.parts)
    except Exception:
        text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"[ \t]+", " ", text)
    # keep substantial paragraphs; drop nav crumbs and one-word fragments
    paras = [ln.strip() for ln in text.split("\n") if len(ln.strip()) >= 40]
    out = "\n".join(paras) if paras else re.sub(r"\s+", " ", text).strip()
    return out[:max_chars]


def _pdf_to_text(data: bytes, max_chars: int) -> str:
    try:
        import fitz  # PyMuPDF, optional
    except Exception:
        return ""
    try:
        doc = fitz.open(stream=data, filetype="pdf")
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        return re.sub(r"\n{3,}", "\n\n", text)[:max_chars]
    except Exception:
        return ""


async def fetch_and_extract(url: str, *, timeout: float = 10.0,
                            max_chars: int = 6000) -> str:
    """Fetch `url`, return clean main text (or '' on any failure). Bounded, best-effort."""
    if not url:
        return ""
    try:
        async with httpx.AsyncClient(timeout=timeout, headers={"user-agent": _UA},
                                     follow_redirects=True) as c:
            r = await c.get(url)
            r.raise_for_status()
            ctype = r.headers.get("content-type", "").lower()
            if "pdf" in ctype or url.lower().endswith(".pdf"):
                return _pdf_to_text(r.content, max_chars)
            try:
                import trafilatura  # optional: better main-content extraction
                extracted = trafilatura.extract(r.text) or ""
                if len(extracted.strip()) > 200:
                    return extracted[:max_chars]
            except Exception:
                pass
            return html_to_text(r.text, max_chars)
    except Exception:
        return ""


async def enrich_sources(results: list[dict], *, limit: int = 8, max_chars: int = 4000,
                         min_len: int = 400) -> list[dict]:
    """Upgrade shallow snippets to full-page text for up to `limit` sources.

    Fetches run concurrently and bounded; a snippet is only replaced when the
    fetched text is materially longer, and any failure leaves the original
    untouched. Never raises.
    """
    targets = results[:limit]

    async def one(item: dict) -> dict:
        text = await fetch_and_extract((item.get("url") or "").strip(), max_chars=max_chars)
        if len(text) > max(min_len, len(item.get("snippet") or "")):
            return {**item, "snippet": text, "full_text": True}
        return item

    try:
        done = await asyncio.gather(*(one(it) for it in targets), return_exceptions=True)
    except Exception:
        return results
    out = [res if isinstance(res, dict) else orig
           for orig, res in zip(targets, done, strict=False)]
    return out + results[limit:]
