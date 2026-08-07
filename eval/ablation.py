"""Retrieval ablation study: vector-only vs BM25-only vs hybrid (RRF).

A controlled comparison on a purpose-built benchmark that isolates the
effect of the retrieval strategy. The benchmark is designed to *discriminate*:
  - 10 documents (more than k) so retrieval must rank, not dump everything
  - exact-identifier queries (SKU codes, cipher names) that favor BM25
  - paraphrase/synonym queries that favor dense vectors
  - reported at recall@1 and recall@3, where ranking quality actually shows

This answers "why hybrid?" with evidence: each single method wins on its
own strength, and hybrid stays robust across both.

Metric: retrieval recall@k (did the gold source appear in top-k?), averaged.
Retrieval-only — needs embeddings but not answer generation.
"""
from __future__ import annotations

import asyncio
import json
import statistics
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path

from app.rag import retriever
from app.rag.bm25 import BM25Index
from app.rag.vectorstore import SearchHit
from eval.dataset import CorpusDoc, QAItem
from eval.run import build_indexes
from eval.scorers import recall_at_k

MODES = ("vector", "bm25", "hybrid")
_LABEL_ORDER = ("vector", "bm25", "hybrid", "rerank", "feedback")

# rerank_fn(query, hits) -> reordered hits
RerankFn = Callable[[str, list[SearchHit]], Awaitable[list[SearchHit]]]
_DATA_DIR = Path(__file__).parent / "datasets"
ABLATION_CORPUS = _DATA_DIR / "ablation_corpus.json"
ABLATION_QA = _DATA_DIR / "ablation_qa.json"
ABLATION_COLLECTION = "ablation_documents"


def load_ablation_corpus(path: Path = ABLATION_CORPUS) -> list[CorpusDoc]:
    data = json.loads(Path(path).read_text())
    return [CorpusDoc(source=d["source"], text=d["text"]) for d in data]


def load_ablation_qa(path: Path = ABLATION_QA) -> list[QAItem]:
    data = json.loads(Path(path).read_text())
    return [
        QAItem(d["id"], d["question"], d["expected_answer"], d["expected_source"])
        for d in data
    ]


async def _sources_by_mode(
    item: QAItem, client, bm25: BM25Index, collection: str, top_k: int,
    rerank_fn: RerankFn | None = None, feedback_rerank_fn: RerankFn | None = None,
    pool: int = 6,
) -> dict[str, list[str]]:
    vector = await retriever.retrieve(item.question, client, collection, limit=top_k)
    sparse = bm25.search(item.question, limit=top_k)
    hybrid = await retriever.hybrid_retrieve(
        item.question, client, bm25, collection=collection, limit=top_k
    )
    modes = {
        "vector": [h.payload.get("source", "") for h in vector],
        "bm25": [h.payload.get("source", "") for h in sparse],
        "hybrid": [h.payload.get("source", "") for h in hybrid],
    }
    if rerank_fn is not None or feedback_rerank_fn is not None:
        candidates = await retriever.hybrid_retrieve(
            item.question, client, bm25, collection=collection, limit=pool
        )
        if rerank_fn is not None:
            reranked = await rerank_fn(item.question, candidates)
            modes["rerank"] = [h.payload.get("source", "") for h in reranked[:top_k]]
        if feedback_rerank_fn is not None:
            reranked = await feedback_rerank_fn(item.question, candidates)
            modes["feedback"] = [h.payload.get("source", "") for h in reranked[:top_k]]
    return modes


async def run_ablation(
    qa: list[QAItem], client, bm25: BM25Index,
    collection: str = ABLATION_COLLECTION, top_k: int = 3,
    rerank_fn: RerankFn | None = None, feedback_rerank_fn: RerankFn | None = None,
) -> dict[str, float]:
    """Return mean recall@k per mode (+ rerank/feedback rerankers if provided)."""
    modes = list(MODES)
    if rerank_fn:
        modes.append("rerank")
    if feedback_rerank_fn:
        modes.append("feedback")
    scores: dict[str, list[float]] = {m: [] for m in modes}
    for item in qa:
        by_mode = await _sources_by_mode(
            item, client, bm25, collection, top_k, rerank_fn, feedback_rerank_fn
        )
        for mode in modes:
            scores[mode].append(recall_at_k(by_mode[mode], item.expected_source, top_k))
    return {mode: statistics.mean(vals) if vals else 0.0 for mode, vals in scores.items()}


def format_ablation_table(results_by_k: dict[int, dict[str, float]]) -> str:
    """Render a Markdown table with one recall@k column per k."""
    label = {"vector": "Vector only (dense)",
             "bm25": "BM25 only (sparse)",
             "hybrid": "Hybrid (RRF)",
             "rerank": "Hybrid + LLM reranker",
             "feedback": "Hybrid + feedback reranker"}
    ks = sorted(results_by_k)
    present = [m for m in _LABEL_ORDER if m in results_by_k[ks[0]]]
    header = "| Retrieval strategy | " + " | ".join(f"Recall@{k}" for k in ks) + " |"
    sep = "|---|" + "|".join("---" for _ in ks) + "|"
    lines = [header, sep]
    for mode in present:
        cells = " | ".join(f"{results_by_k[k][mode]:.0%}" for k in ks)
        lines.append(f"| {label[mode]} | {cells} |")
    return "\n".join(lines)


async def main() -> int:
    from app.core import llm
    from app.rag import reranker, vectorstore

    if not llm.is_configured():
        print("LLM/embeddings not configured. Set OPENAI_API_KEY or LLM_BASE_URL.",
              file=sys.stderr)
        return 1

    corpus, qa = load_ablation_corpus(), load_ablation_qa()
    client = vectorstore.get_client(location=":memory:")
    bm25 = await build_indexes(corpus, client, collection=ABLATION_COLLECTION)

    async def rerank_fn(query, hits):
        return await reranker.rerank(query, hits)

    results_by_k = {}
    for k in (1, 3):
        results_by_k[k] = await run_ablation(qa, client, bm25, top_k=k, rerank_fn=rerank_fn)
    print(format_ablation_table(results_by_k))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
