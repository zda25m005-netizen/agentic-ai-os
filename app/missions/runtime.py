"""The resumable runtime tick — now budgeted, model-routed, and self-healing.

Every tick reloads state from the repository, so the loop holds no in-memory
progress: a mission can stop after any tick (crash, budget, pause) and resume by
calling `tick` again. One tick runs the current ready-set (one layer of the DAG),
persists each result, then re-settles the mission.

Day 11 wires the four OS subsystems into that loop:
- **scheduler** decides *which mission* ticks first (in the worker, Day 7);
- **resources** — a per-mission budget is loaded from `meta`, usage accumulates
  across ticks, and an exhausted budget terminates the mission;
- **router** picks a model tier per task from its role, dropping a tier when the
  budget policy says `DOWNGRADE`;
- **recovery** wraps every task so a transient failure retries up the recovery
  ladder before the task is marked failed.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field

from app.missions import task_graph
from app.missions.executor import TaskExecutor
from app.missions.model_router import route_for
from app.missions.models import Mission, Task
from app.missions.recovery import (
    RecoveryEngine,
    RecoveryExhausted,
    execute_with_recovery,
)
from app.missions.repository import MissionRepository
from app.missions.resources import (
    BudgetStatus,
    ResourceManager,
    Usage,
    budget_from_meta,
)
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


def _load_usage(meta: dict) -> Usage:
    u = (meta or {}).get("usage") or {}
    return Usage(
        usd=u.get("usd", 0.0), tokens=u.get("tokens", 0),
        tool_calls=u.get("tool_calls", 0), llm_calls=u.get("llm_calls", 0),
    )


def _estimate_tokens(*parts: str) -> int:
    return max(1, sum(len(p) for p in parts) // 4)  # ~4 chars/token


class MissionRuntime:
    """Drives missions over their task DAG with budget, routing, and recovery."""

    def __init__(
        self,
        repo: MissionRepository,
        executor: TaskExecutor,
        *,
        recovery: RecoveryEngine | None = None,
    ):
        self._repo = repo
        self._execute = executor
        self._recovery = recovery or RecoveryEngine(max_attempts=3)

    async def _recover(self, mission_id: int) -> None:
        """Reset tasks stuck in RUNNING (a worker that died mid-step) to PENDING."""
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

    async def _run_task(self, task: Task, mission: Mission, mgr: ResourceManager,
                        models: dict[str, str]) -> bool:
        """Execute one task with routing + recovery. Returns True on success."""
        role = (mission.meta.get("roles") or {}).get(str(task.id), "executor")
        model = route_for(role, mgr.evaluate())
        models[str(task.id)] = model.name

        await self._repo.set_task_status(task.id, TaskStatus.RUNNING)
        try:
            res = await execute_with_recovery(
                lambda: self._execute(task), engine=self._recovery,
            )
        except RecoveryExhausted as exc:
            cause = exc.__cause__ or exc
            log.warning("mission %s task %s failed: %s", mission.id, task.id, cause)
            mgr.record(llm_calls=1)
            await self._repo.set_task_status(task.id, TaskStatus.FAILED, result=str(cause))
            return False

        result = str(res.value)
        tokens = _estimate_tokens(task.description, result)
        mgr.record(usd=tokens / 1000.0 * model.usd_per_1k, tokens=tokens, llm_calls=1)
        await self._repo.set_task_status(task.id, TaskStatus.DONE, result=result)
        return True

    async def _persist_meta(self, mission: Mission, mgr: ResourceManager,
                            models: dict[str, str], reason: str | None) -> None:
        meta = dict(mission.meta)
        meta["usage"] = asdict(mgr.usage)
        meta["models"] = {**(meta.get("models") or {}), **models}
        if reason:
            meta["termination_reason"] = reason
        await self._repo.update_meta(mission.id, meta)

    async def tick(self, mission_id: int) -> TickResult:
        """Advance the mission by one DAG layer. Idempotent w.r.t. persisted state."""
        mission = await self._repo.get(mission_id)
        if mission is None:
            raise ValueError(f"mission {mission_id} not found")
        if mission.status in (MissionStatus.COMPLETED, MissionStatus.FAILED,
                              MissionStatus.PAUSED):
            return TickResult(mission_id, mission.status)
        if mission.status == MissionStatus.CREATED:
            await self._repo.set_status(mission_id, MissionStatus.ACTIVE)

        await self._recover(mission_id)

        status = await self._settle(mission_id)
        if status in (MissionStatus.COMPLETED, MissionStatus.FAILED):
            return TickResult(mission_id, status)

        # resource manager for this mission (budget from meta, usage carried over)
        mgr = ResourceManager(
            budget=budget_from_meta(mission.meta),
            usage=_load_usage(mission.meta),
            started_at=mission.created_at,
        )
        models: dict[str, str] = {}

        # already over budget before running anything -> terminate
        if mgr.exceeded():
            await self._persist_meta(mission, mgr, models, "budget exhausted")
            m = await self._repo.set_status(mission_id, MissionStatus.FAILED)
            return TickResult(mission_id, m.status)

        ran: list[int] = []
        failed: list[int] = []
        terminated = False
        for task in task_graph.ready_tasks(await self._repo.get_tasks(mission_id)):
            ran.append(task.id)
            ok = await self._run_task(task, mission, mgr, models)
            if not ok:
                failed.append(task.id)
            if mgr.evaluate() == BudgetStatus.TERMINATE:  # budget hit mid-layer
                terminated = True
                break

        await self._persist_meta(
            mission, mgr, models, "budget exhausted" if terminated else None
        )
        if terminated:
            m = await self._repo.set_status(mission_id, MissionStatus.FAILED)
            return TickResult(mission_id, m.status, ran=ran, failed=failed)

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
