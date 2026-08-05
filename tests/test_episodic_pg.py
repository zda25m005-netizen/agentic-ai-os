"""Postgres episodic store tests, run against in-memory SQLite (aiosqlite).

The store is DB-agnostic (SQLAlchemy async), so the same code path is exercised
without a live Postgres. Also checks the backend factory and that MemoryManager
works with an async episodic backend.
"""
import app.memory.models  # noqa: F401  (registers EpisodeRow on Base)
from app.db import session as db
from app.memory.episodic import EpisodicMemory
from app.memory.episodic_pg import PostgresEpisodicMemory
from app.memory.factory import build_episodic
from app.memory.manager import MemoryManager

SQLITE_MEMORY = "sqlite+aiosqlite:///:memory:"


async def _store():
    engine = db.get_engine(SQLITE_MEMORY)
    await db.init_models(engine)
    return PostgresEpisodicMemory(db.get_sessionmaker(engine)), engine


async def test_save_recent_and_count():
    store, engine = await _store()
    i1 = await store.save("goal one", "answer one")
    i2 = await store.save("goal two", "answer two")
    assert i2 > i1
    recent = await store.recent()
    assert [e.goal for e in recent] == ["goal two", "goal one"]  # newest first
    assert await store.count() == 2
    await engine.dispose()


async def test_search_matches_goal_or_answer():
    store, engine = await _store()
    await store.save("deploy to k8s", "done")
    await store.save("write unit tests", "green")
    hits = await store.search("deploy")
    assert len(hits) == 1 and hits[0].goal == "deploy to k8s"
    hits2 = await store.search("green")
    assert len(hits2) == 1 and hits2[0].answer == "green"
    await engine.dispose()


def test_factory_selects_sqlite_by_default():
    assert isinstance(build_episodic("sqlite"), EpisodicMemory)


def test_factory_selects_postgres():
    store = build_episodic("postgres", sessionmaker=db.get_sessionmaker(
        db.get_engine(SQLITE_MEMORY)))
    assert isinstance(store, PostgresEpisodicMemory)


class _FakeSemantic:
    def __init__(self):
        self.added = []

    async def add(self, goal, answer):
        self.added.append((goal, answer))

    async def recall(self, query, limit=3):
        return []


async def test_manager_remember_with_async_episodic():
    store, engine = await _store()
    manager = MemoryManager(store, _FakeSemantic())  # type: ignore[arg-type]
    await manager.remember("g", "a")
    assert await store.count() == 1
    assert manager.semantic.added == [("g", "a")]
    await engine.dispose()


async def test_manager_remember_still_works_with_sync_sqlite():
    manager = MemoryManager(EpisodicMemory.open(":memory:"), _FakeSemantic())  # type: ignore[arg-type]
    await manager.remember("g", "a")
    assert manager.episodic.count() == 1
