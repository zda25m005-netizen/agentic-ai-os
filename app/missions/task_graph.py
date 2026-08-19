"""Execution view over a mission's task DAG: ready-set, progress, blocked state.

Pure functions over a list of `Task` — no DB, no I/O — so the runtime tick (Day 4)
and the API can share one source of truth for "what can run now" and "are we
stuck". Cycle detection lives in `toposort`; this module refuses to schedule a
cyclic graph.
"""
from __future__ import annotations

from app.missions.models import Task
from app.missions.state import TaskStatus
from app.missions.toposort import has_cycle

# A task is settled once it can't run again.
_DONE = {TaskStatus.DONE, TaskStatus.SKIPPED}
_TERMINAL = _DONE | {TaskStatus.FAILED}


def _index(tasks: list[Task]) -> dict[int, Task]:
    return {t.id: t for t in tasks}


def ready_tasks(tasks: list[Task]) -> list[Task]:
    """Tasks that can start now: PENDING/READY with every dependency DONE.

    A dependency that FAILED (or is missing) leaves the dependent unready — it
    will surface as a blocked mission, not silently run on incomplete inputs.
    Returned in deterministic id order.
    """
    if has_cycle(tasks):
        raise ValueError("cannot compute ready-set on a cyclic task graph")
    by_id = _index(tasks)
    out = [
        t
        for t in tasks
        if t.status in (TaskStatus.PENDING, TaskStatus.READY)
        and all((dep := by_id.get(d)) is not None and dep.status in _DONE
                for d in t.depends_on)
    ]
    return sorted(out, key=lambda t: t.id)


def is_complete(tasks: list[Task]) -> bool:
    """True when every task is DONE or SKIPPED (nothing left to do)."""
    return bool(tasks) and all(t.status in _DONE for t in tasks)


def is_blocked(tasks: list[Task]) -> bool:
    """Stuck: not complete, nothing running, and nothing can start.

    Typically a failed dependency stranding its dependents. The runtime uses this
    to fail the mission instead of ticking forever with no progress.
    """
    if not tasks or is_complete(tasks):
        return False
    if any(t.status == TaskStatus.RUNNING for t in tasks):
        return False
    return not ready_tasks(tasks)


def progress(tasks: list[Task]) -> tuple[int, int]:
    """(settled, total) where settled = DONE|SKIPPED|FAILED — for UI/telemetry."""
    settled = sum(1 for t in tasks if t.status in _TERMINAL)
    return settled, len(tasks)
