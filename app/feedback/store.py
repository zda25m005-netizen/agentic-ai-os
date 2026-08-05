"""Async persistence for user feedback.

`FeedbackStore` mirrors the episodic store's shape (save / recent / count) over
a SQLAlchemy async sessionmaker. `record` is a convenience that persists using
the app's default sessionmaker — the API endpoint calls it, tests monkeypatch it.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import get_sessionmaker
from app.feedback.models import FeedbackRow

VALID_RATINGS = ("up", "down")


@dataclass
class Feedback:
    id: int
    run_id: str | None
    query: str
    answer: str
    rating: str
    better_answer: str | None
    ts: float


class FeedbackStore:
    """Async store of feedback events."""

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]):
        self._sm = sessionmaker

    @staticmethod
    def _to_feedback(r: FeedbackRow) -> Feedback:
        return Feedback(
            id=r.id, run_id=r.run_id, query=r.query, answer=r.answer,
            rating=r.rating, better_answer=r.better_answer, ts=r.ts,
        )

    async def save(
        self,
        query: str,
        answer: str,
        rating: str,
        run_id: str | None = None,
        better_answer: str | None = None,
        ts: float | None = None,
    ) -> int:
        if rating not in VALID_RATINGS:
            raise ValueError(f"rating must be one of {VALID_RATINGS}")
        ts = time.time() if ts is None else ts
        async with self._sm() as session:
            row = FeedbackRow(
                run_id=run_id, query=query, answer=answer,
                rating=rating, better_answer=better_answer, ts=ts,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return int(row.id)

    async def recent(self, limit: int = 20) -> list[Feedback]:
        async with self._sm() as session:
            result = await session.execute(
                select(FeedbackRow).order_by(desc(FeedbackRow.id)).limit(limit)
            )
            return [self._to_feedback(r) for r in result.scalars()]

    async def count(self) -> int:
        async with self._sm() as session:
            result = await session.execute(select(func.count()).select_from(FeedbackRow))
            return int(result.scalar() or 0)


async def record(
    query: str,
    answer: str,
    rating: str,
    run_id: str | None = None,
    better_answer: str | None = None,
) -> int:
    """Persist one feedback event using the default sessionmaker."""
    store = FeedbackStore(get_sessionmaker())
    return await store.save(
        query, answer, rating, run_id=run_id, better_answer=better_answer
    )
