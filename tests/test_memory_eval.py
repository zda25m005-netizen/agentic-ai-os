"""Memory eval harness: computes real metrics; memory beats the no-memory baseline."""

from app.memory.eval.ablation import run
from app.memory.eval.harness import evaluate


def test_orchestrator_beats_no_memory():
    orch = evaluate("orchestrator")["aggregate"]
    base = evaluate("no_memory")["aggregate"]
    assert orch["avg_recall"] > base["avg_recall"]
    assert orch["passed"] > base["passed"]


def test_no_stale_leak_on_temporal_update():
    rows = {r["id"]: r for r in evaluate("orchestrator")["rows"]}
    assert rows["temporal_update"]["stale_leak"] == 0
    assert rows["additive_preferences"]["recall"] == 1.0  # both kept


def test_ablation_runs_D_and_marks_rl_planned():
    abl = run()
    assert abl["status"]["D_lifecycle"] == "implemented"
    assert abl["status"]["F_rl_policy"] == "planned"
    assert "C_orchestrator" in abl["results"] and "D_lifecycle" in abl["results"]
    assert "E_graph" not in abl["results"]  # unbuilt configs report no numbers


def test_lifecycle_config_reduces_irrelevant_leak():
    from app.memory.eval.harness import evaluate

    c = evaluate("orchestrator")["aggregate"]
    d = evaluate("lifecycle")["aggregate"]
    assert d["avg_recall"] == 1.0 and d["total_stale_leak"] == 0
    assert d["total_irrelevant_leak"] <= c["total_irrelevant_leak"]
