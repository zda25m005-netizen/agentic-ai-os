"""Minimal LLM client (OpenAI-compatible chat completions).

Works with OpenAI or any OpenAI-compatible endpoint via LLM_BASE_URL.
Kept dependency-light (httpx) on purpose; swap for the official SDK later if needed.
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


async def chat(messages: list[dict], temperature: float = 0.2) -> str:
    """Send chat messages, return the assistant's text.

    messages: [{"role": "user"|"system"|"assistant", "content": "..."}]
    """
    s = get_settings()
    if not is_configured():
        raise LLMNotConfigured("Set OPENAI_API_KEY or LLM_BASE_URL in your .env")

    headers = {"Content-Type": "application/json"}
    if s.openai_api_key:
        headers["Authorization"] = f"Bearer {s.openai_api_key}"

    payload = {"model": s.llm_model, "messages": messages, "temperature": temperature}

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{_base_url()}/chat/completions", json=payload, headers=headers
        )
        resp.raise_for_status()
        data = resp.json()
    return data["choices"][0]["message"]["content"]
