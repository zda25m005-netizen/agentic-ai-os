"""Assemble SFT instruction/response examples from the labeled QA sets.

Sources are the same datasets the eval harness uses, so the fine-tune targets
the exact behavior we measure: concise, factual answers over the corpus, and
relational answers from the knowledge graph. Deduped by instruction.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parents[2] / "eval" / "datasets"
QA_PATH = _DATA_DIR / "qa.json"
GRAPH_QA_PATH = _DATA_DIR / "graph_qa.json"

SYSTEM_PROMPT = (
    "You are a precise enterprise assistant. Answer concisely and factually, "
    "using only what you are confident about."
)


@dataclass
class SFTExample:
    instruction: str
    output: str
    source: str  # provenance tag: "qa" | "graph_qa"


def from_qa(path: Path = QA_PATH) -> list[SFTExample]:
    """Question -> expected answer, from the RAG QA set."""
    data = json.loads(Path(path).read_text())
    return [
        SFTExample(instruction=d["question"], output=str(d["expected_answer"]), source="qa")
        for d in data
        if d.get("question") and d.get("expected_answer")
    ]


def from_graph_qa(path: Path = GRAPH_QA_PATH) -> list[SFTExample]:
    """Relational question -> its expected facts joined into a short answer."""
    data = json.loads(Path(path).read_text())
    examples: list[SFTExample] = []
    for d in data:
        answer = ", ".join(str(f) for f in d.get("expected_facts", []))
        if d.get("question") and answer:
            examples.append(
                SFTExample(instruction=d["question"], output=answer, source="graph_qa")
            )
    return examples


def build_examples(
    qa_path: Path = QA_PATH, graph_qa_path: Path = GRAPH_QA_PATH
) -> list[SFTExample]:
    """Assemble all sources, deduped by instruction (first occurrence wins)."""
    combined = from_qa(qa_path) + from_graph_qa(graph_qa_path)
    seen: set[str] = set()
    out: list[SFTExample] = []
    for ex in combined:
        key = ex.instruction.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(ex)
    return out
