"""Self-improving policy engine: promotion, demotion, exploration, persistence."""
from app.missions.policy import Policy, PolicyEngine, Strategy


def test_smoothed_rate_starts_at_half():
    s = Strategy("x")
    assert s.rate == 0.5  # untried -> explored before proven-bad ones


def test_better_candidate_is_promoted():
    eng = PolicyEngine()
    eng.register("recover", ["retry", "alt_tool"])
    for _ in range(10):
        eng.record("recover", "alt_tool", success=True)
        eng.record("recover", "retry", success=False)
    assert eng.select("recover") == "alt_tool"          # winner promoted
    assert eng.ranked("recover") == ["alt_tool", "retry"]


def test_worse_candidate_is_not_selected():
    eng = PolicyEngine()
    eng.register("route", ["cheap", "frontier"])
    for _ in range(8):
        eng.record("route", "cheap", success=False)
        eng.record("route", "frontier", success=True)
    assert eng.select("route") != "cheap"


def test_order_flips_as_evidence_changes():
    eng = PolicyEngine()
    eng.register("ctx", ["a", "b"])
    # a wins early
    for _ in range(5):
        eng.record("ctx", "a", success=True)
        eng.record("ctx", "b", success=False)
    assert eng.select("ctx") == "a"
    # b then strongly outperforms and overtakes
    for _ in range(30):
        eng.record("ctx", "b", success=True)
        eng.record("ctx", "a", success=False)
    assert eng.select("ctx") == "b"


def test_untried_strategy_explored_over_proven_bad():
    p = Policy("c", [Strategy("bad", successes=0, attempts=10),
                     Strategy("new", successes=0, attempts=0)])
    assert p.best().name == "new"  # new (0.5) beats bad (~0.08)


def test_single_fluke_does_not_flip_order():
    eng = PolicyEngine()
    eng.register("c", ["a", "b"])
    for _ in range(20):
        eng.record("c", "a", success=True)
    eng.record("c", "b", success=True)   # one lucky win for b
    assert eng.select("c") == "a"        # a's track record still wins


def test_select_unknown_context_is_none():
    assert PolicyEngine().select("nope") is None


def test_roundtrip_serialization():
    eng = PolicyEngine()
    eng.register("c", ["a", "b"])
    eng.record("c", "a", success=True)
    eng.record("c", "b", success=False)
    restored = PolicyEngine.from_dict(eng.to_dict())
    assert restored.ranked("c") == eng.ranked("c")
    assert restored.snapshot() == eng.snapshot()
