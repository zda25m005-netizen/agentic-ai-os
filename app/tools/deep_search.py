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
_S2_API = "https://api.semanticscholar.org/graph/v1/paper/search"


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


# --- Semantic Scholar (keyless, real papers with authors/year) --------------

def parse_semanticscholar(data: dict, max_results: int = 6) -> list[dict]:
    out: list[dict] = []
    for p in (data.get("data") or [])[:max_results]:
        title = (p.get("title") or "").strip()
        ext = p.get("externalIds") or {}
        if ext.get("ArXiv"):
            url, pub = f"https://arxiv.org/abs/{ext['ArXiv']}", "arxiv.org"
        elif ext.get("DOI"):
            url, pub = f"https://doi.org/{ext['DOI']}", "doi.org"
        else:
            url, pub = (p.get("url") or ""), "semanticscholar.org"
        if not (title and url):
            continue
        authors = [a.get("name", "") for a in (p.get("authors") or [])][:4]
        out.append({"title": title, "url": url, "publisher": pub,
                    "snippet": (p.get("abstract") or title)[:1000],
                    "authors": authors, "year": p.get("year"),
                    "venue": (p.get("venue") or "").strip() or None})
    return out


async def semantic_scholar_search(query: str, max_results: int = 6) -> list[dict]:
    params = {"query": query, "limit": max_results,
              "fields": "title,abstract,year,authors,externalIds,url,venue"}
    try:
        async with httpx.AsyncClient(timeout=20, headers={"user-agent": _UA}) as c:
            r = await c.get(_S2_API, params=params)
            r.raise_for_status()
            return parse_semanticscholar(r.json(), max_results)
    except Exception:
        return []


# --- combined multi-source deep research ------------------------------------

async def deep_research(query: str, max_results: int = 6) -> list[dict]:
    """Multi-source: Wikipedia extracts + Semantic Scholar + arXiv, deduped.

    Returns up to ~14 rich source dicts so a single research step yields real
    diversity (encyclopedic + peer-reviewed) instead of one Wikipedia page.
    """
    results: list[dict] = []
    seen: set[str] = set()

    def add(items: list[dict]) -> None:
        for it in items:
            u = (it.get("url") or "").strip()
            if u and u not in seen:
                seen.add(u)
                results.append(it)

    wiki: list[dict] = []
    for hit in await wikipedia.search(query, max_results):
        extract = await wiki_extract(hit["title"])
        wiki.append({"title": hit["title"], "url": hit["url"],
                     "snippet": (extract or hit.get("snippet", ""))[:1200],
                     "publisher": "en.wikipedia.org"})
    add(wiki)
    add(await semantic_scholar_search(query, max_results=6))
    add(await arxiv_search(query, max_results=4))
    return results[:14]
