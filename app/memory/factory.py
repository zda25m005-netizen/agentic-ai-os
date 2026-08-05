"""Pick the episodic-memory backend from config.

Returns the SQLite store (default, zero-setup) or the Postgres store, so the
rest of the app depends on the interface, not the backend.
"""
from __future__ import annotations

from app.core.config import get_settings
from app.db.session import get_sessionmaker
from app.memory.episodic import EpisodicMemory
from app.memory.episodic_pg import PostgresEpisodicMemory


def build_episodic(
    backend: str | None = None,
    sqlite_path: str = ":memory:",
    sessionmaker=None,
):
    """Build an episodic store. `backend` overrides config ("sqlite"|"postgres")."""
    backend = (backend or get_settings().memory_backend).lower()
    if backend == "postgres":
        return PostgresEpisodicMemory(sessionmaker or get_sessionmaker())
    return EpisodicMemory.open(sqlite_path)
