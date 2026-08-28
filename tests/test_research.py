"""Search-augmented researcher: real sources land in the task output + report."""
import app.missions.models  # noqa: F401  (register tables)
from app.db import session as db
from app.missions.agents import MultiAgentExecutor
from app.missions.repository import MissionRepository

SQLITE_MEMORY = "sqlite+aiosqlite:///:memory:"

_FAKE_RESULTS = [
    {"title": "CUDA moat", "snippet": "NVIDIA CUDA dominates AI training.",
     "url": "https://reuters.com/tech/nvidia-cuda"},
    {"title": "MI300X", "snippet": "AMD MI300X closes the gap.",
     "url": "https://amd.com/mi300x"},
]


async def _repo() -> MissionRepository:
    engine = db.get_engine(SQLITE_MEMORY)
    await db.init_models(engine)
    return MissionRepository(db.get_sessionmaker(engine))


async def _researcher_task(repo):
    m = await repo.create("NVIDIA vs AMD AI accelerators", meta={})
    t = await repo.add_task(m.id, "Assess ecosystem moats", depends_on=[])
    await repo.update_meta(m.id, {"roles": {str(t.id): "researcher"}})
    return (await repo.get_tasks(m.id))[0]


async def test_researcher_gathers_and_cites_real_sources():
    repo = await _repo()
    task = await _researcher_task(repo)
    seen = {}

    async def search(q):
        seen["query"] = q
        return _FAKE_RESULTS

    async def chat(messages):
        seen["user"] = messages[1]["content"]
        return "NVIDIA leads on ecosystem."  # LLM ignores URLs; we append them

    out = await MultiAgentExecutor(repo, chat_fn=chat, critic=None, search_fn=search)(task)
    # the query blended objective + task; results were passed into the prompt
    assert "ecosystem" in seen["query"] and "search results" in seen["user"].lower()
    # both real URLs are guaranteed present for the evidence ledger
    assert "https://reuters.com/tech/nvidia-cuda" in out
    assert "https://amd.com/mi300x" in out


async def test_llm_cited_urls_not_duplicated():
    repo = await _repo()
    task = await _researcher_task(repo)

    async def search(q):
        return _FAKE_RESULTS

    async def chat(messages):
        return "See https://amd.com/mi300x for AMD details."  # already cites one

    out = await MultiAgentExecutor(repo, chat_fn=chat, critic=None, search_fn=search)(task)
    assert out.count("https://amd.com/mi300x") == 1        # not duplicated
    assert "https://reuters.com/tech/nvidia-cuda" in out    # the missing one appended


async def test_no_search_fn_means_no_sources():
    repo = await _repo()
    task = await _researcher_task(repo)

    async def chat(messages):
        return "answer without sources"

    out = await MultiAgentExecutor(repo, chat_fn=chat, critic=None)(task)  # search_fn=None
    assert "http" not in out


async def test_non_researcher_role_skips_search():
    repo = await _repo()
    m = await repo.create("obj", meta={})
    t = await repo.add_task(m.id, "do it", depends_on=[])
    await repo.update_meta(m.id, {"roles": {str(t.id): "analyst"}})
    called = {"n": 0}

    async def search(q):
        called["n"] += 1
        return _FAKE_RESULTS

    async def chat(messages):
        return "analysis"

    tasks = await repo.get_tasks(m.id)
    await MultiAgentExecutor(repo, chat_fn=chat, critic=None, search_fn=search)(tasks[0])
    assert called["n"] == 0  # analyst role does not trigger web search
