"""Graph retrieval tests.

Cypher building and serialization are pure. `get_graph_context` is driven with
a fake entity extractor and a fake driver that returns canned neighborhood rows,
so retrieval is verified end-to-end without a live Neo4j.
"""
from app.graph import ingest, retrieval
from app.graph.schema import Entity


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

    def run(self, cypher, params):
        self.last = (cypher, params)
        return FakeResult(self._rows)

    def close(self):
        pass


class FakeDriver:
    def __init__(self, rows):
        self._rows = rows
        self.session_obj = None

    def session(self, database=None):
        self.session_obj = FakeSession(self._rows)
        return self.session_obj

    def close(self):
        pass


# --- pure builders ---

def test_neighborhood_query_clamps_and_injects_hops():
    assert "RELATION*1..2" in retrieval.neighborhood_query(2)
    assert "RELATION*1..3" in retrieval.neighborhood_query(9)   # clamped to MAX
    assert "RELATION*1..1" in retrieval.neighborhood_query(0)   # clamped up to 1


def test_serialize_triples_dedupes():
    triples = [
        ("Ada Lovelace", "worked on", "Analytical Engine"),
        ("ada lovelace", "worked on", "analytical engine"),  # dup (case-insensitive)
        ("Ada Lovelace", "knew", "Charles Babbage"),
    ]
    text = retrieval.serialize_triples(triples)
    assert text.count("worked on") == 1
    assert "Charles Babbage" in text


# --- end to end retrieval ---

async def test_get_graph_context_returns_triples():
    async def fake_extract(_q):
        return [Entity(name="Ada Lovelace")]

    rows = [
        {"subject": "Ada Lovelace", "predicate": "worked on", "object": "Analytical Engine"},
        {"subject": "Ada Lovelace", "predicate": "knew", "object": "Charles Babbage"},
    ]
    driver = FakeDriver(rows)
    ctx = await retrieval.get_graph_context(
        "What did Ada work on?", driver=driver, hops=2, extract_fn=fake_extract
    )
    assert len(ctx.triples) == 2
    assert "Analytical Engine" in ctx.text
    # seed names passed lowercased for case-insensitive match
    assert driver.session_obj.last[1] == {"names": ["ada lovelace"]}


async def test_get_graph_context_empty_when_no_entities():
    async def fake_extract(_q):
        return []

    ctx = await retrieval.get_graph_context("hello", driver=FakeDriver([]), extract_fn=fake_extract)
    assert ctx.triples == []
    assert ctx.text == ""


# --- schema/perf setup ---

def test_ensure_graph_schema_creates_name_index():
    runs = []

    class Sink:
        def run(self, cypher, params):
            runs.append(cypher)

        def close(self):
            pass

    class D:
        def session(self, database=None):
            return Sink()

        def close(self):
            pass

    n = ingest.ensure_graph_schema(driver=D())
    assert n == 2
    assert any("INDEX entity_name" in c for c in runs)
    assert any("CONSTRAINT" in c for c in runs)
