"""Async engine + session factory.

A single cached engine/sessionmaker built from `Settings.database_url`, plus
helpers to create tables and to health-check the connection. Passing an explicit
`dsn`/`engine` returns uncached objects — used by tests (in-memory SQLite) and by
callers targeting a specific database.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.db.base import Base

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None

# Uncached (dsn-provided) engines are tracked so tests can dispose them at the
# end of each test — otherwise their aiosqlite connections linger and raise
# "Event loop is closed" during GC on Python 3.11 (intermittent CI failures).
_ephemeral_engines: list[AsyncEngine] = []


def get_engine(dsn: str | None = None) -> AsyncEngine:
    """Return an async engine. Cached when built from config (dsn=None)."""
    global _engine
    if dsn is not None:
        engine = create_async_engine(dsn, future=True)
        _ephemeral_engines.append(engine)
        return engine
    if _engine is None:
        _engine = create_async_engine(get_settings().database_url, future=True)
    return _engine


def get_sessionmaker(
    engine: AsyncEngine | None = None,
) -> async_sessionmaker[AsyncSession]:
    """Return a sessionmaker. Cached when using the default engine."""
    global _sessionmaker
    if engine is not None:
        return async_sessionmaker(engine, expire_on_commit=False)
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _sessionmaker


async def init_models(engine: AsyncEngine) -> None:
    """Create all tables registered on Base.metadata (idempotent)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def ping(session: AsyncSession) -> bool:
    """Return True if the database answers `SELECT 1`."""
    try:
        result = await session.execute(text("SELECT 1"))
        return result.scalar() == 1
    except Exception:
        return False


async def database_healthy(engine: AsyncEngine | None = None) -> bool:
    """Open a session and health-check the database connection."""
    maker = get_sessionmaker(engine)
    try:
        async with maker() as session:
            return await ping(session)
    except Exception:
        return False


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yield a session and close it."""
    async with get_sessionmaker()() as session:
        yield session


async def reset_engine() -> None:
    """Dispose and clear the cached engine/sessionmaker (shutdown / tests)."""
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None
