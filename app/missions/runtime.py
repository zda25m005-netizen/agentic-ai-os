"""The resumable runtime tick: drive a mission forward one DAG step at a time.

Every tick reloads state from the repository, so the loop holds no in-memory
progress — a mission can stop after any tick (crash, budget, pause) and resume by
calling `tick` again. One tick runs the current ready-set (one layer of the DAG),
persists each result, then re-settles the mission (COMPLETED when all tasks are
done, FAILED when a dead dependency strands the rest).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.missions import task_graph
from app.missions.executor import TaskExecutor
from app.missions.models import Mission
from app.missions.repository import MissionRepository
from app.missions.state import MissionStatus, TaskStatus

log = logging.getLogger(__name__)


@dataclass
class TickResult:
    mission_id: int
    status: MissionStatus
    ran: list[int] = field(default_factory=list)     # tasks attempted this tick
    failed: list[int] = field(default_factory=list)  # tasks that failed this tick

    @property
    def is_terminal(self) -> bool:
        return self.status in (MissionStatus.COMPLETED, MissionStatus.FAILED)


class MissionRuntime:
    """Drives missions over their task DAG using an injected `TaskExecutor`."""

    def __init__(self, repo: MissionRepository, executor: TaskExecutor):
        self._repo = repo
        self._execute = executor

    async def _recover(self, mission_id: int) -> None:
        """Reset tasks stuck in RUNNING (a worker that died mid-step) to PENDING.

        Safe here because Day 4 runs a single worker; the scheduler adds proper
        leasing later. This is what makes a crashed mission resume cleanly.
        """
        for t in await self._repo.get_tasks(mission_id):
            if t.status == TaskStatus.RUNNING:
                await self._repo.set_task_status(t.id, TaskStatus.PENDING)

    async def _settle(self, mission_id: int) -> MissionStatus:
        """Move the mission to COMPLETED / FAILED if the graph says so."""
        tasks = await self._repo.get_tasks(mission_id)
        if task_graph.is_complete(tasks):
            return (await self._repo.set_status(mission_id, MissionStatus.COMPLETED)).status
        if task_graph.is_blocked(tasks):
            return (await self._repo.set_status(mission_id, MissionStatus.FAILED)).status
        return MissionStatus.ACTIVE

    async def tick(self, mission_id: int) -> TickResult:
        """Advance the mission by one DAG layer. Idempotent w.r.t. persisted state."""
        mission = await self._repo.get(mission_id)
        if mission is None:
            raise ValueError(f"mission {mission_id} not found")
        # terminal or paused: nothing to do
        if mission.status in (MissionStatus.COMPLETED, MissionStatus.FAILED,
                              MissionStatus.PAUSED):
            return TickResult(mission_id, mission.status)
        if mission.status == MissionStatus.CREATED:
            await self._repo.set_status(mission_id, MissionStatus.ACTIVE)

        await self._recover(mission_id)

        # settle before running, in case a prior tick already finished the graph
        status = await self._settle(mission_id)
        if status in (MissionStatus.COMPLETED, MissionStatus.FAILED):
            return TickResult(mission_id, status)

        ran: list[int] = []
        failed: list[int] = []
        for task in task_graph.ready_tasks(await self._repo.get_tasks(mission_id)):
            await self._repo.set_task_status(task.id, TaskStatus.RUNNING)
            ran.append(task.id)
            try:
                result = await self._execute(task)
                await self._repo.set_task_status(task.id, TaskStatus.DONE, result=result)
            except Exception as exc:  # a task failing is data, not a runtime crash
                log.warning("mission %s task %s failed: %s", mission_id, task.id, exc)
                await self._repo.set_task_status(task.id, TaskStatus.FAILED, result=str(exc))
                failed.append(task.id)

        status = await self._settle(mission_id)
        return TickResult(mission_id, status, ran=ran, failed=failed)

    async def run(self, mission_id: int, max_ticks: int = 100) -> Mission:
        """Tick until the mission is terminal, paused, or can make no progress."""
        for _ in range(max_ticks):
            result = await self.tick(mission_id)
            if result.is_terminal or result.status == MissionStatus.PAUSED:
                break
            if not result.ran:  # no ready work and not settled -> avoid a spin loop
                break
        mission = await self._repo.get(mission_id)
        assert mission is not None
        return mission
