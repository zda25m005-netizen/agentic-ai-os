"""Mission state machine + repository tests (in-memory SQLite, no live DB)."""
import pytest

import app.missions.models  # noqa: F401  (registers Mission/Task tables on Base)
from app.db import session as db
from app.missions.repository import MissionRepository
from app.missions.state import (
    InvalidTransition,
    MissionStatus,
    TaskStatus,
    can_transition,
    is_terminal,
    transition,
)

SQLITE_MEMORY = "sqlite+aiosqlite:///:memory:"


async def _repo():
    engine = db.get_engine(SQLITE_MEMORY)
    await db.init_models(engine)
    return MissionRepository(db.get_sessionmaker(engine)), engine


# --- state machine ---

def test_legal_and_illegal_transitions():
    assert can_transition(MissionStatus.CREATED, MissionStatus.ACTIVE)
    assert can_transition(MissionStatus.ACTIVE, MissionStatus.PAUSED)
    assert can_transition(MissionStatus.PAUSED, MissionStatus.ACTIVE)
    assert not can_transition(MissionStatus.CREATED, MissionStatus.COMPLETED)
    assert not can_transition(MissionStatus.COMPLETED, MissionStatus.ACTIVE)


def test_transition_raises_on_illegal():
    with pytest.raises(InvalidTransition):
        transition(MissionStatus.CREATED, MissionStatus.COMPLETED)


def test_terminal_states():
    assert is_terminal(MissionStatus.COMPLETED)
    assert is_terminal(MissionStatus.FAILED)
    assert not is_terminal(MissionStatus.ACTIVE)


# --- repository ---

async def test_create_and_get_mission():
    repo, engine = await _repo()
    m = await repo.create("Monitor Company X", priority=5, deadline=123.0,
                          meta={"notify": "strong evidence only"})
    assert m.id and m.status == MissionStatus.CREATED
    fetched = await repo.get(m.id)
    assert fetched.objective == "Monitor Company X"
    assert fetched.priority == 5 and fetched.meta["notify"] == "strong evidence only"
    await engine.dispose()


async def test_status_transitions_are_enforced():
    repo, engine = await _repo()
    m = await repo.create("obj")
    m = await repo.set_status(m.id, MissionStatus.ACTIVE)
    assert m.status == MissionStatus.ACTIVE
    m = await repo.set_status(m.id, MissionStatus.PAUSED)
    m = await repo.set_status(m.id, MissionStatus.ACTIVE)
    m = await repo.set_status(m.id, MissionStatus.COMPLETED)
    assert m.status == MissionStatus.COMPLETED
    # completed is terminal -> any further transition rejected
    with pytest.raises(InvalidTransition):
        await repo.set_status(m.id, MissionStatus.ACTIVE)
    await engine.dispose()


async def test_tasks_crud_and_ordering():
    repo, engine = await _repo()
    m = await repo.create("obj")
    t1 = await repo.add_task(m.id, "research baseline")
    await repo.add_task(m.id, "detect anomalies", depends_on=[t1.id])
    tasks = await repo.get_tasks(m.id)
    assert [t.description for t in tasks] == ["research baseline", "detect anomalies"]
    assert tasks[1].depends_on == [t1.id]
    done = await repo.set_task_status(t1.id, TaskStatus.DONE, result="ok")
    assert done.status == TaskStatus.DONE and done.result == "ok"
    await engine.dispose()


async def test_list_filters_by_status():
    repo, engine = await _repo()
    a = await repo.create("a")
    await repo.create("b")
    await repo.set_status(a.id, MissionStatus.ACTIVE)
    active = await repo.list(status=MissionStatus.ACTIVE)
    assert len(active) == 1 and active[0].id == a.id
    await engine.dispose()
