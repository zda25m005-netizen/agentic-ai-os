"""Integration: memory wired into the agent graph (planner recall + save)."""
import pytest

import app.core.llm as llm_mod
from app.agents.graph import build_graph
from app.agents.state import new_state
from app.memory.episodic import EpisodicMemory
from app.memory.manager import MemoryManager, set_memory
from app.memory.semantic import SemanticMemory
from app.rag import embeddings, vectorstore


@pytest.fixture(autouse=True)
def fake_embeddings(monkeypatch):
    async def fake_embed(texts):
        return [[float(len(t) % 13), 1.0, 0.0] for t in texts]

    monkeypatch.setattr(embeddings, "embed", fake_embed)


@pytest.fixture
def memory():
    client = vectorstore.get_client(location=":memory:")
    mgr = MemoryManager(EpisodicMemory.open(":memory:"), SemanticMemory(client))
    set_memory(mgr)
    try:
        yield mgr
    finally:
        set_memory(None)


def _router(messages, tools=None, temperature=0.2):
    system = messages[0]["content"].lower()

    async def _():
        if "planning agent" in system:
            return {"content": '[{"description": "do it", "agent": "research"}]'}
        if "reviewer" in system:
            return {"content": "APPROVE"}
        return {"content": "final worker output"}

    return _()


async def test_graph_saves_run_to_memory(monkeypatch, memory):
    monkeypatch.setattr(llm_mod, "chat_raw", lambda *a, **k: _router(*a, **k))

    graph = build_graph()
    result = await graph.ainvoke(new_state("summarize the report"))

    assert memory.episodic.count() == 1
    saved = memory.episodic.recent()[0]
    assert saved.goal == "summarize the report"
    assert "final worker output" in saved.answer
    assert any("saved run to memory" in m["content"] for m in result["scratchpad"])


async def test_planner_recalls_prior_run(monkeypatch, memory):
    await memory.remember("summarize the report", "revenue grew 12%")

    monkeypatch.setattr(llm_mod, "chat_raw", lambda *a, **k: _router(*a, **k))
    graph = build_graph()
    result = await graph.ainvoke(new_state("summarize the report"))

    assert any("recalled" in m["content"] for m in result["scratchpad"])
