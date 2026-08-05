"""SQLAlchemy models for long-term memory.

`EpisodeRow` is the Postgres-backed table for the episodic log — the same
shape as the SQLite store's rows (goal, answer, timestamp), so the two backends
are interchangeable behind the memory interface.
"""
from __future__ import annotations

from sqlalchemy import Float, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EpisodeRow(Base):
    """One recorded agent run."""

    __tablename__ = "episodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    ts: Mapped[float] = mapped_column(Float, nullable=False)
