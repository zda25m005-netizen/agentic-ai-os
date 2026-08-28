"""Critic topic-drift detection: heuristic + executor flag + report surfacing."""
import json

import app.missions.models  # noqa: F401  (register tables)
from app.db import session as db
from app.missions.agents import MultiAgentExecutor, detect_topic_drift
from app.missions.repository import MissionRepository

SQLITE_MEMORY = "sqlite+aiosqlite:///:memory:"

_OBJECTIVE = ("Evaluate three approaches to giving LLM agents long-term memory: "
              "vector retrieval (RAG), fine-tuning, and structured memory stores.")
_ON = ("Vector retrieval (RAG) offers the freshest memory for LLM agents, while "
       "fine-tuning bakes knowledge into weights and structured memory stores give "
       "explicit recall. Each approach trades off freshness, cost, and accuracy.")
_OFF = ("Software delivery methodologies include Waterfall, Agile, DevOps, Lean, and "
        "Design Thinking. Waterfall is sequential while Agile is iterative with sprints "
        "and continuous delivery pipelines for shipping product increments.")


def test_on_topic_not_flagged():
    v = detect_topic_drift(_OBJECTIVE, "Compare the approaches", _ON)
    assert v.drifted is False


def test_off_topic_flagged():
    v = detect_topic_drift(_OBJECTIVE, "Compare the approaches", _OFF)
    assert v.drifted is True
    assert v.overlap < 0.12 and v.note


def test_short_output_never_flagged():
    assert detect_topic_drift(_OBJECTIVE, "task", "Waterfall and Agile.").drifted is False


async def _repo() -> MissionRepository:
    engine = db.get_engine(SQLITE_MEMORY)
    await db.init_models(engine)
    return MissionRepository(db.get_sessionmaker(engine))


async def test_executor_flags_drift_and_regenerates():
    repo = await _repo()
    m = await repo.create(_OBJECTIVE, meta={})
    t = await repo.add_task(m.id, "Compare the approaches", depends_on=[])
    tasks = await repo.get_tasks(m.id)
    calls = {"n": 0}

    async def chat(messages):
        # first worker call -> off-topic; regeneration -> on-topic. (no critic)
        if messages[0]["content"].startswith("You are a strict Critic"):
            return json.dumps({"accepted": True, "score": 1.0, "feedback": ""})
        calls["n"] += 1
        return _OFF if calls["n"] == 1 else _ON

    out = await MultiAgentExecutor(repo, chat_fn=chat, critic=None)(tasks[0])
    assert calls["n"] == 2          # regenerated after drift
    assert out == _ON
    # flag persisted to mission meta
    refreshed = await repo.get(m.id)
    flags = refreshed.meta.get("critic_flags")
    assert flags and flags[0]["type"] == "topic_drift" and flags[0]["task_id"] == t.id


async def test_no_drift_single_generation():
    repo = await _repo()
    m = await repo.create(_OBJECTIVE, meta={})
    await repo.add_task(m.id, "Compare the approaches", depends_on=[])
    tasks = await repo.get_tasks(m.id)
    calls = {"n": 0}

    async def chat(messages):
        calls["n"] += 1
        return _ON

    out = await MultiAgentExecutor(repo, chat_fn=chat, critic=None)(tasks[0])
    assert calls["n"] == 1 and out == _ON
    refreshed = await repo.get(m.id)
    assert not refreshed.meta.get("critic_flags")
