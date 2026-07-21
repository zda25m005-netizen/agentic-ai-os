"""Qdrant vector store wrapper.

Thin, typed layer over qdrant-client: connection, collection lifecycle,
upsert, and similarity search. Keeps the rest of the app decoupled from
Qdrant's SDK so the backend could be swapped later.

Tests use in-memory mode (QdrantClient(location=":memory:")) so no Docker
or network is required in CI.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.core.config import get_settings


@dataclass
class SearchHit:
    """A single similarity-search result."""

    id: str
    score: float
    payload: dict


def get_client(location: str | None = None) -> QdrantClient:
    """Return a Qdrant client.

    location=":memory:" gives an in-process store (tests). Otherwise we
    connect to the configured QDRANT_URL.
    """
    if location == ":memory:":
        return QdrantClient(location=":memory:")
    url = location or get_settings().qdrant_url
    return QdrantClient(url=url)


def ensure_collection(client: QdrantClient, name: str, dim: int) -> None:
    """Create the collection if it doesn't already exist (cosine distance)."""
    if client.collection_exists(name):
        return
    client.create_collection(
        collection_name=name,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
    )


def upsert(
    client: QdrantClient,
    collection: str,
    vectors: list[list[float]],
    payloads: list[dict],
    ids: list[str] | None = None,
) -> list[str]:
    """Upsert vectors + payloads. Returns the point ids used."""
    if len(vectors) != len(payloads):
        raise ValueError("vectors and payloads must be the same length")
    point_ids = ids or [str(uuid.uuid4()) for _ in vectors]

    points = [
        PointStruct(id=pid, vector=vec, payload=payload)
        for pid, vec, payload in zip(point_ids, vectors, payloads, strict=True)
    ]
    client.upsert(collection_name=collection, points=points)
    return point_ids


def search(
    client: QdrantClient,
    collection: str,
    query_vector: list[float],
    limit: int = 5,
) -> list[SearchHit]:
    """Return the top-`limit` most similar points."""
    results = client.query_points(
        collection_name=collection, query=query_vector, limit=limit
    ).points
    return [
        SearchHit(id=str(r.id), score=r.score, payload=r.payload or {})
        for r in results
    ]
