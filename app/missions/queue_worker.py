"""Queue-driven distributed worker: claim a mission, tick it, requeue or finish.

Where `MissionWorker` polls the DB directly, `QueueWorker` consumes a shared
`MissionQueue`, so N workers can run in parallel and the queue's lease guarantees
each mission is processed by exactly one worker at a time. A mission is claimed,
ticked one DAG layer, then either completed (terminal/paused) or re-enqueued for
the next tick. An error releases the lease so the mission can be retried.
"""
from __future__ import annotations

import asyncio
import logging

from app.missions.executor import TaskExecutor
from app.missions.queue import MissionQueue
from app.missions.repository import MissionRepository
from app.missions.runtime import MissionRuntime
from app.missions.scheduler import order_missions
from app.missions.state import MissionStatus

log = logging.getLogger(__name__)

_DRIVABLE = (MissionStatus.CREATED, MissionStatus.ACTIVE)


class QueueWorker:
    def __init__(
        self,
        repo: MissionRepository,
        executor: TaskExecutor,
        queue: MissionQueue,
        poll_interval: float = 1.0,
    ):
        self._repo = repo
        self._runtime = MissionRuntime(repo, executor)
        self._queue = queue
        self._poll = poll_interval

    async def seed(self) -> int:
        """Enqueue all drivable missions (scheduled order). Returns count seeded."""
        missions = order_missions(
            [m for m in await self._repo.list(limit=100) if m.status in _DRIVABLE]
        )
        for m in missions:
            await self._queue.enqueue(m.id)
        return len(missions)

    async def step(self) -> int | None:
        """Claim one mission, tick it, and requeue or finish. Returns its id."""
        mid = await self._queue.claim()
        if mid is None:
            return None
        try:
            result = await self._runtime.tick(mid)
            await self._queue.complete(mid)  # drop the lease either way
            if not (result.is_terminal or result.status == MissionStatus.PAUSED):
                await self._queue.enqueue(mid)  # more work -> back in line
        except Exception:
            log.exception("queue worker failed on mission %s", mid)
            await self._queue.release(mid)  # let another worker retry
        return mid

    async def drain(self, max_steps: int = 10000) -> None:
        """Seed + process until the queue is empty (tests / one-shot)."""
        await self.seed()
        for _ in range(max_steps):
            if await self._queue.size() == 0 and await self._queue.in_flight() == 0:
                return
            if await self.step() is None:
                return

    async def run(self, stop: asyncio.Event) -> None:
        """Continuously seed drivable missions and process the queue."""
        log.info("queue worker started")
        while not stop.is_set():
            await self.seed()
            while await self._queue.size() > 0:
                if stop.is_set():
                    break
                await self.step()
            waiter = asyncio.ensure_future(stop.wait())
            _, pending = await asyncio.wait({waiter}, timeout=self._poll)
            for t in pending:
                t.cancel()
        log.info("queue worker stopped")
