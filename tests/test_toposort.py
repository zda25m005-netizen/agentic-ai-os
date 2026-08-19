"""Topological order + cycle detection over the task DAG (pure, no DB)."""
import pytest

from app.missions.models import Task
from app.missions.state import TaskStatus
from app.missions.toposort import CycleError, has_cycle, topological_order


def mk(tid: int, deps: list[int], status=TaskStatus.PENDING) -> Task:
    return Task(id=tid, mission_id=1, description=f"t{tid}", status=status,
                depends_on=deps, result=None, created_at=0.0, updated_at=0.0)


def test_topological_order_respects_dependencies():
    # 1 -> 2 -> 3, plus 1 -> 3 (diamond-ish)
    tasks = [mk(3, [1, 2]), mk(2, [1]), mk(1, [])]
    order = topological_order(tasks)
    assert order.index(1) < order.index(2) < order.index(3)
    assert order.index(1) < order.index(3)


def test_topological_order_is_deterministic():
    # two independent roots -> ascending id tie-break
    tasks = [mk(2, []), mk(1, []), mk(3, [1, 2])]
    assert topological_order(tasks) == [1, 2, 3]


def test_topological_order_raises_on_cycle():
    tasks = [mk(1, [2]), mk(2, [1])]  # mutual dependency
    with pytest.raises(CycleError):
        topological_order(tasks)


def test_has_cycle_detects_self_loop():
    assert has_cycle([mk(1, [1])]) is True
    assert has_cycle([mk(1, []), mk(2, [1])]) is False


def test_dangling_dependency_is_ignored():
    # depends on 99 which does not exist -> treated as no edge, still orderable
    assert topological_order([mk(1, [99])]) == [1]
