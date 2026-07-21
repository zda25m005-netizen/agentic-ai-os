"""BM25 keyword retrieval (Okapi BM25), implemented from scratch.

Vector search matches meaning; BM25 matches exact terms — product codes,
names, acronyms ("SKU-4471") that embeddings often blur. Day 17 fuses the
two. Implemented directly (no extra dependency) so the ranking math is
transparent and testable.

Scoring per document D for query Q:
    score = Σ_t IDF(t) · (f(t,D)·(k1+1)) / (f(t,D) + k1·(1 - b + b·|D|/avgdl))
where IDF(t) = ln(1 + (N - n(t) + 0.5) / (n(t) + 0.5)).
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field

from app.rag.vectorstore import SearchHit

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lowercase and split into alphanumeric tokens."""
    return _TOKEN_RE.findall(text.lower())


@dataclass
class _Doc:
    id: str
    tokens: list[str]
    length: int
    freqs: Counter
    payload: dict


@dataclass
class BM25Index:
    """In-memory BM25 index. Add documents, then search."""

    k1: float = 1.5
    b: float = 0.75
    _docs: list[_Doc] = field(default_factory=list)
    _df: Counter = field(default_factory=Counter)
    _avgdl: float = 0.0

    def add(self, doc_id: str, text: str, payload: dict | None = None) -> None:
        tokens = tokenize(text)
        freqs = Counter(tokens)
        self._docs.append(
            _Doc(id=doc_id, tokens=tokens, length=len(tokens), freqs=freqs,
                 payload=payload or {})
        )
        for term in freqs:
            self._df[term] += 1
        total = sum(d.length for d in self._docs)
        self._avgdl = total / len(self._docs) if self._docs else 0.0

    def _idf(self, term: str) -> float:
        n = self._df.get(term, 0)
        total = len(self._docs)
        return math.log(1 + (total - n + 0.5) / (n + 0.5))

    def search(self, query: str, limit: int = 5) -> list[SearchHit]:
        if not self._docs or not query.strip():
            return []
        q_terms = tokenize(query)
        scored: list[tuple[float, _Doc]] = []
        for doc in self._docs:
            score = 0.0
            for term in q_terms:
                f = doc.freqs.get(term, 0)
                if f == 0:
                    continue
                denom = f + self.k1 * (1 - self.b + self.b * doc.length / self._avgdl)
                score += self._idf(term) * (f * (self.k1 + 1)) / denom
            if score > 0:
                scored.append((score, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            SearchHit(id=doc.id, score=score, payload=doc.payload)
            for score, doc in scored[:limit]
        ]

    def __len__(self) -> int:
        return len(self._docs)
