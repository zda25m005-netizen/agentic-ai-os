"""Resumable mission runtime: tick, run-to-completion, failure, resume."""
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


async def _linear_mission(repo: MissionRepository):
    """Mission with a 3-task chain: t0 -> t1 -> t2."""
    m = await repo.create("demo")
    t0 = await repo.add_task(m.id, "step 0", depends_on=[])
    t1 = await repo.add_task(m.id, "step 1", depends_on=[t0.id])
    await repo.add_task(m.id, "step 2", depends_on=[t1.id])
    return m


def _record_executor(log: list[int]):
    async def execute(task: Task) -> str:
        log.append(task.id)
        return f"ran {task.id}"
    return execute


async def test_run_completes_linear_mission_in_order():
    repo = await _repo()
    m = await _linear_mission(repo)
    order: list[int] = []
    runtime = MissionRuntime(repo, _record_executor(order))

    final = await runtime.run(m.id)

    assert final.status == MissionStatus.COMPLETED
    assert order == sorted(order)  # ran root -> middle -> leaf
    tasks = await repo.get_tasks(m.id)
    assert all(t.status == TaskStatus.DONE for t in tasks)
    assert tasks[0].result == "ran " + str(tasks[0].id)


async def test_tick_advances_one_layer_at_a_time():
    repo = await _repo()
    m = await _linear_mission(repo)
    runtime = MissionRuntime(repo, _record_executor([]))

    r1 = await runtime.tick(m.id)
    assert len(r1.ran) == 1  # only the root was ready
    assert r1.status == MissionStatus.ACTIVE
    # mission moved CREATED -> ACTIVE on the first tick
    assert (await repo.get(m.id)).status == MissionStatus.ACTIVE


async def test_failed_task_fails_the_mission():
    repo = await _repo()
    m = await _linear_mission(repo)

    async def boom(task: Task) -> str:
        if task.description == "step 1":
            raise RuntimeError("kaboom")
        return "ok"

    final = await MissionRuntime(repo, boom).run(m.id)

    assert final.status == MissionStatus.FAILED
    tasks = await repo.get_tasks(m.id)
    by_desc = {t.description: t for t in tasks}
    assert by_desc["step 1"].status == TaskStatus.FAILED
    assert "kaboom" in by_desc["step 1"].result
    # the leaf never ran because its dependency died
    assert by_desc["step 2"].status == TaskStatus.PENDING


async def test_resume_after_partial_progress():
    repo = await _repo()
    m = await _linear_mission(repo)
    runtime = MissionRuntime(repo, _record_executor([]))

    await runtime.tick(m.id)  # completes only the root
    tasks = await repo.get_tasks(m.id)
    assert tasks[0].status == TaskStatus.DONE
    assert tasks[1].status == TaskStatus.PENDING

    # a fresh runtime (as if the process restarted) resumes from persisted state
    fresh = MissionRuntime(repo, _record_executor([]))
    final = await fresh.run(m.id)
    assert final.status == MissionStatus.COMPLETED


async def test_recovers_task_stuck_running():
    repo = await _repo()
    m = await _linear_mission(repo)
    tasks = await repo.get_tasks(m.id)
    # simulate a crash: root left RUNNING
    await repo.set_task_status(tasks[0].id, TaskStatus.RUNNING)

    final = await MissionRuntime(repo, _record_executor([])).run(m.id)
    assert final.status == MissionStatus.COMPLETED  # RUNNING was reset and retried
