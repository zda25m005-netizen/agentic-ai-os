"""Web search tool (DuckDuckGo Instant Answer API).

Uses DuckDuckGo's free JSON endpoint — no API key required — so the agent
can pull live information. The response parser is pure (easy to test); the
HTTP call is isolated so tests can fake it without hitting the network.
"""
from __future__ import annotations

import httpx

from app.tools.registry import tool

DDG_URL = "https://api.duckduckgo.com/"


def parse_ddg(data: dict, max_results: int = 3) -> list[dict]:
    """Turn a DuckDuckGo IA response into a list of {title, snippet, url}."""
    results: list[dict] = []

    abstract = (data.get("AbstractText") or "").strip()
    if abstract:
        results.append(
            {
                "title": data.get("Heading", "Summary"),
                "snippet": abstract,
                "url": data.get("AbstractURL", ""),
            }
        )

    for topic in data.get("RelatedTopics", []):
        if len(results) >= max_results:
            break
        text = (topic.get("Text") or "").strip()
        if not text:
            continue
        results.append(
            {
                "title": text.split(" - ")[0][:80],
                "snippet": text,
                "url": topic.get("FirstURL", ""),
            }
        )

    return results[:max_results]


def format_results(results: list[dict]) -> str:
    """Render results as a compact numbered list for the agent."""
    if not results:
        return "No results found."
    lines = []
    for i, r in enumerate(results, start=1):
        url = f" ({r['url']})" if r.get("url") else ""
        lines.append(f"{i}. {r['snippet']}{url}")
    return "\n".join(lines)


async def _fetch(query: str) -> dict:
    params = {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(DDG_URL, params=params)
        resp.raise_for_status()
        return resp.json()


@tool(
    name="web_search",
    description="Search the web for current information on a query.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to search for"},
            "max_results": {"type": "integer", "description": "Max results (default 3)"},
        },
        "required": ["query"],
    },
)
async def web_search(query: str, max_results: int = 3) -> str:
    """Tool handler: search the web and return formatted snippets."""
    try:
        data = await _fetch(query)
    except (httpx.HTTPError, ValueError) as exc:
        return f"error: web search failed: {exc}"
    return format_results(parse_ddg(data, max_results=max_results))
