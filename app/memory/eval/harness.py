"""Run the memory eval fixtures against a MemoryOrchestrator config."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from app.memory import store as mem_store
from app.memory.eval import metrics
from app.memory.eval.dataset import SCENARIOS
from app.memory.orchestrator import MemoryOrchestrator


def _run_one(scenario: dict, retrieve_enabled: bool, token_budget: int | None) -> dict:
    owner = f"eval-{uuid.uuid4().hex[:8]}"
    orch = MemoryOrchestrator(owner=owner)
    for m in scenario.get("seed", []):
        orch.remember(
            m["content"],
            memory_type=m.get("layer", "semantic"),
            key=m.get("key"),
            confidence=m.get("confidence", 0.7),
            tags=m.get("tags", []),
        )
    for m in scenario.get("ops", []):
        orch.remember(
            m["content"],
            memory_type=m.get("layer", "semantic"),
            key=m.get("key"),
            confidence=m.get("confidence", 0.7),
        )
    if retrieve_enabled:
        recs, tokens = orch.retrieve(scenario["query"], token_budget=token_budget)
        texts = [r.content for r in recs]
    else:  # no-memory baseline
        texts, tokens = [], 0
    return metrics.score_scenario(scenario, texts, tokens)


def evaluate(config: str = "orchestrator", token_budget: int | None = 400) -> dict:
    """Return machine-readable results for a config.

    config: "no_memory" (baseline) | "orchestrator" (current engine).
    Uses an isolated temp store so eval never touches production data.
    """
    prev = mem_store.DB_PATH
    mem_store.DB_PATH = Path(tempfile.mkdtemp()) / "eval_mem.db"
    try:
        retrieve_enabled = config != "no_memory"
        rows = [_run_one(s, retrieve_enabled, token_budget) for s in SCENARIOS]
        return {"config": config, "rows": rows, "aggregate": metrics.aggregate(rows)}
    finally:
        mem_store.DB_PATH = prev
