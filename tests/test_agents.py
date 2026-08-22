"""Multi-agent executor: role prompts, critic accept/reject, bounded replan."""
import json

import app.missions.models  # noqa: F401  (register tables)
from app.db import session as db
from app.missions.agents import (
    ROLE_PROMPTS,
    Critic,
    MultiAgentExecutor,
    Verdict,
)
from app.missions.repository import MissionRepository

SQLITE_MEMORY = "sqlite+aiosqlite:///:memory:"


async def _repo() -> MissionRepository:
    engine = db.get_engine(SQLITE_MEMORY)
    await db.init_models(engine)
    return MissionRepository(db.get_sessionmaker(engine))


async def _task_with_role(repo, role):
    m = await repo.create("demo", meta={})
    t = await repo.add_task(m.id, "do the thing", depends_on=[])
    await repo.update_meta(m.id, {"roles": {str(t.id): role}})
    return await repo.get_tasks(m.id)


# --- critic ---

async def test_critic_accepts_good_answer():
    async def judge(messages):
        return json.dumps({"accepted": True, "score": 0.9, "feedback": ""})
    v = await Critic(judge).review("task", "answer")
    assert v.accepted and v.score == 0.9


async def test_critic_rejects_low_score():
    async def judge(messages):
        return json.dumps({"accepted": True, "score": 0.3, "feedback": "add detail"})
    v = await Critic(judge, threshold=0.6).review("task", "weak")
    assert not v.accepted  # score below threshold overrides "accepted"
    assert v.feedback == "add detail"


async def test_critic_falls_back_to_accept_on_garbage():
    async def judge(messages):
        return "not json"
    assert (await Critic(judge).review("t", "o")) == Verdict(True, 1.0, "")


# --- multi-agent executor ---

async def test_executor_uses_role_specific_prompt():
    repo = await _repo()
    tasks = await _task_with_role(repo, "analyst")
    seen = {}

    async def chat(messages):
        seen["system"] = messages[0]["content"]
        return "analysis done"

    # no critic -> single generation
    out = await MultiAgentExecutor(repo, chat_fn=chat, critic=None)(tasks[0])
    assert out == "analysis done"
    assert seen["system"] == ROLE_PROMPTS["analyst"]


async def test_executor_replans_on_critic_rejection():
    repo = await _repo()
    tasks = await _task_with_role(repo, "researcher")
    gen = {"n": 0}

    async def chat(messages):
        role_system = messages[0]["content"]
        if role_system.startswith("You are a strict Critic"):
            # reject the first answer, accept the second
            accept = gen["n"] >= 2
            return json.dumps({"accepted": accept, "score": 0.9 if accept else 0.2,
                               "feedback": "cite sources"})
        gen["n"] += 1
        return f"draft {gen['n']}"

    critic = Critic(chat, threshold=0.6)
    out = await MultiAgentExecutor(repo, chat_fn=chat, critic=critic, max_replans=2)(tasks[0])
    assert gen["n"] == 2  # regenerated once after the rejection
    assert out == "draft 2"


async def test_executor_defaults_role_to_executor():
    repo = await _repo()
    m = await repo.create("demo", meta={})  # no roles map
    await repo.add_task(m.id, "just do it", depends_on=[])
    seen = {}

    async def chat(messages):
        seen["system"] = messages[0]["content"]
        return "done"

    tasks = await repo.get_tasks(m.id)
    await MultiAgentExecutor(repo, chat_fn=chat, critic=None)(tasks[0])
    assert seen["system"] == ROLE_PROMPTS["executor"]
