"""Mission queue (in-memory + Redis-logic via fake) + queue-driven worker."""
from collections import defaultdict

import app.missions.models  # noqa: F401  (register tables)
from app.db import session as db
from app.missions.queue import InMemoryQueue, RedisQueue, build_queue
from app.missions.queue_worker import QueueWorker
from app.missions.repository import MissionRepository
from app.missions.state import MissionStatus


class FakeRedis:
    """Minimal async Redis stand-in: enough for RedisQueue's list/set ops."""

    def __init__(self):
        self.lists = defaultdict(list)
        self.sets = defaultdict(set)

    async def sadd(self, key, value):
        if value in self.sets[key]:
            return 0
        self.sets[key].add(value)
        return 1

    async def srem(self, key, value):
        if value in self.sets[key]:
            self.sets[key].discard(value)
            return 1
        return 0

    async def lpush(self, key, value):
        self.lists[key].insert(0, value)
        return len(self.lists[key])

    async def rpop(self, key):
        return self.lists[key].pop() if self.lists[key] else None

    async def llen(self, key):
        return len(self.lists[key])

    async def scard(self, key):
        return len(self.sets[key])

    async def sismember(self, key, value):
        return value in self.sets[key]


# --- queue semantics (parametrized over both backends) ---

def _queues():
    return [InMemoryQueue(), RedisQueue(FakeRedis())]


async def test_enqueue_dedupes_and_fifo():
    for q in _queues():
        await q.enqueue(1)
        await q.enqueue(1)  # dedup
        await q.enqueue(2)
        assert await q.size() == 2
        assert await q.claim() == 1  # FIFO
        assert await q.claim() == 2


async def test_claim_leases_exclusively():
    for q in _queues():
        await q.enqueue(5)
        assert await q.claim() == 5
        assert await q.in_flight() == 1
        assert await q.claim() is None       # nothing else queued
        # a claimed mission can't be re-enqueued while in flight
        await q.enqueue(5)
        assert await q.size() == 0


async def test_complete_and_release():
    for q in _queues():
        await q.enqueue(7)
        await q.claim()
        await q.complete(7)
        assert await q.in_flight() == 0
        # after completion it can be enqueued again
        await q.enqueue(7)
        assert await q.size() == 1

        mid = await q.claim()
        await q.release(mid)                 # failed -> back in queue
        assert await q.size() == 1 and await q.in_flight() == 0


def test_build_queue_defaults_to_in_memory():
    assert isinstance(build_queue(""), InMemoryQueue)


# --- queue-driven worker ---

async def _repo():
    engine = db.get_engine("sqlite+aiosqlite:///:memory:")
    await db.init_models(engine)
    return MissionRepository(db.get_sessionmaker(engine))


async def _ok(task):
    return "ok"


async def test_queue_worker_drains_missions_to_completion():
    repo = await _repo()
    ids = []
    for _ in range(3):
        m = await repo.create("demo")
        a = await repo.add_task(m.id, "s0", depends_on=[])
        await repo.add_task(m.id, "s1", depends_on=[a.id])
        ids.append(m.id)

    worker = QueueWorker(repo, _ok, InMemoryQueue())
    await worker.drain()

    for mid in ids:
        assert (await repo.get(mid)).status == MissionStatus.COMPLETED


async def test_two_workers_share_a_queue_without_double_processing():
    repo = await _repo()
    m = await repo.create("demo")
    await repo.add_task(m.id, "s0", depends_on=[])

    q = InMemoryQueue()
    await q.enqueue(m.id)
    w1, w2 = QueueWorker(repo, _ok, q), QueueWorker(repo, _ok, q)

    first = await w1.step()          # w1 claims it
    second = await w2.step()         # w2 finds nothing (leased)
    assert first == m.id and second is None
