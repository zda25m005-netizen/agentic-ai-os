"""LLM-based reranker: re-score retrieved candidates against the query.

Retrieval (dense/BM25/hybrid) is fast but coarse. A reranker takes the top
candidates and scores each one's relevance to the query with a stronger
model, then reorders — pushing the best passage to rank 1. We use the LLM
as the scorer (a "listwise" rerank in one call) to avoid a heavyweight
cross-encoder dependency; the interface would accept a cross-encoder too.

Parsing is defensive: a malformed score response falls back to the original
order rather than crashing.
"""
from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable

from app.core import llm
from app.rag.vectorstore import SearchHit

ChatFn = Callable[[list[dict]], Awaitable[str]]

_RERANK_SYSTEM = (
    "You are a relevance judge. For each candidate passage, score how well it "
    "answers the query from 0 (irrelevant) to 10 (perfect). Reply with ONLY a "
    'JSON object mapping candidate index to score, e.g. {"0": 8, "1": 2}.'
)
_JSON_OBJ_RE = re.compile(r"\{.*\}", re.DOTALL)


def parse_scores(raw: str, n: int) -> dict[int, float]:
    """Parse the judge's JSON scores; return {} on any failure."""
    match = _JSON_OBJ_RE.search(raw or "")
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    scores: dict[int, float] = {}
    for key, value in data.items():
        try:
            idx = int(key)
            if 0 <= idx < n:
                scores[idx] = float(value)
        except (ValueError, TypeError):
            continue
    return scores


async def rerank(
    query: str,
    hits: list[SearchHit],
    chat_fn: ChatFn | None = None,
    top_k: int | None = None,
) -> list[SearchHit]:
    """Reorder `hits` by LLM-judged relevance to `query` (stable on ties)."""
    if not hits:
        return []
    chat_fn = chat_fn or llm.chat

    listing = "\n".join(
        f"[{i}] {(h.payload.get('text', '') or '')[:200]}" for i, h in enumerate(hits)
    )
    messages = [
        {"role": "system", "content": _RERANK_SYSTEM},
        {"role": "user", "content": f"Query: {query}\n\nCandidates:\n{listing}"},
    ]
    scores = parse_scores(await chat_fn(messages), len(hits))

    order = sorted(range(len(hits)), key=lambda i: scores.get(i, -1.0), reverse=True)
    ranked = [hits[i] for i in order]
    return ranked[:top_k] if top_k else ranked
