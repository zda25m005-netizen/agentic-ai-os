"""Agent registry (Phase 3): persistence, owner isolation, character assignment, templates."""

import app.agent_registry.models  # noqa: F401  (registers agents table on Base)
from app.agent_registry.characters import CHARACTER_IDS, pick_available_character
from app.agent_registry.repository import AgentRepository
from app.agent_registry.templates import BUILTIN_TEMPLATES, TEMPLATE_MAP
from app.db import session as db

SQLITE_MEMORY = "sqlite+aiosqlite:///:memory:"


async def _repo():
    engine = db.get_engine(SQLITE_MEMORY)
    await db.init_models(engine)
    return AgentRepository(db.get_sessionmaker(engine)), engine


async def test_create_persists_and_autoassigns_character():
    repo, engine = await _repo()
    try:
        a = await repo.create("me", name="Job Scout", purpose="Find ML jobs")
        assert a.id.startswith("agent-")
        assert a.owner == "me" and a.name == "Job Scout"
        assert a.character_id in CHARACTER_IDS  # auto-assigned
        got = await repo.get("me", a.id)
        assert got is not None and got.id == a.id  # persisted
    finally:
        await engine.dispose()


async def test_auto_assignment_avoids_duplicates():
    repo, engine = await _repo()
    try:
        seen = set()
        for i in range(5):
            a = await repo.create("me", name=f"A{i}")
            assert a.character_id not in seen  # unique while characters remain
            seen.add(a.character_id)
    finally:
        await engine.dispose()


async def test_owner_isolation():
    repo, engine = await _repo()
    try:
        mine = await repo.create("me", name="Mine")
        await repo.create("alice", name="Hers")
        assert await repo.get("alice", mine.id) is None  # cannot read across owners
        assert [a.name for a in await repo.list("me")] == ["Mine"]
        assert [a.name for a in await repo.list("alice")] == ["Hers"]
        assert await repo.delete("alice", mine.id) is False  # cannot delete across owners
        assert await repo.get("me", mine.id) is not None
    finally:
        await engine.dispose()


async def test_update_and_delete():
    repo, engine = await _repo()
    try:
        a = await repo.create("me", name="X", character_id="nova")
        upd = await repo.update("me", a.id, name="Y", character_id="luna", tools=["web_search"])
        assert upd.name == "Y" and upd.character_id == "luna" and upd.tools == ["web_search"]
        upd2 = await repo.update("me", a.id, character_id="not-a-real-character")
        assert upd2.character_id == "luna"  # invalid character ignored
        assert await repo.delete("me", a.id) is True
        assert await repo.get("me", a.id) is None
    finally:
        await engine.dispose()


async def test_character_persists_across_reads():
    repo, engine = await _repo()
    try:
        a = await repo.create("me", name="Z", character_id="rory")
        again = await repo.get("me", a.id)
        assert again.character_id == "rory"  # survives (persisted, not random)
    finally:
        await engine.dispose()


def test_pick_available_character():
    assert pick_available_character([]) == CHARACTER_IDS[0]
    assert pick_available_character([CHARACTER_IDS[0]]) == CHARACTER_IDS[1]
    # all used -> reuse (returns first), never crashes
    assert pick_available_character(CHARACTER_IDS) == CHARACTER_IDS[0]


def test_builtin_templates_present():
    ids = {t["id"] for t in BUILTIN_TEMPLATES}
    for expected in (
        "job-search",
        "research",
        "resume-optimizer",
        "sop-builder",
        "scholarship-finder",
        "phd-finder",
        "interview-coach",
    ):
        assert expected in ids
    assert TEMPLATE_MAP["job-search"]["route"] == "jobs"
    # every template references a real character id
    assert all(t["character_id"] in CHARACTER_IDS for t in BUILTIN_TEMPLATES)
