"""Wikipedia tool: fetch a topic summary.

Uses Wikipedia's REST summary endpoint for richer factual lookups than the
DuckDuckGo instant-answer API. Parser is pure; the network call is isolated
for offline testing.
"""
from __future__ import annotations

import asyncio
import re

import httpx

from app.tools.registry import tool

WIKI_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/"
WIKI_API_URL = "https://en.wikipedia.org/w/api.php"
# Wikimedia's User-Agent policy requires a descriptive UA that identifies the
# client and a way to contact the operator; a generic UA gets 429-throttled.
_UA = ("agentic-ai-os/1.0 "
       "(https://github.com/zda25m005-netizen/agentic-ai-os; jhag8094@gmail.com)")


def parse_summary(data: dict) -> str:
    """Extract a readable summary from the REST response."""
    title = data.get("title", "")
    extract = (data.get("extract") or "").strip()
    if not extract:
        return "No summary found."
    return f"{title}: {extract}" if title else extract


def _title_url(title: str) -> str:
    return "https://en.wikipedia.org/wiki/" + title.strip().replace(" ", "_")


def parse_search(data: dict, max_results: int = 4) -> list[dict]:
    """Turn a MediaWiki search response into [{title, snippet, url}] with real URLs."""
    out: list[dict] = []
    for item in (data.get("query", {}).get("search", []) or [])[:max_results]:
        title = (item.get("title") or "").strip()
        if not title:
            continue
        snippet = re.sub(r"<[^>]+>", "", item.get("snippet") or "").strip()
        out.append({"title": title, "snippet": snippet or title, "url": _title_url(title)})
    return out


async def _search_fetch(query: str, max_results: int, retries: int = 2) -> dict:
    params = {
        "action": "query", "list": "search", "srsearch": query,
        "format": "json", "srlimit": max_results,
    }
    async with httpx.AsyncClient(timeout=15, headers={"user-agent": _UA}) as client:
        for attempt in range(retries + 1):
            resp = await client.get(WIKI_API_URL, params=params)
            if resp.status_code == 429 and attempt < retries:
                wait = float(resp.headers.get("retry-after", 1.0) or 1.0)
                await asyncio.sleep(min(wait, 3.0))
                continue
            resp.raise_for_status()
            return resp.json()
    resp.raise_for_status()  # exhausted retries
    return resp.json()


async def search(query: str, max_results: int = 4) -> list[dict]:
    """Keyless web search over Wikipedia; returns real sources ([] on failure)."""
    try:
        return parse_search(await _search_fetch(query, max_results), max_results)
    except Exception:
        return []


async def _fetch(title: str) -> dict:
    url = WIKI_SUMMARY_URL + title.strip().replace(" ", "_")
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        resp = await client.get(url, headers={"accept": "application/json"})
        resp.raise_for_status()
        return resp.json()


@tool(
    name="wikipedia",
    description="Get a concise Wikipedia summary for a topic or title.",
    parameters={
        "type": "object",
        "properties": {"title": {"type": "string", "description": "Article title/topic"}},
        "required": ["title"],
    },
)
async def wikipedia(title: str) -> str:
    """Tool handler: fetch and format a Wikipedia summary."""
    try:
        data = await _fetch(title)
    except httpx.HTTPError as exc:
        return f"error: wikipedia lookup failed: {exc}"
    return parse_summary(data)
