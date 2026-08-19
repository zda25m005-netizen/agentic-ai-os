"""Topological ordering + cycle detection over a task DAG (Kahn's algorithm).

Pure graph algorithms over the mission's tasks. A cycle is a runtime guard: the
planner sanitizes to backward-only deps, but persisted edits could introduce one,
so the runtime must refuse to execute a cyclic graph rather than loop forever.
"""
from __future__ import annotations

from app.missions.models import Task


class CycleError(Exception):
    """Raised when the task graph contains a dependency cycle."""


def _index(tasks: list[Task]) -> dict[int, Task]:
    return {t.id: t for t in tasks}


def topological_order(tasks: list[Task]) -> list[int]:
    """Return task ids in a valid execution order. Raises CycleError on a cycle.

    Deterministic: ties are broken by ascending id, so the order is stable.
    """
    by_id = _index(tasks)
    indeg: dict[int, int] = {t.id: 0 for t in tasks}
    adj: dict[int, list[int]] = {t.id: [] for t in tasks}
    for t in tasks:
        for d in t.depends_on:
            if d in by_id:  # ignore dangling deps
                adj[d].append(t.id)
                indeg[t.id] += 1

    queue = sorted(i for i, deg in indeg.items() if deg == 0)
    order: list[int] = []
    while queue:
        n = queue.pop(0)
        order.append(n)
        for m in adj[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                queue.append(m)
                queue.sort()

    if len(order) != len(tasks):
        raise CycleError("task graph has a cycle")
    return order


def has_cycle(tasks: list[Task]) -> bool:
    try:
        topological_order(tasks)
        return False
    except CycleError:
        return True
