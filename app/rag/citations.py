"""Citation-aware answering.

The prompt instructs the LLM to cite context blocks inline with [n]
markers. After generation we parse which markers were actually used and
map each back to its source chunk, so the API can return exactly the
sources the answer relied on (and flag uncited answers).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.rag.vectorstore import SearchHit

_CITATION_RE = re.compile(r"\[(\d+)\]")

CITATION_SYSTEM_PROMPT = (
    "You are a precise assistant. Answer the question using ONLY the "
    "numbered context blocks. Cite the block you use inline with its "
    "number in square brackets, e.g. 'Revenue grew 12% [1].' Every claim "
    "must have a citation. If the context does not contain the answer, "
    "say you don't know. Be concise."
)


@dataclass
class Citation:
    """A source chunk the answer actually cited."""

    marker: int
    source: str
    chunk_index: int | None
    score: float
    text: str


def build_context(hits: list[SearchHit]) -> str:
    """Numbered context blocks for the prompt."""
    blocks = []
    for i, hit in enumerate(hits, start=1):
        source = hit.payload.get("source", "unknown")
        text = hit.payload.get("text", "")
        blocks.append(f"[{i}] (source: {source})\n{text}")
    return "\n\n".join(blocks)


def build_messages(query: str, hits: list[SearchHit]) -> list[dict]:
    """Chat messages instructing inline [n] citations."""
    context = build_context(hits)
    user = f"Context:\n{context}\n\nQuestion: {query}"
    return [
        {"role": "system", "content": CITATION_SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def parse_citations(answer: str, hits: list[SearchHit]) -> list[Citation]:
    """Extract [n] markers from the answer and map them to hits.

    Markers are 1-based (as shown to the model). Out-of-range or duplicate
    markers are ignored; order follows first appearance in the answer.
    """
    seen: set[int] = set()
    result: list[Citation] = []
    for match in _CITATION_RE.finditer(answer):
        marker = int(match.group(1))
        if marker in seen or not (1 <= marker <= len(hits)):
            continue
        seen.add(marker)
        hit = hits[marker - 1]
        result.append(
            Citation(
                marker=marker,
                source=hit.payload.get("source", "unknown"),
                chunk_index=hit.payload.get("chunk_index"),
                score=hit.score,
                text=hit.payload.get("text", ""),
            )
        )
    return result
