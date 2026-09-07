"""Graph memory (config E) tests.

Driven entirely with a fake Neo4j driver and a fake entity extractor, so the
owner-scoped ingest + retrieval and the graceful-degradation path are verified
end-to-end without a live graph database (mirrors tests/test_graph_retrieval.py).
"""

import pytest

from app.graph.schema import Entity, GraphExtraction, Relation
from app.memory.graph_memory import GraphMemory


class FakeRecord:
    def __init__(self, d):
        self._d = d

    def data(self):
        return self._d


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def __iter__(self):
        return iter(FakeRecord(r) for r in self._rows)


class FakeSession:
    def __init__(self, rows):
        self._rows = rows
        self.calls = []

    def run(self, cypher, params=None):
        self.calls.append((cypher, params or {}))
        # answer the connectivity probe truthfully; canned rows for everything else
        if "RETURN 1" in cypher:
            return FakeResult([{"ok": 1}])
        return FakeResult(self._rows)

    def close(self):
        pass


class FakeDriver:
    """A reachable Neo4j: connectivity passes; records every statement run."""

    def __init__(self, rows=None):
        self._rows = rows or []
        self.sessions = []

    def session(self, database=None):
        s = FakeSession(self._rows)
        self.sessions.append(s)
        return s

    def close(self):
        pass


class DeadDriver:
    def session(self, database=None):
        raise RuntimeError("no neo4j")

    def close(self):
        pass


async def _extract_one(query):
    return [Entity(name="Germany", type="Place")]


# --- availability / graceful degradation ---------------------------------


def test_unavailable_when_driver_dead():
    assert GraphMemory(owner="me", driver=DeadDriver()).available() is False


def test_available_when_driver_reachable():
    assert GraphMemory(owner="me", driver=FakeDriver()).available() is True


@pytest.mark.asyncio
async def test_ingest_is_noop_when_unavailable():
    gm = GraphMemory(owner="me", driver=DeadDriver())
    assert await gm.ingest_text("The user wants a funded PhD in Germany.") == {
        "entities": 0,
        "relations": 0,
        "ops": 0,
    }


@pytest.mark.asyncio
async def test_related_is_empty_when_unavailable():
    gm = GraphMemory(owner="me", driver=DeadDriver())
    res = await gm.related("PhD in Germany")
    assert res["triples"] == [] and res["context"] == ""


# --- ingest (owner-scoped) -------------------------------------------------


@pytest.mark.asyncio
async def test_ingest_scopes_every_write_to_owner(monkeypatch):
    driver = FakeDriver()
    gm = GraphMemory(owner="alice", driver=driver)

    async def fake_extract_graph(text, chat_fn=None):
        return GraphExtraction(
            entities=[Entity(name="Germany", type="Place"), Entity(name="PhD", type="Concept")],
            relations=[],
        )

    monkeypatch.setattr("app.memory.graph_memory.extract_graph", fake_extract_graph)
    out = await gm.ingest_text("The user wants a funded PhD in Germany.")

    assert out["entities"] == 2 and out["ops"] == 2
    entity_writes = [(cy, p) for s in driver.sessions for cy, p in s.calls if "MemEntity" in cy]
    assert entity_writes, "expected owner-scoped MemEntity writes"
    assert all(p.get("owner") == "alice" for _, p in entity_writes)


@pytest.mark.asyncio
async def test_ingest_writes_relations_scoped(monkeypatch):
    driver = FakeDriver()
    gm = GraphMemory(owner="me", driver=driver)

    async def fake_extract_graph(text, chat_fn=None):
        return GraphExtraction(
            entities=[Entity(name="Ada", type="Person"), Entity(name="Analytical Engine")],
            relations=[Relation(subject="Ada", predicate="worked on", object="Analytical Engine")],
        )

    monkeypatch.setattr("app.memory.graph_memory.extract_graph", fake_extract_graph)
    out = await gm.ingest_text("Ada worked on the Analytical Engine.")
    assert out["relations"] == 1
    rel_writes = [(cy, p) for s in driver.sessions for cy, p in s.calls if "MEM_RELATION" in cy]
    assert rel_writes and all(p.get("owner") == "me" for _, p in rel_writes)


# --- retrieval -------------------------------------------------------------


@pytest.mark.asyncio
async def test_related_returns_owner_scoped_triples():
    rows = [
        {"subject": "Germany", "predicate": "hosts", "object": "PhD"},
        {"subject": "PhD", "predicate": "funded_by", "object": "DAAD"},
    ]
    driver = FakeDriver(rows=rows)
    gm = GraphMemory(owner="me", driver=driver)

    res = await gm.related("PhD in Germany", extract_fn=_extract_one)
    assert len(res["triples"]) == 2
    assert "Germany —[hosts]→ PhD" in res["text"]
    assert "advisory" in res["context"].lower()
    query_calls = [c for s in driver.sessions for c in s.calls if "MEM_RELATION" in c[0]]
    assert query_calls and query_calls[0][1].get("owner") == "me"


@pytest.mark.asyncio
async def test_related_empty_when_no_seed_entities():
    async def _none(query):
        return []

    gm = GraphMemory(owner="me", driver=FakeDriver(rows=[{"subject": "a", "object": "b"}]))
    res = await gm.related("something with no known entities", extract_fn=_none)
    assert res["triples"] == []
