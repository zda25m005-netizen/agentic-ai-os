"""Semantic memory: recall past runs by meaning, not keywords.

Each run is embedded and stored in a Qdrant collection. Given a new goal,
`recall` finds the most similar past runs — so the agent can reuse prior
work even when the wording differs. Complements the keyword search in
episodic memory.
"""
from __future__ import annotations

from dataclasses import dataclass

from qdrant_client import QdrantClient

from app.rag import embeddings, vectorstore

MEMORY_COLLECTION = "agent_memory"


@dataclass
class MemoryHit:
    """A recalled past run with its similarity score."""

    goal: str
    answer: str
    score: float


class SemanticMemory:
    """Vector store of embedded past runs."""

    def __init__(self, client: QdrantClient, collection: str = MEMORY_COLLECTION):
        self._client = client
        self._collection = collection

    async def add(self, goal: str, answer: str) -> None:
        """Embed and store a run."""
        text = f"Goal: {goal}\nAnswer: {answer}"
        vector = await embeddings.embed_one(text)
        vectorstore.ensure_collection(self._client, self._collection, dim=len(vector))
        vectorstore.upsert(
            self._client, self._collection, [vector], [{"goal": goal, "answer": answer}]
        )

    async def recall(self, query: str, limit: int = 3) -> list[MemoryHit]:
        """Return the most semantically similar past runs (empty if none)."""
        if not query.strip() or not self._client.collection_exists(self._collection):
            return []
        vector = await embeddings.embed_one(query)
        hits = vectorstore.search(self._client, self._collection, vector, limit=limit)
        return [
            MemoryHit(
                goal=h.payload.get("goal", ""),
                answer=h.payload.get("answer", ""),
                score=h.score,
            )
            for h in hits
        ]
