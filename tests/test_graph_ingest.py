"""Graph ingest tests.

`build_ops` is pure, so we assert exact statement counts and shapes. Execution
is checked with a recording fake driver that captures every (cypher, params)
run across sessions — no live Neo4j needed.
"""
from app.graph import ingest
from app.graph.schema import Entity, GraphExtraction, Relation


class RecSession:
    def __init__(self, sink: list):
        self.sink = sink
        self.closed = False

    def run(self, cypher, params):
        self.sink.append((cypher, params))

    def close(self):
        self.closed = True


class RecDriver:
    """Accumulates every statement run through any session it hands out."""

    def __init__(self):
        self.runs: list = []

    def session(self, database=None):
        return RecSession(self.runs)

    def close(self):
        pass


def _extraction():
    return GraphExtraction(
        entities=[Entity(name="Ada Lovelace", type="Person"),
                  Entity(name="Analytical Engine", type="Product")],
        relations=[Relation(subject="Ada Lovelace", predicate="worked on",
                            object="Analytical Engine")],
    )


# --- build_ops (pure) ---

def test_build_ops_with_chunk_links_mentions():
    ops = ingest.build_ops(_extraction(), chunk_id="doc1.pdf")
    # 1 MERGE chunk + 2*(entity + mention) + 1 relation = 6
    assert len(ops) == 6
    cyphers = [c for c, _ in ops]
    assert ingest.MERGE_CHUNK in cyphers
    assert cyphers.count(ingest.MERGE_ENTITY) == 2
    assert cyphers.count(ingest.LINK_MENTION) == 2
    assert ingest.MERGE_RELATION in cyphers


def test_build_ops_without_chunk_skips_mentions():
    ops = ingest.build_ops(_extraction(), chunk_id=None)
    cyphers = [c for c, _ in ops]
    assert ingest.LINK_MENTION not in cyphers
    assert ingest.MERGE_CHUNK not in cyphers
    assert len(ops) == 3  # 2 entities + 1 relation


def test_relation_params_are_wired():
    ops = ingest.build_ops(_extraction(), chunk_id=None)
    rel = next(p for c, p in ops if c == ingest.MERGE_RELATION)
    assert rel == {"subject": "Ada Lovelace", "object": "Analytical Engine",
                   "predicate": "worked on"}


# --- execution ---

def test_ingest_extraction_runs_every_op():
    driver = RecDriver()
    n = ingest.ingest_extraction(_extraction(), chunk_id="doc1", driver=driver)
    assert n == 6
    assert len(driver.runs) == 6


async def test_ingest_documents_aggregates_stats():
    async def fake_extract(_text):
        return _extraction()

    driver = RecDriver()
    docs = [{"source": "a", "text": "..."}, {"source": "b", "text": "..."}]
    stats = await ingest.ingest_documents(docs, extract_fn=fake_extract, driver=driver)
    assert stats.documents == 2
    assert stats.entities == 4
    assert stats.relations == 2
    assert stats.operations == 12  # 6 ops per doc
    assert len(driver.runs) == 12
