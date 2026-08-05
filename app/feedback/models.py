"""Feedback table.

One row per rating a user gives an answer. `rating` is "up"/"down"; an optional
`better_answer` lets a user supply a preferred response — together these yield
(chosen, rejected) pairs for DPO and labels for the feedback reranker.
"""
from __future__ import annotations

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FeedbackRow(Base):
    """A single feedback event on a produced answer."""

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    rating: Mapped[str] = mapped_column(String(8), nullable=False)  # "up" | "down"
    better_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    ts: Mapped[float] = mapped_column(Float, nullable=False)
