"""Shared pytest fixtures.

Tests create in-memory async SQLAlchemy/aiosqlite engines via
`app.db.session.get_engine(dsn=...)`. If they aren't disposed, their aiosqlite
connections linger and raise "Event loop is closed" during garbage collection
when the test's event loop is torn down — an intermittent CI failure on Python
3.11. This autouse fixture disposes every ephemeral engine at the end of each
test, while its event loop is still open.
"""
from __future__ import annotations

import pytest_asyncio

from app.db import session as _db


@pytest_asyncio.fixture(autouse=True)
async def _dispose_ephemeral_engines():
    yield
    engines, _db._ephemeral_engines = _db._ephemeral_engines, []
    for engine in engines:
        try:
            await engine.dispose()
        except Exception:
            pass
