"""Minimal LLM client (OpenAI-compatible chat completions).

Works with OpenAI or any OpenAI-compatible endpoint via LLM_BASE_URL.
`chat` returns text; `chat_raw` returns the full assistant message (with
tool_calls) so the agent's tool-use loop can act on function calls.
"""
from __future__ import annotations

import httpx

from app.core.config import get_settings


class LLMNotConfigured(RuntimeError):
    """Raised when no API key / base URL is configured."""


def is_configured() -> bool:
    s = get_settings()
    return bool(s.openai_api_key or s.llm_base_url)


def _base_url() -> str:
    s = get_settings()
    return (s.llm_base_url or "https://api.openai.com/v1").rstrip("/")


async def _post(payload: dict) -> dict:
    s = get_settings()
    headers = {"Content-Type": "application/json"}
    if s.openai_api_key:
        headers["Authorization"] = f"Bearer {s.openai_api_key}"
    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(
            f"{_base_url()}/chat/completions", json=payload, headers=headers
        )
        resp.raise_for_status()
        return resp.json()


async def chat_raw(
    messages: list[dict],
    tools: list[dict] | None = None,
    temperature: float = 0.2,
) -> dict:
    """Send messages (optionally with tool specs); return the assistant message.

    The returned dict may contain `content` and/or `tool_calls`.
    """
    if not is_configured():
        raise LLMNotConfigured("Set OPENAI_API_KEY or LLM_BASE_URL in your .env")
    payload: dict = {
        "model": get_settings().llm_model,
        "messages": messages,
        "temperature": temperature,
    }
    if tools:
        payload["tools"] = tools
    data = await _post(payload)
    return data["choices"][0]["message"]


async def chat(messages: list[dict], temperature: float = 0.2) -> str:
    """Send chat messages, return the assistant's text."""
    message = await chat_raw(messages, temperature=temperature)
    return message.get("content") or ""
