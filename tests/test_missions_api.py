"""Mission REST surface, driven end to end offline (fake LLM + executor)."""
import json

import pytest
from httpx import ASGITransport, AsyncClient

import app.missions.models  # noqa: F401  (register tables)
from app.api import missions as mapi
from app.api.main import app
from app.db import session as db
from app.missions.models import Task
from app.missions.repository import MissionRepository

SQLITE_MEMORY = "sqlite+aiosqlite:///:memory:"

_OBJECT_JSON = json.dumps({
    "summary": "Monitor Company X",
    "success_criteria": ["detect changes"],
    "horizon": "monitoring",
    "deadline_days": 30,
})
_PLAN_JSON = json.dumps([
    {"description": "Establish baseline", "depends_on": [], "role": "researcher"},
    {"description": "Detect anomalies", "depends_on": [0], "role": "analyst"},
    {"description": "Prepare report", "depends_on": [1], "role": "executor"},
])


async def _fake_chat(messages):
    system = messages[0]["content"].lower()
    return _PLAN_JSON if "mission planner" in system else _OBJECT_JSON


async def _record_executor(task: Task) -> str:
    return f"ran {task.id}"


@pytest.fixture
async def client():
    engine = db.get_engine(SQLITE_MEMORY)
    await db.init_models(engine)
    repo = MissionRepository(db.get_sessionmaker(engine))

    app.dependency_overrides[mapi.get_mission_repo] = lambda: repo
    app.dependency_overrides[mapi.get_chat_fn] = lambda: _fake_chat
    app.dependency_overrides[mapi.get_executor] = lambda: _record_executor

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        yield c

    app.dependency_overrides.clear()
    await engine.dispose()


async def _create(client, goal="watch company x", priority=0):
    r = await client.post("/missions", json={"goal": goal, "priority": priority})
    assert r.status_code == 201, r.text
    return r.json()


async def test_create_returns_mission_with_task_dag(client):
    body = await _create(client)
    assert body["status"] == "created"
    assert [t["description"] for t in body["tasks"]] == [
        "Establish baseline", "Detect anomalies", "Prepare report"]
    assert body["total"] == 3 and body["settled"] == 0
    # deps were wired to real task ids
    ids = [t["id"] for t in body["tasks"]]
    assert body["tasks"][1]["depends_on"] == [ids[0]]


async def test_get_and_list_missions(client):
    created = await _create(client)
    mid = created["id"]

    got = await client.get(f"/missions/{mid}")
    assert got.status_code == 200 and got.json()["id"] == mid

    listed = await client.get("/missions")
    assert listed.status_code == 200
    assert mid in [m["id"] for m in listed.json()]

    tasks = await client.get(f"/missions/{mid}/tasks")
    assert len(tasks.json()) == 3


async def test_get_missing_mission_is_404(client):
    r = await client.get("/missions/9999")
    assert r.status_code == 404


async def test_run_drives_mission_to_completion(client):
    mid = (await _create(client))["id"]
    r = await client.post(f"/missions/{mid}/run")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "completed"
    assert body["settled"] == body["total"] == 3
    assert all(t["status"] == "done" for t in body["tasks"])


async def test_tick_advances_one_layer(client):
    mid = (await _create(client))["id"]
    r = await client.post(f"/missions/{mid}/tick")
    assert r.status_code == 200
    body = r.json()
    assert len(body["ran"]) == 1  # only the root was ready
    assert body["status"] == "active"


async def test_pause_and_resume(client):
    mid = (await _create(client))["id"]
    await client.post(f"/missions/{mid}/tick")  # -> active

    paused = await client.post(f"/missions/{mid}/pause")
    assert paused.status_code == 200 and paused.json()["status"] == "paused"

    resumed = await client.post(f"/missions/{mid}/resume")
    assert resumed.status_code == 200 and resumed.json()["status"] == "active"


async def test_illegal_transition_is_409(client):
    mid = (await _create(client))["id"]
    # CREATED cannot go straight to PAUSED
    r = await client.post(f"/missions/{mid}/pause")
    assert r.status_code == 409
