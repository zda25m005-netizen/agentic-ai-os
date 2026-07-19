"""Recursive text chunking with overlap.

Splits on the largest structural boundary that fits the size budget:
paragraphs first, then sentences, then words. Overlap keeps context
across chunk borders so retrieval doesn't lose meaning at the seams.

Sizes are measured in characters (~4 chars ≈ 1 token for English), so
chunk_size=1600 ≈ 400 tokens — a solid default for embedding models.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_PARAGRAPH_RE = re.compile(r"\n\s*\n")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass
class Chunk:
    """A chunk of a source document, ready for embedding."""

    text: str
    index: int
    metadata: dict = field(default_factory=dict)


def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in _PARAGRAPH_RE.split(text) if p.strip()]


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_RE.split(text) if s.strip()]


def _pack(pieces: list[str], chunk_size: int, joiner: str) -> list[str]:
    """Greedily pack pieces into strings no longer than chunk_size."""
    packed: list[str] = []
    current = ""
    for piece in pieces:
        candidate = f"{current}{joiner}{piece}" if current else piece
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                packed.append(current)
            current = piece
    if current:
        packed.append(current)
    return packed


def _split_recursive(text: str, chunk_size: int) -> list[str]:
    """Split text into pieces <= chunk_size, preferring natural boundaries."""
    if len(text) <= chunk_size:
        return [text]

    paragraphs = _split_paragraphs(text)
    if len(paragraphs) > 1:
        result: list[str] = []
        for packed in _pack(paragraphs, chunk_size, "\n\n"):
            result.extend(_split_recursive(packed, chunk_size))
        return result

    sentences = _split_sentences(text)
    if len(sentences) > 1:
        result = []
        for packed in _pack(sentences, chunk_size, " "):
            result.extend(_split_recursive(packed, chunk_size))
        return result

    # Last resort: hard split on words.
    words = text.split()
    return _pack(words, chunk_size, " ")


def chunk_text(
    text: str,
    chunk_size: int = 1600,
    overlap: int = 200,
    metadata: dict | None = None,
) -> list[Chunk]:
    """Chunk text with overlap carried from the tail of the previous chunk.

    Args:
        text: source text.
        chunk_size: max characters per chunk.
        overlap: characters of trailing context prepended to the next chunk.
        metadata: copied onto every chunk (e.g. source filename).
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    text = text.strip()
    if not text:
        return []

    pieces = _split_recursive(text, chunk_size - overlap)

    chunks: list[Chunk] = []
    prev_tail = ""
    for i, piece in enumerate(pieces):
        body = f"{prev_tail}{piece}" if prev_tail else piece
        chunks.append(Chunk(text=body, index=i, metadata=dict(metadata or {})))
        prev_tail = piece[-overlap:] + "\n" if overlap and len(piece) > overlap else ""
    return chunks
