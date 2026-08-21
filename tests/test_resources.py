"""Resource manager: budget accounting and the downgrade/terminate policy."""
from app.missions.resources import (
    Budget,
    BudgetStatus,
    ResourceManager,
    budget_from_meta,
)

T0 = 1_000_000.0


def mgr(budget: Budget) -> ResourceManager:
    return ResourceManager(budget=budget, started_at=T0)


def test_no_budget_is_always_ok():
    m = ResourceManager(started_at=T0)
    m.record(usd=1000, tokens=10**9)
    assert m.utilization(now=T0) == 0.0
    assert m.evaluate(now=T0) == BudgetStatus.OK


def test_under_soft_threshold_is_ok():
    m = mgr(Budget(max_usd=1.0))
    m.record(usd=0.5)
    assert m.evaluate(now=T0) == BudgetStatus.OK


def test_soft_threshold_triggers_downgrade():
    m = mgr(Budget(max_usd=1.0))
    m.record(usd=0.85)  # 85% > default soft 0.8
    assert m.evaluate(now=T0) == BudgetStatus.DOWNGRADE


def test_exhausted_budget_terminates():
    m = mgr(Budget(max_tokens=1000))
    m.record(tokens=1000)
    assert m.evaluate(now=T0) == BudgetStatus.TERMINATE
    assert m.exceeded(now=T0) is True


def test_tightest_dimension_governs():
    # usd fine, but tool_calls exhausted -> terminate
    m = mgr(Budget(max_usd=10.0, max_tool_calls=2))
    m.record(usd=1.0, tool_calls=2)
    assert m.evaluate(now=T0) == BudgetStatus.TERMINATE


def test_time_budget_uses_elapsed():
    m = mgr(Budget(max_seconds=100))
    assert m.evaluate(now=T0 + 50) == BudgetStatus.OK
    assert m.evaluate(now=T0 + 90) == BudgetStatus.DOWNGRADE  # 90%
    assert m.evaluate(now=T0 + 100) == BudgetStatus.TERMINATE


def test_record_accumulates():
    m = mgr(Budget(max_llm_calls=10))
    m.record(llm_calls=3)
    m.record(llm_calls=4)
    assert m.usage.llm_calls == 7
    assert m.utilization(now=T0) == 0.7


def test_remaining_reports_headroom_and_unbounded():
    m = mgr(Budget(max_usd=2.0))
    m.record(usd=0.5)
    rem = m.remaining(now=T0)
    assert rem["usd"] == 1.5
    assert rem["tokens"] is None  # unbounded dimension


def test_budget_from_meta_parses_spec():
    b = budget_from_meta({"budget": {"max_usd": 5.0, "max_tool_calls": 20}})
    assert b.max_usd == 5.0
    assert b.max_tool_calls == 20
    assert b.max_tokens is None


def test_budget_from_meta_handles_missing():
    assert budget_from_meta(None) == Budget()
    assert budget_from_meta({}) == Budget()
