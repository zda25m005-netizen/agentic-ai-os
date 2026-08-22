"""Day 11: scheduler + resources + router + recovery wired into the tick."""
import app.missions.models  # noqa: F401  (register tables)
from app.db import session as db
from app.missions.models import Task
from app.missions.repository import MissionRepository
from app.missions.runtime import MissionRuntime
from app.missions.state import MissionStatus, TaskStatus

SQLITE_MEMORY = "sqlite+aiosqlite:///:memory:"


async def _repo() -> MissionRepository:
    engine = db.get_engine(SQLITE_MEMORY)
    await db.init_models(engine)
    return MissionRepository(db.get_sessionmaker(engine))


async def _chain(repo, n=3, meta=None):
    m = await repo.create("demo", meta=meta or {})
    prev = None
    for i in range(n):
        deps = [prev] if prev is not None else []
        t = await repo.add_task(m.id, f"step {i}", depends_on=deps)
        prev = t.id
    return m


async def _ok(task: Task) -> str:
    return f"done {task.id}"


# --- recovery in the tick ---

async def test_transient_failure_recovers_via_retry():
    repo = await _repo()
    m = await _chain(repo, n=1)
    calls = {"n": 0}

    async def flaky(task: Task) -> str:
        calls["n"] += 1
        if calls["n"] == 1:
            raise TimeoutError("blip")
        return "recovered"

    final = await MissionRuntime(repo, flaky).run(m.id)
    assert final.status == MissionStatus.COMPLETED  # retry healed it
    assert calls["n"] == 2  # failed once, retried once
    tasks = await repo.get_tasks(m.id)
    assert tasks[0].result == "recovered"


# --- resource budget in the tick ---

async def test_budget_exhaustion_terminates_mission():
    repo = await _repo()
    # a tiny llm-call budget: the first task consumes it, the rest can't run
    m = await _chain(repo, n=3, meta={"budget": {"max_llm_calls": 1}})

    final = await MissionRuntime(repo, _ok).run(m.id)

    assert final.status == MissionStatus.FAILED
    assert final.meta["termination_reason"] == "budget exhausted"
    assert final.meta["usage"]["llm_calls"] >= 1
    # not all tasks ran
    tasks = await repo.get_tasks(m.id)
    assert any(t.status == TaskStatus.PENDING for t in tasks)


async def test_usage_is_tracked_and_persisted():
    repo = await _repo()
    m = await _chain(repo, n=2)
    final = await MissionRuntime(repo, _ok).run(m.id)
    assert final.status == MissionStatus.COMPLETED
    assert final.meta["usage"]["llm_calls"] == 2  # one per task
    assert final.meta["usage"]["tokens"] > 0


# --- router in the tick ---

async def test_model_routed_per_task_role():
    repo = await _repo()
    # a task tagged as analyst should route to the frontier model
    m = await repo.create("demo", meta={})
    t = await repo.add_task(m.id, "analyze", depends_on=[])
    await repo.update_meta(m.id, {"roles": {str(t.id): "analyst"}})

    final = await MissionRuntime(repo, _ok).run(m.id)
    assert final.status == MissionStatus.COMPLETED
    assert final.meta["models"][str(t.id)] == "frontier"


async def test_downgrade_routes_to_cheaper_model():
    repo = await _repo()
    # budget already ~85% spent -> DOWNGRADE -> analyst drops frontier->balanced
    m = await repo.create("demo", meta={
        "budget": {"max_llm_calls": 100},
        "usage": {"llm_calls": 85},
    })
    t = await repo.add_task(m.id, "analyze", depends_on=[])
    await repo.update_meta(m.id, {
        "budget": {"max_llm_calls": 100},
        "usage": {"llm_calls": 85},
        "roles": {str(t.id): "analyst"},
    })

    final = await MissionRuntime(repo, _ok).run(m.id)
    assert final.meta["models"][str(t.id)] == "balanced"  # downgraded from frontier
