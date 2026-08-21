"""Background worker: drive missions forward without a client holding a request.

The Mission API can tick/run a mission on demand, but a long-horizon system must
make progress on its own. The worker polls for non-terminal missions and ticks
each one, so a mission created via `POST /missions` advances by itself. It's the
same `MissionRuntime.tick` the API uses — the worker just calls it on a schedule,
highest priority first, and every tick reloads from the DB so a restart is safe.
"""
from __future__ import annotations

import asyncio
import logging

from app.missions.executor import TaskExecutor
from app.missions.models import Mission
from app.missions.repository import MissionRepository
from app.missions.runtime import MissionRuntime, TickResult
from app.missions.scheduler import order_missions
from app.missions.state import MissionStatus

log = logging.getLogger(__name__)

# Missions the worker should keep ticking (paused/terminal are left alone).
_DRIVABLE = (MissionStatus.CREATED, MissionStatus.ACTIVE)


class MissionWorker:
    """Polls the repository and ticks drivable missions on an interval."""

    def __init__(
        self,
        repo: MissionRepository,
        executor: TaskExecutor,
        poll_interval: float = 2.0,
    ):
        self._repo = repo
        self._runtime = MissionRuntime(repo, executor)
        self._poll = poll_interval

    async def _due(self) -> list[Mission]:
        """Drivable missions in scheduled order (highest score first).

        Ordering is delegated to the scheduler (priority · deadline · age · value)
        so the most important mission is ticked first under contention.
        """
        missions = await self._repo.list(limit=100)
        drivable = [m for m in missions if m.status in _DRIVABLE]
        return order_missions(drivable)

    async def poll_once(self) -> list[TickResult]:
        """Tick every drivable mission once. Returns each tick's result."""
        results: list[TickResult] = []
        for m in await self._due():
            results.append(await self._runtime.tick(m.id))
        return results

    async def run(self, stop: asyncio.Event) -> None:
        """Loop until `stop` is set, ticking due missions each `poll_interval`.

        A failure in one poll is logged and swallowed so the worker never dies on
        a transient error. Shutdown is prompt: it waits on the stop event with a
        timeout instead of a blind sleep.
        """
        log.info("mission worker started (poll=%.1fs)", self._poll)
        while not stop.is_set():
            try:
                await self.poll_once()
            except Exception:  # a bad poll must not kill the worker
                log.exception("mission worker poll failed")
            await self._wait_or_stop(stop)
        log.info("mission worker stopped")

    async def _wait_or_stop(self, stop: asyncio.Event) -> None:
        """Wait up to `poll_interval`, returning early if `stop` is set.

        Uses `asyncio.wait` (which never raises on timeout) so shutdown is prompt
        and the code is portable across Python versions.
        """
        waiter = asyncio.ensure_future(stop.wait())
        _, pending = await asyncio.wait({waiter}, timeout=self._poll)
        for t in pending:
            t.cancel()

    async def drain(self, max_rounds: int = 1000) -> None:
        """Tick repeatedly until no mission can make progress (tests / one-shot)."""
        for _ in range(max_rounds):
            due = await self._due()
            if not due:
                return
            progressed = False
            for m in due:
                if (await self._runtime.tick(m.id)).ran:
                    progressed = True
            if not progressed:
                return  # nothing advanced this round -> stop, don't spin
