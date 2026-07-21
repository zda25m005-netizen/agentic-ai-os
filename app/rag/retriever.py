"""Retrieval: turn a question into relevant chunks, then into an answer prompt.

Day 15 is dense (vector) retrieval. Hybrid search (vector + BM25) arrives
in Day 17; citation-aware answers in Day 18. Keeping the seams clean here
so those upgrades slot in without touching the API layer.
"""
from __future__ import annotations

from qdrant_client import QdrantClient

from app.rag import embeddings, vectorstore
from app.rag.vectorstore import SearchHit

DEFAULT_COLLECTION = "documents"


async def retrieve(
    query: str,
    client: QdrantClient,
    collection: str = DEFAULT_COLLECTION,
    limit: int = 5,
) -> list[SearchHit]:
    """Embed the query and return the top-`limit` matching chunks."""
    if not query.strip():
        return []
    query_vector = await embeddings.embed_one(query)
    return vectorstore.search(client, collection, query_vector, limit=limit)


def build_context(hits: list[SearchHit]) -> str:
    """Render hits into a numbered context block for the LLM prompt."""
    blocks = []
    for i, hit in enumerate(hits, start=1):
        source = hit.payload.get("source", "unknown")
        text = hit.payload.get("text", "")
        blocks.append(f"[{i}] (source: {source})\n{text}")
    return "\n\n".join(blocks)


def build_messages(query: str, hits: list[SearchHit]) -> list[dict]:
    """Build the chat messages for a grounded answer."""
    context = build_context(hits)
    system = (
        "You are a precise assistant. Answer the question using ONLY the "
        "context provided. If the context does not contain the answer, say "
        "you don't know. Be concise."
    )
    user = f"Context:\n{context}\n\nQuestion: {query}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
