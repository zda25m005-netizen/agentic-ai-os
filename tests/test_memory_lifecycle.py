"""Mem0 lifecycle: extraction filtering + retrieve-similar resolver."""

import app.memory.store as ms
from app.memory.lifecycle import extract_candidates, resolve_and_ingest
from app.memory.orchestrator import MemoryOrchestrator


def _orch(tmp_path):
    ms.DB_PATH = tmp_path / "m.db"
    return MemoryOrchestrator(owner="lc")


def test_extract_filters_noise():
    c = extract_candidates("I prefer Switzerland for my PhD. The weather is nice today.")
    contents = [x["content"] for x in c]
    assert any("Switzerland" in t for t in contents)
    assert not any("weather" in t.lower() for t in contents)  # non-durable noise dropped


def test_duplicate_is_noop(tmp_path):
    o = _orch(tmp_path)
    a = resolve_and_ingest(o, extract_candidates("User is interested in reinforcement learning."))
    b = resolve_and_ingest(o, extract_candidates("User is interested in reinforcement learning."))
    assert a["ops"]["ADD"] == 1 and b["ops"]["NOOP"] == 1


def test_explicit_correction_supersedes(tmp_path):
    o = _orch(tmp_path)
    resolve_and_ingest(o, extract_candidates("First-choice country is Switzerland."))
    r = resolve_and_ingest(o, extract_candidates("First-choice country is now Germany."))
    assert r["ops"]["UPDATE"] == 1
    current = " ".join(x.content for x in o.retrieve("country")[0])
    assert "Germany" in current and "Switzerland" not in current
    # history retained
    allr = ms.query("lc", include_archived=True)
    assert any("Switzerland" in x.content and x.status == "superseded" for x in allr)


def test_additive_kept(tmp_path):
    o = _orch(tmp_path)
    resolve_and_ingest(o, extract_candidates("Prefers Switzerland for a PhD."))
    r = resolve_and_ingest(o, extract_candidates("Also considering Norway for a PhD."))
    assert r["ops"]["ADD"] == 1  # additive, not a correction
    current = " ".join(x.content for x in o.retrieve("phd")[0])
    assert "Switzerland" in current and "Norway" in current
