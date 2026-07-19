"""Embeddings client (OpenAI-compatible /embeddings endpoint).

Works with OpenAI, or any OpenAI-compatible provider (e.g. Gemini's
compatibility endpoint) via LLM_BASE_URL. Batches requests to stay
under provider input limits.
"""
from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.core.llm import LLMNotConfigured, is_configured

# Most providers cap inputs per request; 128 is a safe, efficient batch.
MAX_BATCH_SIZE = 128


def _base_url() -> str:
    s = get_settings()
    return (s.llm_base_url or "https://api.openai.com/v1").rstrip("/")


async def embed(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts, preserving order. Batches automatically."""
    if not texts:
        return []
    if not is_configured():
        raise LLMNotConfigured("Set OPENAI_API_KEY or LLM_BASE_URL in your .env")

    s = get_settings()
    headers = {"Content-Type": "application/json"}
    if s.openai_api_key:
        headers["Authorization"] = f"Bearer {s.openai_api_key}"

    vectors: list[list[float]] = []
    async with httpx.AsyncClient(timeout=120) as client:
        for start in range(0, len(texts), MAX_BATCH_SIZE):
            batch = texts[start : start + MAX_BATCH_SIZE]
            resp = await client.post(
                f"{_base_url()}/embeddings",
                json={"model": s.embedding_model, "input": batch},
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            # Providers may return items out of order; sort by index.
            items = sorted(data["data"], key=lambda d: d["index"])
            vectors.extend(item["embedding"] for item in items)
    return vectors


async def embed_one(text: str) -> list[float]:
    """Embed a single text."""
    result = await embed([text])
    return result[0]
