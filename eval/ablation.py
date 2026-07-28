"""Retrieval ablation study: vector-only vs BM25-only vs hybrid (RRF).

A controlled comparison on the same labeled dataset that isolates the
effect of the retrieval strategy. This answers the "why hybrid?" question
with numbers instead of assertion — the kind of ablation that turns a
design claim into evidence.

Metric: retrieval recall@k (did the gold source appear in the top-k?),
averaged over the Q&A set. Retrieval-only, so it needs embeddings but not
answer generation — cheap to run.
"""
from __future__ import annotations

import asyncio
import statistics
import sys
from collections.abc import Awaitable, Callable

from app.rag import retriever
from app.rag.bm25 import BM25Index
from eval.dataset import QAItem, load_corpus, load_qa, validate
from eval.run import EVAL_COLLECTION, build_indexes
from eval.scorers import recall_at_k

MODES = ("vector", "bm25", "hybrid")

RetrieveModes = Callable[[QAItem], Awaitable[dict[str, list[str]]]]


async def _sources_by_mode(
    item: QAItem, client, bm25: BM25Index, collection: str, top_k: int
) -> dict[str, list[str]]:
    """Run all three retrieval strategies; return the source list for each."""
    vector = await retriever.retrieve(item.question, client, collection, limit=top_k)
    sparse = bm25.search(item.question, limit=top_k)
    hybrid = await retriever.hybrid_retrieve(
        item.question, client, bm25, collection=collection, limit=top_k
    )
    return {
        "vector": [h.payload.get("source", "") for h in vector],
        "bm25": [h.payload.get("source", "") for h in sparse],
        "hybrid": [h.payload.get("source", "") for h in hybrid],
    }


async def run_ablation(
    qa: list[QAItem], client, bm25: BM25Index,
    collection: str = EVAL_COLLECTION, top_k: int = 5,
) -> dict[str, float]:
    """Return mean recall@k for each retrieval mode."""
    scores: dict[str, list[float]] = {m: [] for m in MODES}
    for item in qa:
        by_mode = await _sources_by_mode(item, client, bm25, collection, top_k)
        for mode in MODES:
            scores[mode].append(recall_at_k(by_mode[mode], item.expected_source, top_k))
    return {mode: statistics.mean(vals) if vals else 0.0 for mode, vals in scores.items()}


def format_ablation_md(results: dict[str, float], top_k: int = 5) -> str:
    """Render the ablation as a Markdown comparison table."""
    label = {"vector": "Vector only (dense)",
             "bm25": "BM25 only (sparse)",
             "hybrid": "Hybrid (RRF)"}
    lines = [f"| Retrieval strategy | Recall@{top_k} |", "|---|---|"]
    for mode in MODES:
        lines.append(f"| {label[mode]} | {results[mode]:.0%} |")
    return "\n".join(lines)


async def main() -> int:
    from app.core import llm
    from app.rag import vectorstore

    if not llm.is_configured():
        print("LLM/embeddings not configured. Set OPENAI_API_KEY or LLM_BASE_URL.",
              file=sys.stderr)
        return 1

    corpus, qa = load_corpus(), load_qa()
    validate(qa, corpus)
    client = vectorstore.get_client(location=":memory:")
    bm25 = await build_indexes(corpus, client)

    results = await run_ablation(qa, client, bm25)
    print(format_ablation_md(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
