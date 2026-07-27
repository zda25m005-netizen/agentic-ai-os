"""HTTP GET tool: fetch a public URL.

Read-only (GET only) with a basic SSRF guard — it refuses localhost and
private network ranges so the agent can't be tricked into probing internal
services. Output is truncated to keep tool responses bounded.
"""
from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

import httpx

from app.tools.registry import tool

MAX_OUTPUT = 4000
_BLOCKED_HOSTS = {"localhost", "0.0.0.0", "::1"}


def is_allowed_url(url: str) -> bool:
    """Allow only http/https to public hosts (blocks SSRF to internal IPs)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    if host in _BLOCKED_HOSTS:
        return False
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return False
    except ValueError:
        pass
    return True


async def _fetch(url: str) -> str:
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text[:MAX_OUTPUT]


@tool(
    name="http_get",
    description="Fetch the contents of a public URL over HTTP(S) (GET only).",
    parameters={
        "type": "object",
        "properties": {"url": {"type": "string", "description": "Public http(s) URL"}},
        "required": ["url"],
    },
)
async def http_get(url: str) -> str:
    """Tool handler: fetch a URL after an SSRF safety check."""
    if not is_allowed_url(url):
        return "error: url not allowed (must be a public http/https address)"
    try:
        return await _fetch(url)
    except httpx.HTTPError as exc:
        return f"error: fetch failed: {exc}"
