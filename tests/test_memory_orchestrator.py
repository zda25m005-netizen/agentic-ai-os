"""MemoryOrchestrator: resolution, retrieval budget, lifecycle, guarantees."""

import app.memory.store as mem_store
from app.memory.orchestrator import MemoryOrchestrator


def _orch(tmp_path, name="m.db"):
    mem_store.DB_PATH = tmp_path / name
    return MemoryOrchestrator(owner="tester")


def test_add_noop_supersede_additive(tmp_path):
    o = _orch(tmp_path)
    assert o.remember("Switzerland", key="pref", confidence=0.7)["operation"] == "ADD"
    assert o.remember("Switzerland", key="pref", confidence=0.7)["operation"] == "NOOP"
    # lower-confidence differing value is kept alongside (no blind overwrite)
    assert o.remember("Norway", key="pref", confidence=0.5)["operation"] == "ADD"
    # explicit higher-confidence correction supersedes prior key value(s)
    res = o.remember("Germany", key="pref", confidence=0.9)
    assert res["operation"] == "UPDATE" and res["superseded"]


def test_no_blind_overwrite_keeps_history(tmp_path):
    o = _orch(tmp_path)
    o.remember("Switzerland", key="pref", confidence=0.7)
    o.remember("Germany", key="pref", confidence=0.9)
    current = [r.content for r in o.retrieve("pref")[0]]
    assert "Germany" in current and "Switzerland" not in current  # superseded not current
    # but history is retained (queryable)
    allr = mem_store.query("tester", include_archived=True)
    assert any(r.content == "Switzerland" and r.status == "superseded" for r in allr)


def test_temporal_update_no_stale(tmp_path):
    o = _orch(tmp_path)
    o.remember("First choice Switzerland", key="country", confidence=0.7)
    o.remember("First choice Germany", key="country", confidence=0.9)
    recs, _ = o.retrieve("country preference")
    joined = " ".join(r.content for r in recs)
    assert "Germany" in joined and "Switzerland" not in joined


def test_retrieval_within_token_budget(tmp_path):
    o = _orch(tmp_path)
    for i in range(20):
        o.remember("some memory content number " + str(i) * 5, memory_type="semantic")
    recs, tokens = o.retrieve("memory content", token_budget=30)
    assert tokens <= 30 and len(recs) < 20  # budget guard prevents overflow


def test_build_context_is_advisory(tmp_path):
    o = _orch(tmp_path)
    o.remember("User prefers Switzerland", key="pref", confidence=0.8)
    ctx = o.build_context("phd", token_budget=200)
    assert "advisory" in ctx["context"].lower()
    assert "current request takes precedence" in ctx["context"].lower()


def test_forget_restore_and_stats(tmp_path):
    o = _orch(tmp_path)
    r = o.remember("temp note", memory_type="working")["record"]
    assert o.forget(r.id) is True
    assert all(x.id != r.id for x in o.retrieve("temp")[0])  # archived hidden
    assert o.restore(r.id) is not None
    assert any(x.id == r.id for x in o.retrieve("temp")[0])  # back
    s = o.stats()
    assert s["layers"]["working"] >= 1 and "total" in s


def test_owner_isolation(tmp_path):
    mem_store.DB_PATH = tmp_path / "iso.db"
    a = MemoryOrchestrator(owner="alice")
    b = MemoryOrchestrator(owner="bob")
    a.remember("alice secret", memory_type="semantic")
    assert a.retrieve("secret")[0] and not b.retrieve("secret")[0]
