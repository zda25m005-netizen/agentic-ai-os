"""Mem0 lifecycle + MemGPT context controller wired into the real LangGraph nodes.

Proves the engine is on the execution path (planner recall + finalize write), that
memory is advisory (current query preserved), and that legacy behavior returns when
no orchestrator is installed.
"""

import app.core.llm as llm_mod
import app.memory.store as ms
from app.agents.graph import finalize_node
from app.agents.planner import planner_node
from app.agents.state import new_state
from app.memory.orchestrator import MemoryOrchestrator, set_orchestrator


def _install(tmp_path):
    ms.DB_PATH = tmp_path / "m.db"
    o = MemoryOrchestrator(owner="me")
    set_orchestrator(o)
    return o


async def test_planner_injects_advisory_context_without_overriding_goal(tmp_path):
    o = _install(tmp_path)
    o.remember("User prefers Switzerland for a PhD.", memory_type="semantic", confidence=0.8)
    captured = {}

    async def fake_chat(messages):
        captured["user"] = messages[1]["content"]
        return '[{"description": "search german phd portals", "agent": "research"}]'

    orig = llm_mod.chat
    llm_mod.chat = fake_chat
    try:
        update = await planner_node(new_state("Find funded PhD positions in Germany"))
    finally:
        llm_mod.chat = orig
        set_orchestrator(None)

    # controller wired: a recall note was added
    assert any("recalled" in m["content"] for m in update["scratchpad"] if m["node"] == "planner")
    # current query preserved (goal unchanged), memory only advisory
    assert "Goal: Find funded PhD positions in Germany" in captured["user"]
    assert "advisory" in captured["user"].lower()
    assert len(update["plan"]) == 1


async def test_finalize_runs_mem0_lifecycle(tmp_path):
    _install(tmp_path)
    try:
        state = new_state("What are the user's research interests?")
        state["results"] = ["The user is interested in reinforcement learning for robotics."]
        update = await finalize_node(state)
    finally:
        set_orchestrator(None)

    assert any("memory lifecycle" in m["content"] for m in update["scratchpad"])
    # an episodic run log + an extracted durable candidate were persisted
    allr = ms.query("me", include_archived=True)
    assert any(r.memory_type == "episodic" for r in allr)
    assert any("reinforcement learning" in r.content.lower() for r in allr)


async def test_no_orchestrator_uses_legacy_path(tmp_path):
    set_orchestrator(None)  # ensure legacy fallback

    async def fake_chat(messages):
        return '[{"description": "a", "agent": "research"}]'

    orig = llm_mod.chat
    llm_mod.chat = fake_chat
    try:
        update = await planner_node(new_state("some goal"))
    finally:
        llm_mod.chat = orig
    # legacy path: no orchestrator, no memory manager set -> no recall note, plan still built
    assert len(update["plan"]) == 1
    assert not any("advisory" in m["content"].lower() for m in update["scratchpad"])
