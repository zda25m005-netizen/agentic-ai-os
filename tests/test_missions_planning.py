"""Goal interpreter + mission planner + builder tests (fake LLM, in-memory DB)."""
import json

import pytest

import app.missions.models  # noqa: F401  (register tables)
from app.db import session as db
from app.missions.builder import build_mission
from app.missions.goal_interpreter import interpret_goal
from app.missions.mission_planner import (
    SubgoalSpec,
    plan_objective,
    validate_dag,
)
from app.missions.objective import Objective
from app.missions.repository import MissionRepository

SQLITE_MEMORY = "sqlite+aiosqlite:///:memory:"

_OBJECT_JSON = json.dumps({
    "summary": "Monitor Company X filings",
    "success_criteria": ["detect material changes"],
    "constraints": ["notify only on strong evidence"],
    "notify_conditions": ["strong evidence"],
    "deadline_days": 30,
    "horizon": "monitoring",
})
_PLAN_JSON = json.dumps([
    {"description": "Establish baseline", "depends_on": [], "role": "researcher"},
    {"description": "Detect anomalies", "depends_on": [0], "role": "analyst"},
    {"description": "Prepare report", "depends_on": [1], "role": "executor"},
])


def make_fake(object_json=_OBJECT_JSON, plan_json=_PLAN_JSON):
    async def fake(messages):
        system = messages[0]["content"].lower()
        return plan_json if "mission planner" in system else object_json
    return fake


# --- interpreter ---

async def test_interpret_goal_parses_structured_objective():
    obj = await interpret_goal("watch company x", chat_fn=make_fake())
    assert obj.summary == "Monitor Company X filings"
    assert obj.horizon == "monitoring"
    assert obj.deadline_days == 30
    assert obj.notify_conditions == ["strong evidence"]


async def test_interpret_goal_falls_back_on_garbage():
    async def bad(messages):
        return "not json at all"
    obj = await interpret_goal("just answer this", chat_fn=bad)
    assert obj.summary == "just answer this"
    assert obj.horizon == "one_shot"


# --- planner + DAG ---

async def test_plan_objective_returns_dag():
    specs = await plan_objective(Objective(summary="x"), chat_fn=make_fake())
    assert [s.role for s in specs] == ["researcher", "analyst", "executor"]
    assert specs[1].depends_on == [0] and specs[2].depends_on == [1]
    validate_dag(specs)  # should not raise


async def test_plan_objective_falls_back_when_empty():
    async def empty(messages):
        return "[]"
    specs = await plan_objective(Objective(summary="x"), chat_fn=empty)
    assert len(specs) == 3  # research -> analyze -> report fallback


def test_validate_dag_rejects_forward_dependency():
    bad = [SubgoalSpec("a", [1]), SubgoalSpec("b", [])]  # 0 depends on 1 (forward)
    with pytest.raises(ValueError, match="forward"):
        validate_dag(bad)


# --- builder (end to end, persisted) ---

async def test_build_mission_persists_wired_task_dag():
    engine = db.get_engine(SQLITE_MEMORY)
    await db.init_models(engine)
    repo = MissionRepository(db.get_sessionmaker(engine))

    mission = await build_mission(repo, "watch company x", chat_fn=make_fake())
    assert mission.meta["objective"]["horizon"] == "monitoring"
    assert mission.deadline is not None  # 30 days -> a timestamp

    tasks = await repo.get_tasks(mission.id)
    assert [t.description for t in tasks] == [
        "Establish baseline", "Detect anomalies", "Prepare report"]
    # subgoal indices were translated into real task ids
    assert tasks[1].depends_on == [tasks[0].id]
    assert tasks[2].depends_on == [tasks[1].id]
    await engine.dispose()
