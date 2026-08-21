"""Model router: pick the model tier for a task, maximizing quality under limits.

Different steps deserve different models — a cheap model can run an executor step,
but analysis or planning wants the strongest one. The router maps a task's role to
a preferred **tier**, then returns the **highest-quality model that still fits the
cost and latency constraints**. When the resource manager signals `DOWNGRADE`
(budget getting tight), the router drops one tier — that's where the budget policy
gets teeth.

The catalog below uses **relative, illustrative** quality/cost/latency numbers for
three generic tiers; they're meant to be overridden with real per-deployment
figures, not treated as vendor benchmarks. Selection is deterministic.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.missions.resources import BudgetStatus


@dataclass(frozen=True)
class ModelSpec:
    name: str
    tier: int          # 1 = small/cheap … 3 = frontier/best
    quality: float     # relative quality (0–1)
    usd_per_1k: float  # blended $ per 1k tokens
    latency_ms: int    # typical
    context: int


# Illustrative, configurable — replace with real figures per deployment.
DEFAULT_CATALOG: list[ModelSpec] = [
    ModelSpec("fast", tier=1, quality=0.62, usd_per_1k=0.0004, latency_ms=400, context=128_000),
    ModelSpec("balanced", tier=2, quality=0.81, usd_per_1k=0.003, latency_ms=900, context=200_000),
    ModelSpec("frontier", tier=3, quality=1.00, usd_per_1k=0.012, latency_ms=1800, context=200_000),
]

# Preferred tier per task role (see mission_planner.ROLES + planner/critic steps).
TASK_TIER: dict[str, int] = {
    "executor": 1,
    "researcher": 2,
    "analyst": 3,
    "planner": 3,
    "critic": 3,
}
DEFAULT_TIER = 2


def route(
    task_type: str,
    *,
    downgrade: bool = False,
    max_usd_per_1k: float | None = None,
    max_latency_ms: int | None = None,
    catalog: list[ModelSpec] | None = None,
) -> ModelSpec:
    """Return the best model for `task_type` under the given constraints.

    Picks the highest-quality model at or below the task's preferred tier that
    satisfies the cost/latency limits. `downgrade=True` lowers the target tier by
    one. If nothing fits the constraints, degrades gracefully to the cheapest
    model rather than failing.
    """
    catalog = catalog or DEFAULT_CATALOG
    target = TASK_TIER.get(task_type, DEFAULT_TIER)
    if downgrade:
        target = max(1, target - 1)

    candidates = [m for m in catalog if m.tier <= target] or list(catalog)

    def within_limits(m: ModelSpec) -> bool:
        if max_usd_per_1k is not None and m.usd_per_1k > max_usd_per_1k:
            return False
        if max_latency_ms is not None and m.latency_ms > max_latency_ms:
            return False
        return True

    affordable = [m for m in candidates if within_limits(m)]
    if affordable:
        # maximize quality; break ties toward the cheaper model
        return max(affordable, key=lambda m: (m.quality, -m.usd_per_1k))
    # nothing satisfies the constraints -> cheapest available (graceful degrade)
    return min(catalog, key=lambda m: m.usd_per_1k)


def route_for(
    task_type: str,
    status: BudgetStatus = BudgetStatus.OK,
    **constraints: float | int | None,
) -> ModelSpec:
    """Route with the resource manager's decision folded in.

    `DOWNGRADE` lowers the tier; `OK` routes normally. (`TERMINATE` is handled by
    the runtime, which stops the mission before routing.)
    """
    return route(task_type, downgrade=(status == BudgetStatus.DOWNGRADE), **constraints)
