"""Build training pairs for the feedback reranker.

Feedback is answer-level (👍/👎 on a query's answer); we propagate that rating to
the passages retrieved for the query, yielding (query, passage, label) pairs.
`retrieve_fn` is injected, so this is backend-agnostic and unit-testable.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from app.rag.vectorstore import SearchHit

RetrieveFn = Callable[[str], Awaitable[list[SearchHit]]]


@dataclass
class TrainingPair:
    query: str
    passage: str
    label: int  # 1 = relevant (👍), 0 = not (👎)


async def pairs_from_feedback(feedback_items, retrieve_fn: RetrieveFn) -> list[TrainingPair]:
    """A rating labels the passages retrieved for that query (👍 pos, 👎 neg)."""
    pairs: list[TrainingPair] = []
    for fb in feedback_items:
        label = 1 if getattr(fb, "rating", "") == "up" else 0
        for hit in await retrieve_fn(fb.query):
            passage = hit.payload.get("text", "")
            if passage:
                pairs.append(TrainingPair(query=fb.query, passage=passage, label=label))
    return pairs
