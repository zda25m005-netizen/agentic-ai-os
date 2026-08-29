"""Deeper, keyless research: full Wikipedia extracts + arXiv papers.

Snippets are shallow. This module fetches *full article intro extracts* from
Wikipedia (paragraphs, not one-line snippets) and adds real arXiv papers with
their abstracts — both keyless and free — so the researcher has substantial,
citable content to reason over. Parsers are pure (unit-tested offline); network
calls are isolated and fail soft (return []), so a research step never breaks.
"""
from __future__ import annotations

import re

import httpx

from app.tools import wikipedia

_UA = wikipedia._UA
_WIKI_API = "https://en.wikipedia.org/w/api.php"
_ARXIV_API = "http://export.arxiv.org/api/query"


# --- Wikipedia full extract -------------------------------------------------

def parse_extract(data: dict) -> str:
    pages = (data.get("query", {}) or {}).get("pages", {}) or {}
    for page in pages.values():
        extract = (page.get("extract") or "").strip()
        if extract:
            return re.sub(r"\n{2,}", " ", extract)
    return ""


async def wiki_extract(title: str) -> str:
    params = {"action": "query", "prop": "extracts", "explaintext": 1, "exintro": 1,
              "redirects": 1, "format": "json", "titles": title}
    try:
        async with httpx.AsyncClient(timeout=15, headers={"user-agent": _UA}) as c:
            r = await c.get(_WIKI_API, params=params)
            r.raise_for_status()
            return parse_extract(r.json())
    except Exception:
        return ""


# --- arXiv ------------------------------------------------------------------

def _tag(entry: str, name: str) -> str:
    m = re.search(rf"<{name}[^>]*>(.*?)</{name}>", entry, re.DOTALL)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def parse_arxiv(xml: str, max_results: int = 3) -> list[dict]:
    out: list[dict] = []
    for entry in re.findall(r"<entry>(.*?)</entry>", xml or "", re.DOTALL)[:max_results]:
        url, title, summary = _tag(entry, "id"), _tag(entry, "title"), _tag(entry, "summary")
        if url and title:
            out.append({"title": title, "url": url.replace("http://", "https://"),
                        "snippet": summary[:1000], "publisher": "arxiv.org",
                        "published": (_tag(entry, "published") or "")[:10] or None})
    return out


async def arxiv_search(query: str, max_results: int = 3) -> list[dict]:
    params = {"search_query": f"all:{query}", "start": 0, "max_results": max_results}
    try:
        async with httpx.AsyncClient(timeout=15, headers={"user-agent": _UA}) as c:
            r = await c.get(_ARXIV_API, params=params)
            r.raise_for_status()
            return parse_arxiv(r.text, max_results)
    except Exception:
        return []


# --- combined deep research -------------------------------------------------

async def deep_research(query: str, max_results: int = 4) -> list[dict]:
    """Wikipedia (with full extracts) + arXiv, as [{title, snippet, url, ...}]."""
    results: list[dict] = []
    for hit in await wikipedia.search(query, max_results):
        extract = await wiki_extract(hit["title"])
        results.append({
            "title": hit["title"], "url": hit["url"],
            "snippet": (extract or hit.get("snippet", ""))[:1200],
            "publisher": "en.wikipedia.org",
        })
    results.extend(await arxiv_search(query, max_results=2))
    return results
