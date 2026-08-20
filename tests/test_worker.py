"""Background mission worker: drains missions, respects paused, survives errors."""
import asyncio

import app.missions.models  # noqa: F401  (register tables)
from app.db import session as db
from app.missions.models import Task
from app.missions.repository import MissionRepository
from app.missions.state import MissionStatus, TaskStatus
from app.missions.worker import MissionWorker

SQLITE_MEMORY = "sqlite+aiosqlite:///:memory:"


async def _repo() -> MissionRepository:
    engine = db.get_engine(SQLITE_MEMORY)
    await db.init_models(engine)
    return MissionRepository(db.get_sessionmaker(engine))


async def _chain(repo: MissionRepository, priority: int = 0):
    """A 3-task chain t0 -> t1 -> t2."""
    m = await repo.create("demo", priority=priority)
    t0 = await repo.add_task(m.id, "s0", depends_on=[])
    t1 = await repo.add_task(m.id, "s1", depends_on=[t0.id])
    await repo.add_task(m.id, "s2", depends_on=[t1.id])
    return m


async def _ok_executor(task: Task) -> str:
    return f"ran {task.id}"


async def test_drain_completes_all_missions():
    repo = await _repo()
    a = await _chain(repo)
    b = await _chain(repo)
    worker = MissionWorker(repo, _ok_executor, poll_interval=0.01)

    await worker.drain()

    assert (await repo.get(a.id)).status == MissionStatus.COMPLETED
    assert (await repo.get(b.id)).status == MissionStatus.COMPLETED


async def test_poll_once_advances_one_layer():
    repo = await _repo()
    m = await _chain(repo)
    worker = MissionWorker(repo, _ok_executor)

    results = await worker.poll_once()
    assert len(results) == 1  # one drivable mission
    assert len(results[0].ran) == 1  # only the root was ready
    assert (await repo.get(m.id)).status == MissionStatus.ACTIVE


async def test_worker_skips_paused_missions():
    repo = await _repo()
    m = await _chain(repo)
    await repo.set_status(m.id, MissionStatus.ACTIVE)
    await repo.set_status(m.id, MissionStatus.PAUSED)

    await MissionWorker(repo, _ok_executor).drain()

    # paused mission was left untouched
    assert (await repo.get(m.id)).status == MissionStatus.PAUSED
    assert all(t.status == TaskStatus.PENDING for t in await repo.get_tasks(m.id))


async def test_run_loop_drives_then_stops():
    repo = await _repo()
    m = await _chain(repo)
    worker = MissionWorker(repo, _ok_executor, poll_interval=0.01)

    stop = asyncio.Event()
    task = asyncio.create_task(worker.run(stop))
    # let it tick until the mission completes
    for _ in range(200):
        if (await repo.get(m.id)).status == MissionStatus.COMPLETED:
            break
        await asyncio.sleep(0.01)
    stop.set()
    await asyncio.wait_for(task, timeout=1.0)

    assert (await repo.get(m.id)).status == MissionStatus.COMPLETED


async def test_poll_survives_executor_errors():
    repo = await _repo()
    m = await _chain(repo)

    async def boom(task: Task) -> str:
        raise RuntimeError("kaboom")

    # a failing task should fail the mission, not crash the worker
    await MissionWorker(repo, boom, poll_interval=0.01).drain()
    assert (await repo.get(m.id)).status == MissionStatus.FAILED
