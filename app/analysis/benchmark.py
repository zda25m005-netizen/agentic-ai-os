"""Evidence-first benchmark dataset (Phase 14).

A small, deterministic corpus of missions with pre-collected research text (each
carrying real source URLs) across categories — research, comparison, technical,
numerical. It runs offline (no network/LLM) so the pipeline and the ablation are
fully reproducible. Each item's `results` mimic what the research agent would
have gathered; the pipeline then does the evidence work over them.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.missions.models import Mission, Task
from app.missions.state import MissionStatus, TaskStatus


@dataclass
class BenchmarkItem:
    id: str
    category: str
    objective: str
    results: list[tuple[str, str]] = field(default_factory=list)  # (task_desc, result_text)

    def mission(self) -> Mission:
        return Mission(id=0, objective=self.objective, status=MissionStatus.COMPLETED,
                       priority=0, deadline=None, created_at=0.0, updated_at=0.0, meta={})

    def tasks(self) -> list[Task]:
        return [Task(id=i + 1, mission_id=0, description=d, status=TaskStatus.DONE,
                     depends_on=[], result=r, created_at=0.0, updated_at=0.0)
                for i, (d, r) in enumerate(self.results)]


_A = "https://arxiv.org/abs/2005.11401"
_W = "https://en.wikipedia.org/wiki/Retrieval-augmented_generation"
_WF = "https://en.wikipedia.org/wiki/Fine-tuning_(deep_learning)"

DATASET: list[BenchmarkItem] = [
    BenchmarkItem(
        "research-1", "research", "Explain retrieval-augmented generation for LLM agents",
        [("RAG", "Retrieval-augmented generation fetches external documents at query time. "
          f"It grounds answers in retrieved passages. Sources:\n{_A}\n{_W}")],
    ),
    BenchmarkItem(
        "comparison-1", "comparison", "Compare Vector Retrieval (RAG) vs Fine-Tuning",
        [("RAG", "Vector retrieval keeps knowledge fresh without retraining. "
          f"It retrieves relevant documents at query time. Sources:\n{_A}\n{_W}"),
         ("Fine-Tuning", "Fine-tuning bakes knowledge into model weights. "
          f"Fine-tuning is costly to update. Sources:\n{_WF}")],
    ),
    BenchmarkItem(
        "technical-1", "technical", "Analyze failure modes of vector retrieval architectures",
        [("Retrieval", "Stale embeddings degrade retrieval accuracy over time. "
          f"Chunk-boundary errors split relevant context. Sources:\n{_A}")],
    ),
    BenchmarkItem(
        "numerical-1", "numerical", "Compare retrieval and fine-tuning update latency",
        [("Retrieval", "Retrieval latency 120 ms was reported for the index. "
          f"The system keeps knowledge fresh. Sources:\n{_W}"),
         ("Fine-Tuning", "Fine-tuning update latency 5 ms at inference was reported. "
          f"Weight updates take hours. Sources:\n{_WF}")],
    ),
]


def load_dataset() -> list[BenchmarkItem]:
    return list(DATASET)
