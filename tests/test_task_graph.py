"""Ready-set, completion, blocked, and progress over the task DAG (pure)."""
import pytest

from app.missions.models import Task
from app.missions.state import TaskStatus
from app.missions.task_graph import is_blocked, is_complete, progress, ready_tasks


def mk(tid: int, deps: list[int], status=TaskStatus.PENDING) -> Task:
    return Task(id=tid, mission_id=1, description=f"t{tid}", status=status,
                depends_on=deps, result=None, created_at=0.0, updated_at=0.0)


def test_ready_set_only_roots_at_start():
    tasks = [mk(1, []), mk(2, [1]), mk(3, [2])]
    assert [t.id for t in ready_tasks(tasks)] == [1]


def test_ready_set_advances_as_deps_complete():
    tasks = [mk(1, [], TaskStatus.DONE), mk(2, [1]), mk(3, [1])]
    # both 2 and 3 unblock together once 1 is done
    assert [t.id for t in ready_tasks(tasks)] == [2, 3]


def test_failed_dependency_leaves_dependent_unready():
    tasks = [mk(1, [], TaskStatus.FAILED), mk(2, [1])]
    assert ready_tasks(tasks) == []


def test_running_task_is_not_re_offered():
    tasks = [mk(1, [], TaskStatus.RUNNING), mk(2, [1])]
    assert ready_tasks(tasks) == []


def test_is_complete_only_when_all_settled():
    assert is_complete([mk(1, [], TaskStatus.DONE), mk(2, [], TaskStatus.SKIPPED)])
    assert not is_complete([mk(1, [], TaskStatus.DONE), mk(2, [])])
    assert not is_complete([])  # empty is not "complete"


def test_is_blocked_on_failed_dependency():
    # 1 failed, 2 depends on 1, nothing running -> stuck
    tasks = [mk(1, [], TaskStatus.FAILED), mk(2, [1])]
    assert is_blocked(tasks) is True


def test_not_blocked_while_work_remains():
    assert is_blocked([mk(1, []), mk(2, [1])]) is False          # 1 is ready
    assert is_blocked([mk(1, [], TaskStatus.RUNNING)]) is False  # in progress
    assert is_blocked([mk(1, [], TaskStatus.DONE)]) is False     # complete


def test_progress_counts_settled():
    tasks = [mk(1, [], TaskStatus.DONE), mk(2, [], TaskStatus.FAILED), mk(3, [])]
    assert progress(tasks) == (2, 3)


def test_ready_set_rejects_cycle():
    with pytest.raises(ValueError, match="cyclic"):
        ready_tasks([mk(1, [2]), mk(2, [1])])
