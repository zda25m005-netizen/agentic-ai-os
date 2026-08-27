"""SSE mission stream + versioned /v1 routes."""
import json

import pytest
from httpx import ASGITransport, AsyncClient

import app.missions.models  # noqa: F401  (register tables)
from app.api import missions as mapi
from app.api.main import app
from app.db import session as db
from app.missions.repository import MissionRepository
from app.missions.state import MissionStatus

SQLITE_MEMORY = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def ctx():
    engine = db.get_engine(SQLITE_MEMORY)
    await db.init_models(engine)
    repo = MissionRepository(db.get_sessionmaker(engine))
    app.dependency_overrides[mapi.get_mission_repo] = lambda: repo
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        yield c, repo
    app.dependency_overrides.clear()
    await engine.dispose()


async def test_stream_emits_state_and_done_for_terminal_mission(ctx):
    c, repo = ctx
    m = await repo.create("demo")
    await repo.set_status(m.id, MissionStatus.ACTIVE)
    await repo.set_status(m.id, MissionStatus.COMPLETED)

    r = await c.get(f"/missions/{m.id}/stream")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    body = r.text
    assert "data:" in body and "event: done" in body
    first = json.loads(body.split("data:", 1)[1].split("\n", 1)[0])
    assert first["id"] == m.id and first["status"] == "completed"


async def test_stream_404_for_unknown_mission(ctx):
    c, _ = ctx
    r = await c.get("/missions/9999/stream")
    assert r.status_code == 404


async def test_v1_routes_are_mounted(ctx):
    c, repo = ctx
    m = await repo.create("demo")
    r = await c.get(f"/v1/missions/{m.id}")
    assert r.status_code == 200 and r.json()["id"] == m.id
