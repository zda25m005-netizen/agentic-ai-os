"""MemGPT context controller: budget, advisory framing, eviction."""

import app.memory.store as ms
from app.memory.context import ContextController
from app.memory.orchestrator import MemoryOrchestrator


def _orch(tmp_path):
    ms.DB_PATH = tmp_path / "m.db"
    return MemoryOrchestrator(owner="ctx")


def test_context_respects_budget_and_is_advisory(tmp_path):
    o = _orch(tmp_path)
    for i in range(30):
        o.remember(f"durable fact about topic alpha number {i} " + "x" * 40, memory_type="semantic")
    ctx = ContextController(o, token_budget=60).build("topic alpha")
    assert ctx["tokens"] <= 60
    assert "advisory" in ctx["context"].lower()
    assert ctx["utilization"] <= 1.0


def test_working_notes_included(tmp_path):
    o = _orch(tmp_path)
    o.remember("User studies computer vision.", memory_type="semantic")
    ctx = ContextController(o, token_budget=400).build(
        "computer vision", working_notes=["planned 2 steps", "recalled context"]
    )
    assert "[working]" in ctx["context"] and "computer vision" in ctx["context"].lower()


def test_empty_when_no_memory(tmp_path):
    o = _orch(tmp_path)
    ctx = ContextController(o, token_budget=200).build("anything")
    assert ctx["context"] == "" and ctx["count"] == 0
