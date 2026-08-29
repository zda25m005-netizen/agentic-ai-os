"""Shared pytest fixtures.

Use a single session-scoped asyncio event loop for the whole test run. Many tests
create in-memory async SQLAlchemy/aiosqlite engines (and subprocesses) without
disposing them; with the default per-test loop, those linger and raise
"Event loop is closed" during garbage collection when each test's loop is torn
down — an intermittent CI failure. One shared loop that closes only at the end
of the session avoids the mid-run teardown entirely.
"""
from __future__ import annotations

import asyncio

import pytest


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
