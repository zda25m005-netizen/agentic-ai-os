"""GraphRAG fusion: combine vector/BM25 retrieval with the knowledge graph.

Two complementary signals: RAG finds passages that are *semantically* similar;
the graph finds chunks that *mention the query's entities*. We RRF-merge the two
rankings (keyed by source), then build a prompt that puts structured graph facts
above the fused passages — so the LLM sees both relationships and prose.

Reuses the existing `reciprocal_rank_fusion`; the fused hits carry the RAG
payload (which has the passage text) wherever a source appears in both.
"""
from __future__ import annotations

from app.rag import retriever
from app.rag.hybrid import reciprocal_rank_fusion
from app.rag.vectorstore import SearchHit

_GRAPHRAG_SYSTEM = (
    "You are a precise assistant. Answer using ONLY the context provided — the "
    "knowledge-graph facts and the passages. If the answer isn't there, say you "
    "don't know. Cite passages with their [n] markers. Be concise."
)


def _rekey_by_source(hits: list[SearchHit]) -> list[SearchHit]:
    """Copy hits re-keyed by their source, so fusion aligns with graph hits."""
    return [
        SearchHit(id=h.payload.get("source", "unknown"), score=h.score, payload=h.payload)
        for h in hits
    ]


def fuse_hits(
    rag_hits: list[SearchHit],
    graph_hits: list[SearchHit],
    limit: int = 5,
) -> list[SearchHit]:
    """RRF-merge RAG and graph chunk hits by source; keep RAG payloads (text)."""
    fused = reciprocal_rank_fusion([_rekey_by_source(rag_hits), graph_hits], limit=limit)
    rag_by_source: dict[str, SearchHit] = {}
    for h in rag_hits:
        rag_by_source.setdefault(h.payload.get("source", "unknown"), h)
    out: list[SearchHit] = []
    for f in fused:
        rep = rag_by_source.get(f.id)
        out.append(SearchHit(id=f.id, score=f.score, payload=rep.payload if rep else f.payload))
    return out


def build_graphrag_messages(
    question: str, hits: list[SearchHit], graph_text: str = ""
) -> list[dict]:
    """Prompt with graph facts prepended to the fused passage context."""
    context = retriever.build_context(hits)
    if graph_text:
        context = f"Knowledge-graph facts:\n{graph_text}\n\nPassages:\n{context}"
    return [
        {"role": "system", "content": _GRAPHRAG_SYSTEM},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
    ]
