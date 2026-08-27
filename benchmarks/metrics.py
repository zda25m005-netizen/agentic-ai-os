"""Aggregate per-task benchmark results into reproducible metrics."""
from __future__ import annotations

from benchmarks.harness import TaskResult


def _rate(results: list[TaskResult], attr: str) -> float | None:
    vals = [getattr(r, attr) for r in results if getattr(r, attr) is not None]
    if not vals:
        return None
    return round(sum(1 for v in vals if v) / len(vals), 4)


def _mean(results: list[TaskResult], attr: str) -> float:
    if not results:
        return 0.0
    return round(sum(getattr(r, attr) for r in results) / len(results), 6)


def aggregate(results: list[TaskResult]) -> dict:
    had_fault = [r for r in results if r.had_fault]
    recovery = (
        round(sum(1 for r in had_fault if r.recovered) / len(had_fault), 4)
        if had_fault else None
    )
    by_cat: dict[str, list[bool]] = {}
    for r in results:
        by_cat.setdefault(r.category, []).append(r.success)

    return {
        "n_tasks": len(results),
        "task_success_rate": _rate(results, "success"),
        "recovery_rate": recovery,
        "tool_selection_accuracy": _rate(results, "tool_correct"),
        "memory_retrieval_rate": _rate(results, "memory_hit"),
        "safety_block_rate": _rate(results, "safe_blocked"),
        "planning_validity": _rate(results, "planning_valid"),
        "human_intervention_rate": _rate(results, "intervention"),
        "avg_latency_s": _mean(results, "latency_s"),
        "avg_cost_usd": _mean(results, "cost_usd"),
        "success_by_category": {
            c: round(sum(1 for s in v if s) / len(v), 4) for c, v in by_cat.items()
        },
    }
