"""Hybrid retrieval via Reciprocal Rank Fusion (RRF).

Dense (vector) and sparse (BM25) retrievers each return a ranked list.
RRF merges them by rank, not by score — which sidesteps the problem that
cosine similarities and BM25 scores live on totally different scales.

RRF score for a document d:
    score(d) = Σ_r  1 / (k + rank_r(d))
summed over every ranked list r it appears in (rank starts at 1). k is a
smoothing constant (60 is the standard default from the original paper).
"""
from __future__ import annotations

from app.rag.vectorstore import SearchHit

RRF_K = 60


def reciprocal_rank_fusion(
    result_lists: list[list[SearchHit]],
    k: int = RRF_K,
    limit: int = 5,
) -> list[SearchHit]:
    """Fuse multiple ranked hit-lists into one, by reciprocal rank.

    Documents are keyed by id; the payload from the first list that
    contains a document is kept. Returns the top-`limit` fused hits with
    the RRF score in `.score`.
    """
    scores: dict[str, float] = {}
    payloads: dict[str, dict] = {}

    for hits in result_lists:
        for rank, hit in enumerate(hits, start=1):
            scores[hit.id] = scores.get(hit.id, 0.0) + 1.0 / (k + rank)
            payloads.setdefault(hit.id, hit.payload)

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return [
        SearchHit(id=doc_id, score=score, payload=payloads[doc_id])
        for doc_id, score in ranked[:limit]
    ]
