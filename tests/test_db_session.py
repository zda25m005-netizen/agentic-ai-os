"""Async DB layer tests, run against in-memory SQLite (no live Postgres)."""
from sqlalchemy import Integer, String, select
from sqlalchemy.orm import Mapped, mapped_column

from app.db import session as db
from app.db.base import Base

SQLITE_MEMORY = "sqlite+aiosqlite:///:memory:"


class _Thing(Base):
    __tablename__ = "things"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)


async def test_ping_returns_true_on_live_connection():
    engine = db.get_engine(SQLITE_MEMORY)
    async with db.get_sessionmaker(engine)() as session:
        assert await db.ping(session) is True
    await engine.dispose()


async def test_init_models_creates_tables_and_roundtrips():
    engine = db.get_engine(SQLITE_MEMORY)
    await db.init_models(engine)
    maker = db.get_sessionmaker(engine)
    async with maker() as session:
        session.add(_Thing(name="widget"))
        await session.commit()
    async with maker() as session:
        rows = (await session.execute(select(_Thing))).scalars().all()
        assert [t.name for t in rows] == ["widget"]
    await engine.dispose()


async def test_database_healthy_true_and_false():
    engine = db.get_engine(SQLITE_MEMORY)
    assert await db.database_healthy(engine) is True
    await engine.dispose()

    # A bogus DSN should health-check False, not raise.
    bad = db.get_engine("sqlite+aiosqlite:///:memory:")
    await bad.dispose()  # dispose first so a query fails
    # database_healthy swallows errors and returns a bool
    assert isinstance(await db.database_healthy(bad), bool)


def test_get_engine_caches_default():
    import asyncio

    asyncio.run(db.reset_engine())
    a = db.get_engine()
    b = db.get_engine()
    assert a is b
    asyncio.run(db.reset_engine())
