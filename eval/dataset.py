"""Labeled evaluation dataset: a small corpus + gold Q&A pairs.

The corpus is ingested into a vector store; each Q&A item names the answer
we expect and the source document it should come from. Day 20's scorers
compare the system's retrieval and answers against these labels.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

_DATA_DIR = Path(__file__).parent / "datasets"
CORPUS_PATH = _DATA_DIR / "corpus.json"
QA_PATH = _DATA_DIR / "qa.json"


@dataclass(frozen=True)
class CorpusDoc:
    """One document in the evaluation corpus."""

    source: str
    text: str


@dataclass(frozen=True)
class QAItem:
    """A gold question with its expected answer and source document."""

    id: str
    question: str
    expected_answer: str
    expected_source: str


def load_corpus(path: Path = CORPUS_PATH) -> list[CorpusDoc]:
    data = json.loads(Path(path).read_text())
    return [CorpusDoc(source=d["source"], text=d["text"]) for d in data]


def load_qa(path: Path = QA_PATH) -> list[QAItem]:
    data = json.loads(Path(path).read_text())
    return [
        QAItem(
            id=d["id"],
            question=d["question"],
            expected_answer=d["expected_answer"],
            expected_source=d["expected_source"],
        )
        for d in data
    ]


def validate(qa: list[QAItem], corpus: list[CorpusDoc]) -> None:
    """Ensure every Q&A item references a source that exists in the corpus.

    Raises ValueError on any dangling reference or duplicate id.
    """
    sources = {d.source for d in corpus}
    ids: set[str] = set()
    for item in qa:
        if item.id in ids:
            raise ValueError(f"duplicate QA id: {item.id}")
        ids.add(item.id)
        if item.expected_source not in sources:
            raise ValueError(
                f"{item.id}: expected_source '{item.expected_source}' not in corpus"
            )
