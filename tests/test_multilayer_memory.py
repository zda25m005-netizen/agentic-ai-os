"""Multi-layer memory: per-layer behavior + unified retrieval."""
from app.memory.multilayer import MemoryType, MultiLayerMemory


def test_working_memory_is_capacity_bounded():
    m = MultiLayerMemory()
    m.working.capacity = 3
    for i in range(5):
        m.working.note(f"thought {i}")
    recent = m.working.recent()
    assert len(recent) == 3  # oldest two evicted
    assert [r.content for r in recent] == ["thought 2", "thought 3", "thought 4"]


def test_episodic_records_in_time_order():
    m = MultiLayerMemory()
    m.episodic.record("planned the mission")
    m.episodic.record("executed step 1")
    assert [e.content for e in m.episodic.recent()] == [
        "planned the mission", "executed step 1"]


def test_semantic_learn_is_keyed_and_updates():
    m = MultiLayerMemory()
    m.semantic.learn("capital_of_france", "Paris")
    m.semantic.learn("capital_of_france", "Paris, France")  # update, not duplicate
    assert m.semantic.get("capital_of_france") == "Paris, France"
    assert len(m.semantic) == 1


def test_procedural_stores_named_steps():
    m = MultiLayerMemory()
    m.procedural.learn("deploy", ["build image", "push", "helm upgrade"])
    assert m.procedural.get("deploy") == "build image -> push -> helm upgrade"


def test_organizational_is_shared_knowledge():
    m = MultiLayerMemory()
    m.organizational.share("Company X reports earnings quarterly", tags=("finance",))
    hits = m.organizational.search("earnings")
    assert len(hits) == 1 and hits[0].type == MemoryType.ORGANIZATIONAL


def test_retrieve_spans_all_layers_ranked_by_importance():
    m = MultiLayerMemory()
    m.working.note("checking anomaly in transactions")
    m.episodic.record("anomaly flagged last run", importance=2.0)
    m.semantic.learn("anomaly_def", "an anomaly is an outlier transaction", importance=3.0)
    m.organizational.share("anomaly policy: escalate over $10k", importance=0.5)

    hits = m.retrieve("anomaly", limit=4)
    assert len(hits) == 4
    # highest importance first
    assert hits[0].importance >= hits[1].importance >= hits[2].importance
    assert hits[0].type == MemoryType.SEMANTIC


def test_search_matches_content_key_and_tags():
    m = MultiLayerMemory()
    m.semantic.learn("neo4j", "graph database")   # match by key
    m.organizational.share("use RRF for fusion", tags=("retrieval",))  # match by tag
    assert m.semantic.search("neo4j")
    assert m.organizational.search("retrieval")


def test_format_context_and_snapshot():
    m = MultiLayerMemory()
    m.working.note("a")
    m.episodic.record("b")
    m.semantic.learn("k", "c")
    snap = m.snapshot()
    assert snap["working"] == 1 and snap["episodic"] == 1 and snap["semantic"] == 1
    ctx = m.format_context(m.retrieve("c"))
    assert "semantic" in ctx or "Relevant memory" in ctx
