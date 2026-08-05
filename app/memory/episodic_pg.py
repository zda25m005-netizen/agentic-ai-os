"""Postgres-backed episodic memory (async SQLAlchemy).

Mirrors the SQLite ``EpisodicMemory`` API — save / recent / search / count —
but async, over a sessionmaker. Returns the same ``Episode`` dataclass, so
``MemoryManager`` treats either backend identically.
"""
from __future__ import annotations

import time

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.memory.episodic import Episode
from app.memory.models import EpisodeRow


class PostgresEpisodicMemory:
    """Async episodic store over Postgres (or any SQLAlchemy async DB)."""

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]):
        self._sm = sessionmaker

    @staticmethod
    def _to_episode(r: EpisodeRow) -> Episode:
        return Episode(id=r.id, goal=r.goal, answer=r.answer, ts=r.ts)

    async def save(self, goal: str, answer: str, ts: float | None = None) -> int:
        ts = time.time() if ts is None else ts
        async with self._sm() as session:
            row = EpisodeRow(goal=goal, answer=answer, ts=ts)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return int(row.id)

    async def recent(self, limit: int = 10) -> list[Episode]:
        async with self._sm() as session:
            result = await session.execute(
                select(EpisodeRow).order_by(desc(EpisodeRow.id)).limit(limit)
            )
            return [self._to_episode(r) for r in result.scalars()]

    async def search(self, term: str, limit: int = 10) -> list[Episode]:
        like = f"%{term}%"
        async with self._sm() as session:
            result = await session.execute(
                select(EpisodeRow)
                .where(or_(EpisodeRow.goal.like(like), EpisodeRow.answer.like(like)))
                .order_by(desc(EpisodeRow.id))
                .limit(limit)
            )
            return [self._to_episode(r) for r in result.scalars()]

    async def count(self) -> int:
        async with self._sm() as session:
            result = await session.execute(select(func.count()).select_from(EpisodeRow))
            return int(result.scalar() or 0)
