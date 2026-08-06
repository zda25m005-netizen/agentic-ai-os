"""Feedback-driven reranker.

Turns user 👍/👎 into a lightweight learned scorer over (query, passage)
features, then reorders retrieved passages by predicted relevance. Until enough
labeled data exists (cold start) it transparently falls back to the existing
LLM reranker — so quality never regresses while the signal accumulates.

Deliberately dependency-free: features are lexical (term coverage, Jaccard,
length), and training is a tiny logistic-regression gradient descent. That keeps
it deterministic and unit-testable with no model download or API call. The
interface matches `app.rag.reranker.rerank`, so it's a drop-in.
"""
from __future__ import annotations

import math
import re

from app.rag import reranker as llm_reranker
from app.rag.feedback_pairs import RetrieveFn, TrainingPair, pairs_from_feedback
from app.rag.vectorstore import SearchHit

# Re-export so callers can use one module surface.
__all__ = [
    "features",
    "LearnedReranker",
    "TrainingPair",
    "RetrieveFn",
    "pairs_from_feedback",
]

_WORD_RE = re.compile(r"\w+")
N_FEATURES = 3


def _tokens(text: str) -> set[str]:
    return set(_WORD_RE.findall((text or "").lower()))


def features(query: str, passage: str) -> list[float]:
    """Cheap lexical features in [0, 1]: coverage, Jaccard, length."""
    q, p = _tokens(query), _tokens(passage)
    if not q:
        return [0.0, 0.0, 0.0]
    overlap = len(q & p)
    coverage = overlap / len(q)
    jaccard = overlap / len(q | p) if (q | p) else 0.0
    length = min(len(p), 300) / 300.0
    return [coverage, jaccard, length]


class LearnedReranker:
    """Logistic-regression reranker over lexical features; LLM fallback if cold."""

    def __init__(self, min_pairs: int = 4):
        self.weights: list[float] | None = None
        self.bias: float = 0.0
        self.min_pairs = min_pairs

    @property
    def is_fitted(self) -> bool:
        return self.weights is not None

    def fit(self, pairs: list[TrainingPair], epochs: int = 300, lr: float = 0.5) -> LearnedReranker:
        """Fit weights on labeled pairs. Stays unfitted (cold) below min_pairs."""
        if len({p.label for p in pairs}) < 2 or len(pairs) < self.min_pairs:
            self.weights = None  # need both classes and enough signal
            return self
        w = [0.0] * N_FEATURES
        b = 0.0
        for _ in range(epochs):
            for pair in pairs:
                x = features(pair.query, pair.passage)
                z = sum(wi * xi for wi, xi in zip(w, x, strict=True)) + b
                pred = 1.0 / (1.0 + math.exp(-z))
                err = pred - pair.label
                for i in range(N_FEATURES):
                    w[i] -= lr * err * x[i]
                b -= lr * err
        self.weights, self.bias = w, b
        return self

    def score(self, query: str, passage: str) -> float:
        """Predicted relevance in [0, 1]. Requires a fitted model."""
        if self.weights is None:
            raise RuntimeError("reranker is not fitted")
        x = features(query, passage)
        z = sum(wi * xi for wi, xi in zip(self.weights, x, strict=True)) + self.bias
        return 1.0 / (1.0 + math.exp(-z))

    async def rerank(
        self,
        query: str,
        hits: list[SearchHit],
        chat_fn=None,
        top_k: int | None = None,
    ) -> list[SearchHit]:
        """Reorder hits by learned score; fall back to the LLM reranker if cold."""
        if not hits:
            return []
        if not self.is_fitted:
            return await llm_reranker.rerank(query, hits, chat_fn=chat_fn, top_k=top_k)
        order = sorted(
            range(len(hits)),
            key=lambda i: self.score(query, hits[i].payload.get("text", "")),
            reverse=True,
        )
        ranked = [hits[i] for i in order]
        return ranked[:top_k] if top_k else ranked
