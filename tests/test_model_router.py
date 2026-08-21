"""Model router: tier per role, downgrade, cost/latency limits, graceful fallback."""
from app.missions.model_router import (
    DEFAULT_CATALOG,
    route,
    route_for,
)
from app.missions.resources import BudgetStatus


def test_analyst_gets_the_frontier_model():
    assert route("analyst").name == "frontier"


def test_executor_gets_the_cheap_model():
    assert route("executor").name == "fast"


def test_unknown_role_uses_default_tier():
    # default tier 2 -> best model at or below tier 2 is "balanced"
    assert route("mystery").name == "balanced"


def test_downgrade_drops_one_tier():
    assert route("analyst").name == "frontier"
    assert route("analyst", downgrade=True).name == "balanced"


def test_cost_limit_forces_cheaper_model():
    # analyst wants frontier ($0.012); cap at $0.005 -> balanced ($0.003)
    assert route("analyst", max_usd_per_1k=0.005).name == "balanced"


def test_latency_limit_forces_faster_model():
    # cap latency below balanced's 900ms -> only "fast" qualifies
    assert route("analyst", max_latency_ms=500).name == "fast"


def test_graceful_fallback_when_nothing_fits():
    # impossible cost cap -> cheapest model, not an error
    assert route("analyst", max_usd_per_1k=0.00001).name == "fast"


def test_route_for_downgrade_status():
    assert route_for("analyst", BudgetStatus.OK).name == "frontier"
    assert route_for("analyst", BudgetStatus.DOWNGRADE).name == "balanced"


def test_maximizes_quality_within_tier():
    best = route("planner")  # tier 3 -> highest quality in catalog
    assert best.quality == max(m.quality for m in DEFAULT_CATALOG)


def test_selection_is_deterministic():
    assert route("researcher").name == route("researcher").name == "balanced"
