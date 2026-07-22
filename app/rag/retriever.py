"""Retrieval: turn a question into relevant chunks, then into an answer prompt.

Dense (vector) + sparse (BM25) retrieval fused with RRF. Citation-aware
answers arrive in Day 18. Seams kept clean so upgrades don't touch the API.
"""
from __future__ import annotations

from qdrant_client import QdrantClient

from app.rag import embeddings, vectorstore
from app.rag.bm25 import BM25Index
from app.rag.hybrid import reciprocal_rank_fusion
from app.rag.vectorstore import SearchHit

DEFAULT_COLLECTION = "documents"


async def retrieve(
    query: str,
    client: QdrantClient,
    collection: str = DEFAULT_COLLECTION,
    limit: int = 5,
) -> list[SearchHit]:
    """Embed the query and return the top-`limit` matching chunks (dense only)."""
    if not query.strip():
        return []
    query_vector = await embeddings.embed_one(query)
    return vectorstore.search(client, collection, query_vector, limit=limit)


async def hybrid_retrieve(
    query: str,
    client: QdrantClient,
    bm25_index: BM25Index,
    collection: str = DEFAULT_COLLECTION,
    limit: int = 5,
    fetch_k: int = 20,
) -> list[SearchHit]:
    """Dense + BM25 retrieval fused with RRF.

    Both retrievers must key documents by the same id (the Qdrant point id)
    so fusion can recognize the same chunk across lists. Each retriever
    fetches `fetch_k` candidates before fusion narrows to `limit`.
    """
    if not query.strip():
        return []
    dense = await retrieve(query, client, collection, limit=fetch_k)
    sparse = bm25_index.search(query, limit=fetch_k)
    return reciprocal_rank_fusion([dense, sparse], limit=limit)


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
