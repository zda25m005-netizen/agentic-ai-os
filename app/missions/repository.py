"""Async persistence for missions and tasks.

All state transitions go through here so the state machine is enforced in exactly
one place. Backed by SQLAlchemy async; tests run on in-memory SQLite.
"""
from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.missions.models import Mission, MissionRow, Task, TaskRow
from app.missions.state import MissionStatus, TaskStatus, transition


class MissionRepository:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]):
        self._sm = sessionmaker

    # --- missions ---

    async def create(
        self, objective: str, priority: int = 0,
        deadline: float | None = None, meta: dict | None = None,
    ) -> Mission:
        async with self._sm() as s:
            row = MissionRow(
                objective=objective, priority=priority,
                deadline=deadline, meta=meta or {},
            )
            s.add(row)
            await s.commit()
            await s.refresh(row)
            return Mission.from_row(row)

    async def get(self, mission_id: int) -> Mission | None:
        async with self._sm() as s:
            row = await s.get(MissionRow, mission_id)
            return Mission.from_row(row) if row else None

    async def list(
        self, status: MissionStatus | None = None, limit: int = 50
    ) -> list[Mission]:
        async with self._sm() as s:
            q = select(MissionRow).order_by(desc(MissionRow.priority), MissionRow.id)
            if status is not None:
                q = q.where(MissionRow.status == status.value)
            rows = (await s.execute(q.limit(limit))).scalars().all()
            return [Mission.from_row(r) for r in rows]

    async def set_status(self, mission_id: int, target: MissionStatus) -> Mission:
        """Transition a mission's status, enforcing the state machine."""
        async with self._sm() as s:
            row = await s.get(MissionRow, mission_id)
            if row is None:
                raise ValueError(f"mission {mission_id} not found")
            current = MissionStatus(row.status)
            row.status = transition(current, target).value  # raises if illegal
            await s.commit()
            await s.refresh(row)
            return Mission.from_row(row)

    # --- tasks ---

    async def add_task(
        self, mission_id: int, description: str,
        depends_on: list[int] | None = None,
    ) -> Task:
        async with self._sm() as s:
            row = TaskRow(
                mission_id=mission_id, description=description,
                depends_on=depends_on or [],
            )
            s.add(row)
            await s.commit()
            await s.refresh(row)
            return Task.from_row(row)

    async def get_tasks(self, mission_id: int) -> list[Task]:
        async with self._sm() as s:
            rows = (await s.execute(
                select(TaskRow).where(TaskRow.mission_id == mission_id).order_by(TaskRow.id)
            )).scalars().all()
            return [Task.from_row(r) for r in rows]

    async def set_task_status(
        self, task_id: int, status: TaskStatus, result: str | None = None
    ) -> Task:
        async with self._sm() as s:
            row = await s.get(TaskRow, task_id)
            if row is None:
                raise ValueError(f"task {task_id} not found")
            row.status = status.value
            if result is not None:
                row.result = result
            await s.commit()
            await s.refresh(row)
            return Task.from_row(row)
