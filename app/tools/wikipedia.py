"""Wikipedia tool: fetch a topic summary.

Uses Wikipedia's REST summary endpoint for richer factual lookups than the
DuckDuckGo instant-answer API. Parser is pure; the network call is isolated
for offline testing.
"""
from __future__ import annotations

import httpx

from app.tools.registry import tool

WIKI_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/"


def parse_summary(data: dict) -> str:
    """Extract a readable summary from the REST response."""
    title = data.get("title", "")
    extract = (data.get("extract") or "").strip()
    if not extract:
        return "No summary found."
    return f"{title}: {extract}" if title else extract


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
