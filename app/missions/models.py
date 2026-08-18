"""ORM tables + plain dataclasses for missions and their tasks.

The ORM rows persist state; the dataclasses (`Mission`, `Task`) are the clean
domain objects the rest of the app works with, so nothing outside this package
depends on SQLAlchemy internals.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.missions.state import MissionStatus, TaskStatus


class MissionRow(Base):
    __tablename__ = "missions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=MissionStatus.CREATED.value)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    deadline: Mapped[float | None] = mapped_column(Float, nullable=True)  # unix ts
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    updated_at: Mapped[float] = mapped_column(Float, default=time.time, onupdate=time.time)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)


class TaskRow(Base):
    __tablename__ = "mission_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id"), index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=TaskStatus.PENDING.value)
    depends_on: Mapped[list] = mapped_column(JSON, default=list)  # list of task ids
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    updated_at: Mapped[float] = mapped_column(Float, default=time.time, onupdate=time.time)


@dataclass
class Mission:
    id: int
    objective: str
    status: MissionStatus
    priority: int
    deadline: float | None
    created_at: float
    updated_at: float
    meta: dict = field(default_factory=dict)

    @classmethod
    def from_row(cls, r: MissionRow) -> Mission:
        return cls(
            id=r.id, objective=r.objective, status=MissionStatus(r.status),
            priority=r.priority, deadline=r.deadline, created_at=r.created_at,
            updated_at=r.updated_at, meta=r.meta or {},
        )


@dataclass
class Task:
    id: int
    mission_id: int
    description: str
    status: TaskStatus
    depends_on: list[int]
    result: str | None
    created_at: float
    updated_at: float

    @classmethod
    def from_row(cls, r: TaskRow) -> Task:
        return cls(
            id=r.id, mission_id=r.mission_id, description=r.description,
            status=TaskStatus(r.status), depends_on=list(r.depends_on or []),
            result=r.result, created_at=r.created_at, updated_at=r.updated_at,
        )
