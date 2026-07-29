import pytest

from app.memory.episodic import EpisodicMemory
from app.memory.manager import MemoryManager, get_memory, set_memory
from app.memory.semantic import MemoryHit, SemanticMemory
from app.rag import embeddings, vectorstore


@pytest.fixture
def client():
    return vectorstore.get_client(location=":memory:")


@pytest.fixture(autouse=True)
def fake_embeddings(monkeypatch):
    async def fake_embed(texts):
        return [[float(len(t) % 13), float(len(t) % 5), 1.0] for t in texts]

    monkeypatch.setattr(embeddings, "embed", fake_embed)


async def test_recall_empty_when_nothing_stored(client):
    mem = SemanticMemory(client)
    assert await mem.recall("anything") == []


async def test_add_then_recall(client):
    mem = SemanticMemory(client)
    await mem.add("summarize the Q3 report", "revenue grew 12%")
    hits = await mem.recall("summarize the Q3 report", limit=1)
    assert hits
    assert isinstance(hits[0], MemoryHit)
    assert hits[0].goal == "summarize the Q3 report"
    assert hits[0].answer == "revenue grew 12%"


async def test_recall_empty_query(client):
    mem = SemanticMemory(client)
    await mem.add("g", "a")
    assert await mem.recall("   ") == []


async def test_manager_remember_writes_both(client):
    manager = MemoryManager(EpisodicMemory.open(":memory:"), SemanticMemory(client))
    await manager.remember("do a task", "task done")

    assert manager.episodic.count() == 1
    assert await manager.recall("do a task")


def test_format_recall():
    hits = [MemoryHit(goal="g1", answer="a1", score=0.9)]
    out = MemoryManager.format_recall(hits)
    assert "Relevant past work" in out
    assert "g1 -> a1" in out
    assert MemoryManager.format_recall([]) == ""


def test_default_memory_get_set():
    assert get_memory() is None
    sentinel = object()
    set_memory(sentinel)  # type: ignore[arg-type]
    try:
        assert get_memory() is sentinel
    finally:
        set_memory(None)
