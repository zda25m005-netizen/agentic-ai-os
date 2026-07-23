"""Evaluation runner: ingest the corpus, answer every gold question, score.

`python -m eval.run` (or `make eval`) ingests the labeled corpus into an
in-memory store, runs the real hybrid-retrieval + citation-answer pipeline
over each question, scores against the gold labels, prints a metrics table,
and writes eval/results.json.

Runs fully in-memory (no Docker) but DOES need embeddings + an LLM, so the
real command requires a configured key. The pieces are injectable so tests
run offline with fakes.
"""
from __future__ import annotations

import asyncio
import json
import statistics
import sys
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path

from app.core import llm
from app.rag import citations, embeddings, retriever, vectorstore
from app.rag.bm25 import BM25Index
from app.rag.chunker import chunk_text
from eval import scorers
from eval.dataset import CorpusDoc, QAItem, load_corpus, load_qa, validate

EVAL_COLLECTION = "eval_documents"
RESULTS_PATH = Path(__file__).parent / "results.json"

AnswerFn = Callable[[list[dict]], Awaitable[str]]


@dataclass
class EvalReport:
    n: int
    recall_at_k: float
    answer_match: float
    citation_accuracy: float
    llm_judge: float | None = None
    per_item: list[dict] = field(default_factory=list)


async def build_indexes(
    corpus: list[CorpusDoc],
    client,
    collection: str = EVAL_COLLECTION,
) -> BM25Index:
    """Chunk + embed the corpus into Qdrant and a BM25 index (shared ids)."""
    bm25 = BM25Index()
    for doc in corpus:
        chunks = chunk_text(doc.text, metadata={"source": doc.source})
        vectors = await embeddings.embed([c.text for c in chunks])
        vectorstore.ensure_collection(client, collection, dim=len(vectors[0]))
        ids = [str(uuid.uuid4()) for _ in chunks]
        payloads = [
            {"text": c.text, "source": doc.source, "chunk_index": c.index}
            for c in chunks
        ]
        vectorstore.upsert(client, collection, vectors, payloads, ids=ids)
        for cid, c in zip(ids, chunks, strict=True):
            bm25.add(cid, c.text, {"source": doc.source, "chunk_index": c.index})
    return bm25


async def run_eval(
    qa: list[QAItem],
    client,
    bm25: BM25Index,
    answer_fn: AnswerFn,
    collection: str = EVAL_COLLECTION,
    top_k: int = 5,
    judge_fn: AnswerFn | None = None,
) -> EvalReport:
    """Run retrieval + answering + scoring over every Q&A item."""
    recalls, matches, cites, judges = [], [], [], []
    per_item = []

    for item in qa:
        hits = await retriever.hybrid_retrieve(
            item.question, client, bm25, collection=collection, limit=top_k
        )
        sources = [h.payload.get("source", "") for h in hits]
        recall = scorers.recall_at_k(sources, item.expected_source, k=top_k)

        messages = citations.build_messages(item.question, hits)
        answer = await answer_fn(messages)
        cited = [c.source for c in citations.parse_citations(answer, hits)]

        match = scorers.answer_match(item.expected_answer, answer)
        cite = scorers.citation_accuracy(cited, item.expected_source)

        judge = None
        if judge_fn is not None:
            judge = await scorers.llm_judge(
                item.question, item.expected_answer, answer, judge_fn
            )
            judges.append(judge)

        recalls.append(recall)
        matches.append(match)
        cites.append(cite)
        per_item.append(
            {
                "id": item.id,
                "recall": recall,
                "answer_match": match,
                "citation": cite,
                "judge": judge,
                "answer": answer,
            }
        )

    return EvalReport(
        n=len(qa),
        recall_at_k=statistics.mean(recalls) if recalls else 0.0,
        answer_match=statistics.mean(matches) if matches else 0.0,
        citation_accuracy=statistics.mean(cites) if cites else 0.0,
        llm_judge=statistics.mean(judges) if judges else None,
        per_item=per_item,
    )


def format_report_md(report: EvalReport, top_k: int = 5) -> str:
    """Render the report as a Markdown metrics table."""
    rows = [
        ("Questions", str(report.n)),
        (f"Retrieval recall@{top_k}", f"{report.recall_at_k:.0%}"),
        ("Answer match (exact)", f"{report.answer_match:.0%}"),
        ("Citation accuracy", f"{report.citation_accuracy:.0%}"),
    ]
    if report.llm_judge is not None:
        rows.append(("Answer correctness (LLM-judge)", f"{report.llm_judge:.0%}"))

    lines = ["| Metric | Score |", "|---|---|"]
    lines += [f"| {name} | {value} |" for name, value in rows]
    return "\n".join(lines)


async def main() -> int:
    if not llm.is_configured():
        print(
            "LLM/embeddings not configured. Set OPENAI_API_KEY or LLM_BASE_URL "
            "in .env to run the full evaluation.",
            file=sys.stderr,
        )
        return 1

    corpus, qa = load_corpus(), load_qa()
    validate(qa, corpus)

    client = vectorstore.get_client(location=":memory:")
    bm25 = await build_indexes(corpus, client)

    report = await run_eval(qa, client, bm25, answer_fn=llm.chat, judge_fn=llm.chat)

    print(format_report_md(report))
    RESULTS_PATH.write_text(json.dumps(asdict(report), indent=2))
    print(f"\nWrote {RESULTS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
