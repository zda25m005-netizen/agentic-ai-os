"""Evaluate the feedback reranker: off vs LLM vs learned, on the same benchmark.

The scoring core (`rerank_recall_on_candidates`) takes pre-retrieved candidates
and a reranker, so it's deterministic and unit-testable with fakes — no
embeddings or API. `main` wires the real retrieval + rerankers and prints a
recall@k comparison, and fits the learned reranker offline from the corpus.

Honest expectation: the learned reranker is lexical-only, so on this
identifier-heavy benchmark it may not beat the LLM reranker — the harness
reports whatever is true.
"""
from __future__ import annotations

import asyncio
import statistics
import sys

from app.rag.vectorstore import SearchHit
from eval.scorers import recall_at_k


async def rerank_recall_on_candidates(items, rerank_fn, top_k: int = 3) -> float:
    """Mean recall@k after reranking pre-retrieved candidates.

    `items`: iterable of (question, candidates: list[SearchHit], gold_source).
    """
    scores: list[float] = []
    for question, candidates, gold in items:
        reranked = await rerank_fn(question, candidates)
        sources = [h.payload.get("source", "") for h in reranked[:top_k]]
        scores.append(recall_at_k(sources, gold, top_k))
    return statistics.mean(scores) if scores else 0.0


async def compare_on_candidates(items, rerankers: dict, top_k: int = 3) -> dict[str, float]:
    """Recall@k for each named reranker over the same candidate lists."""
    return {
        name: await rerank_recall_on_candidates(items, fn, top_k)
        for name, fn in rerankers.items()
    }


def format_comparison(results: dict[str, float]) -> str:
    """Render a small Markdown table of reranker -> recall."""
    lines = ["| Reranker | Recall@k |", "|---|---|"]
    for name, value in results.items():
        lines.append(f"| {name} | {value:.0%} |")
    return "\n".join(lines)


def _fit_feedback_reranker(corpus, qa):
    """Fit the learned reranker offline: gold passage positive, others negative."""
    from app.rag.feedback_pairs import TrainingPair
    from app.rag.feedback_reranker import LearnedReranker

    text_by_source = {d.source: d.text for d in corpus}
    pairs: list[TrainingPair] = []
    for item in qa:
        for source, text in text_by_source.items():
            label = 1 if source == item.expected_source else 0
            pairs.append(TrainingPair(item.question, text, label))
    return LearnedReranker(min_pairs=4).fit(pairs)


async def main() -> int:
    from app.core import llm
    from app.rag import reranker, retriever, vectorstore
    from eval.ablation import (
        ABLATION_COLLECTION,
        load_ablation_corpus,
        load_ablation_qa,
    )
    from eval.run import build_indexes

    if not llm.is_configured():
        print("LLM/embeddings not configured. Set OPENAI_API_KEY or LLM_BASE_URL.",
              file=sys.stderr)
        return 1

    corpus, qa = load_ablation_corpus(), load_ablation_qa()
    client = vectorstore.get_client(location=":memory:")
    bm25 = await build_indexes(corpus, client, collection=ABLATION_COLLECTION)
    learned = _fit_feedback_reranker(corpus, qa)

    async def identity(_q, hits: list[SearchHit]):
        return hits

    items = []
    for item in qa:
        candidates = await retriever.hybrid_retrieve(
            item.question, client, bm25, collection=ABLATION_COLLECTION, limit=6
        )
        items.append((item.question, candidates, item.expected_source))

    rerankers = {
        "hybrid (no rerank)": identity,
        "LLM reranker": reranker.rerank,
        "feedback reranker": learned.rerank,
    }
    results = await compare_on_candidates(items, rerankers, top_k=3)
    print(format_comparison(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
