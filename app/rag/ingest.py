"""End-to-end ingestion pipeline: file → load → chunk → embed → store.

This ties the RAG components together. Point it at a file (or hand it a
pre-loaded Document) and it lands searchable, citation-ready chunks in
Qdrant.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from qdrant_client import QdrantClient

from app.rag import embeddings, vectorstore
from app.rag.chunker import chunk_text
from app.rag.loaders import Document, load

DEFAULT_COLLECTION = "documents"


@dataclass
class IngestResult:
    """Outcome of ingesting one document."""

    source: str
    num_chunks: int
    ids: list[str] = field(default_factory=list)


async def ingest_document(
    doc: Document,
    client: QdrantClient,
    collection: str = DEFAULT_COLLECTION,
    chunk_size: int = 1600,
    overlap: int = 200,
) -> IngestResult:
    """Chunk, embed, and store a single loaded Document."""
    source = doc.metadata.get("source", "unknown")
    chunks = chunk_text(doc.text, chunk_size, overlap, metadata=doc.metadata)
    if not chunks:
        return IngestResult(source=source, num_chunks=0, ids=[])

    texts = [c.text for c in chunks]
    vectors = await embeddings.embed(texts)

    vectorstore.ensure_collection(client, collection, dim=len(vectors[0]))

    payloads = [
        {
            "text": c.text,
            "chunk_index": c.index,
            "source": c.metadata.get("source", source),
            "filetype": c.metadata.get("filetype"),
        }
        for c in chunks
    ]
    ids = vectorstore.upsert(client, collection, vectors, payloads)
    return IngestResult(source=source, num_chunks=len(chunks), ids=ids)


async def ingest_file(
    path: str | Path,
    client: QdrantClient,
    collection: str = DEFAULT_COLLECTION,
    chunk_size: int = 1600,
    overlap: int = 200,
) -> IngestResult:
    """Load a file from disk and ingest it."""
    doc = load(path)
    return await ingest_document(
        doc, client, collection, chunk_size=chunk_size, overlap=overlap
    )
