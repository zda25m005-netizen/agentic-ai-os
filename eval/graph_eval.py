"""GraphRAG evaluation: measure how well graph-backed answers cover the facts.

Each item has a question and the key facts a correct answer must mention. The
scorer is fact coverage — the fraction of expected facts that appear in the
answer — averaged across the set. The runner takes an injectable `answer_fn`
(question -> answer) so tests run offline; the real command answers via the
knowledge graph + LLM.
"""
from __future__ import annotations

import asyncio
import json
import statistics
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path

from eval.scorers import normalize

_DATA_DIR = Path(__file__).parent / "datasets"
GRAPH_QA_PATH = _DATA_DIR / "graph_qa.json"

AnswerFn = Callable[[str], Awaitable[str]]


@dataclass
class GraphEvalReport:
    n: int = 0
    coverage: float = 0.0
    per_item: list[dict] = field(default_factory=list)


def fact_coverage(answer: str, expected_facts: list[str]) -> float:
    """Fraction of expected facts present (substring, normalized) in the answer."""
    if not expected_facts:
        return 0.0
    a = normalize(answer)
    hits = sum(1 for f in expected_facts if normalize(str(f)) in a)
    return hits / len(expected_facts)


def load_graph_qa(path: Path = GRAPH_QA_PATH) -> list[dict]:
    return json.loads(Path(path).read_text())


async def run_graph_eval(answer_fn: AnswerFn, items: list[dict] | None = None) -> GraphEvalReport:
    """Score `answer_fn` over the graph-QA set; return coverage + per-item detail."""
    items = items if items is not None else load_graph_qa()
    scores: list[float] = []
    per_item: list[dict] = []
    for item in items:
        answer = await answer_fn(item["question"])
        score = fact_coverage(answer, item.get("expected_facts", []))
        scores.append(score)
        per_item.append({"id": item.get("id"), "coverage": score})
    return GraphEvalReport(
        n=len(items),
        coverage=statistics.mean(scores) if scores else 0.0,
        per_item=per_item,
    )


async def _graph_answer(question: str) -> str:
    """Real answer_fn: fetch graph facts and let the LLM answer from them."""
    from app.core import llm
    from app.graph.fusion import build_graphrag_messages
    from app.graph.retrieval import get_graph_context

    ctx = await get_graph_context(question)
    if not ctx.triples:
        return "I don't know."
    return await llm.chat(build_graphrag_messages(question, [], ctx.text))


def main() -> None:
    report = asyncio.run(run_graph_eval(_graph_answer))
    print(f"GraphRAG eval — {report.n} questions")
    print(f"  fact coverage: {report.coverage:.2%}")
    for row in report.per_item:
        print(f"    {row['id']}: {row['coverage']:.0%}")


if __name__ == "__main__":
    main()
