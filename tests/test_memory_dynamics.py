"""Memory dynamics: reinforcement, decay/prune, consolidation, conflicts."""
import app.missions.models  # noqa: F401  (register tables)
from app.db import session as db
from app.memory.dynamics import MemoryDynamics
from app.memory.multilayer import MultiLayerMemory
from app.missions.repository import MissionRepository
from app.missions.runtime import MissionRuntime
from app.missions.state import MissionStatus

T0 = 1_000_000.0
HOUR = 3600.0


def test_retrieve_reinforces_accessed_items():
    m = MultiLayerMemory()
    m.semantic.learn("k", "a fact about anomaly", importance=1.0)
    dyn = MemoryDynamics(m, access_boost=0.5)
    before = m.semantic.get("k")
    hits = dyn.retrieve("anomaly", now=T0)
    assert before == "a fact about anomaly"
    assert hits[0].importance == 1.5      # boosted
    assert hits[0].access_count == 1


def test_decay_reduces_importance_over_time():
    m = MultiLayerMemory()
    item = m.organizational.share("policy note", importance=1.0)
    dyn = MemoryDynamics(m, decay_rate=0.1)
    dyn.decay(now=item.last_access + 10 * HOUR)  # 10h later
    assert item.importance < 1.0             # decayed
    assert item.importance > 0.0


def test_decay_prunes_weak_items_but_keeps_procedures():
    m = MultiLayerMemory()
    m.organizational.share("trivia", importance=0.05)      # below prune threshold
    m.procedural.learn("deploy", ["build", "push"])        # importance 1.0, exempt
    dyn = MemoryDynamics(m, decay_rate=0.0, prune_threshold=0.1)
    pruned = dyn.decay(now=T0)
    assert pruned == 1
    assert len(m.organizational) == 0
    assert m.procedural.get("deploy") is not None          # procedures persist


def test_consolidation_promotes_important_working_notes():
    m = MultiLayerMemory()
    m.working.note("trivial thought")                      # importance 1.0
    hot = m.working.note("critical finding")
    hot.importance = 3.0                                    # above threshold
    dyn = MemoryDynamics(m, consolidate_threshold=2.0)

    promoted = dyn.consolidate(now=T0)
    assert promoted == 1
    assert any("critical finding" in e.content for e in m.episodic.all())
    assert [w.content for w in m.working.all()] == ["trivial thought"]


def test_conflict_resolution_keeps_higher_importance():
    m = MultiLayerMemory()
    dyn = MemoryDynamics(m)
    assert dyn.assert_fact("ceo", "Alice", importance=1.0, now=T0) == "new"
    assert dyn.assert_fact("ceo", "Alice", importance=1.0, now=T0) == "reinforced"
    assert dyn.assert_fact("ceo", "Bob", importance=2.0, now=T0) == "overridden"
    assert m.semantic.get("ceo") == "Bob"
    # a weaker contradicting claim is rejected
    assert dyn.assert_fact("ceo", "Carol", importance=0.5, now=T0) == "kept_existing"
    assert m.semantic.get("ceo") == "Bob"


# --- runtime integration ---

async def _repo():
    engine = db.get_engine("sqlite+aiosqlite:///:memory:")
    await db.init_models(engine)
    return MissionRepository(db.get_sessionmaker(engine))


async def test_runtime_records_episodic_memory():
    repo = await _repo()
    mission = await repo.create("demo")
    await repo.add_task(mission.id, "step 0", depends_on=[])

    mem = MultiLayerMemory()

    async def ok(task):
        return "done"

    final = await MissionRuntime(repo, ok, memory=mem).run(mission.id)
    assert final.status == MissionStatus.COMPLETED
    # the tick recorded an episodic trace
    assert any("mission" in e.content for e in mem.episodic.all())
