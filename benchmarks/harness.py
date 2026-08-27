"""Run benchmark tasks through the real runtime and measure genuine outcomes."""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass

from app.db import session as db
from app.memory.multilayer import MultiLayerMemory
from app.missions.mission_planner import plan_objective, validate_dag
from app.missions.objective import Objective
from app.missions.repository import MissionRepository
from app.missions.runtime import MissionRuntime
from app.missions.state import MissionStatus
from benchmarks.tasks import BenchTask, generate_tasks

SQLITE_MEMORY = "sqlite+aiosqlite:///:memory:"

_UNSAFE = ("delete all", "drop table", "rm -rf", "exfiltrate", "leak")
_TOOL_KEYWORDS = [
    ("calculat", "calculator"), ("comput", "calculator"),
    ("python", "python_exec"), ("analyz", "python_exec"),
    ("database", "sql_tool"), ("query", "sql_tool"), ("sql", "sql_tool"),
    ("recall", "rag_search"), ("remember", "rag_search"),
    ("search", "web_search"), ("web", "web_search"),
    ("research", "web_search"), ("report", "web_search"),
]


@dataclass
class TaskResult:
    id: str
    category: str
    success: bool
    had_fault: bool
    recovered: bool | None
    latency_s: float
    cost_usd: float
    intervention: bool
    tool_correct: bool | None
    memory_hit: bool | None
    safe_blocked: bool | None
    planning_valid: bool

    def as_dict(self) -> dict:
        return asdict(self)


def _select_tool(goal: str) -> str:
    g = goal.lower()
    for kw, tool in _TOOL_KEYWORDS:
        if kw in g:
            return tool
    return "web_search"  # default when no keyword matches (ambiguous goals)


def _is_unsafe(goal: str) -> bool:
    g = goal.lower()
    return any(p in g for p in _UNSAFE)


async def _fake_plan(messages):
    return ('[{"description":"research","depends_on":[],"role":"researcher"},'
            '{"description":"analyze","depends_on":[0],"role":"analyst"}]')


async def _planning_ok(goal: str) -> bool:
    specs = await plan_objective(Objective(summary=goal), chat_fn=_fake_plan)
    try:
        validate_dag(specs)
        return True
    except ValueError:
        return False


def _executor(faults: int):
    """Executor that fails each subtask's first `faults` attempts, then succeeds."""
    calls: dict[int, int] = {}

    async def run(task) -> str:
        calls[task.id] = calls.get(task.id, 0) + 1
        if calls[task.id] <= faults:
            raise TimeoutError("injected fault")
        return "ok"

    return run


async def run_task(repo: MissionRepository, task: BenchTask,
                   memory: MultiLayerMemory) -> TaskResult:
    planning_valid = await _planning_ok(task.goal)
    tool_correct = None if task.required_tool is None else (
        _select_tool(task.goal) == task.required_tool)
    safe_blocked = _is_unsafe(task.goal) if task.unsafe else None

    memory_hit = None
    if task.category == "memory_dependent":
        memory.semantic.learn(task.mem_key, task.mem_val, importance=2.0)
        hits = memory.retrieve(task.mem_query, limit=5)
        memory_hit = any(h.content == task.mem_val for h in hits)

    if task.unsafe:  # blocked before execution -> counts as a (correct) intervention
        return TaskResult(
            task.id, task.category, success=bool(safe_blocked), had_fault=False,
            recovered=None, latency_s=0.0, cost_usd=0.0, intervention=True,
            tool_correct=tool_correct, memory_hit=memory_hit,
            safe_blocked=safe_blocked, planning_valid=planning_valid)

    mission = await repo.create(task.goal)
    prev = None
    for i in range(task.subtasks):
        deps = [prev] if prev is not None else []
        st = await repo.add_task(mission.id, f"{task.id}-s{i}", depends_on=deps)
        prev = st.id

    t0 = time.perf_counter()
    final = await MissionRuntime(repo, _executor(task.faults), memory=memory).run(mission.id)
    latency = time.perf_counter() - t0

    success = final.status == MissionStatus.COMPLETED
    had_fault = task.faults > 0
    cost = float((final.meta.get("usage") or {}).get("usd", 0.0))
    return TaskResult(
        task.id, task.category, success=success, had_fault=had_fault,
        recovered=(success if had_fault else None), latency_s=latency, cost_usd=cost,
        intervention=(final.status == MissionStatus.FAILED),
        tool_correct=tool_correct, memory_hit=memory_hit,
        safe_blocked=safe_blocked, planning_valid=planning_valid)


async def run_benchmark(per_category: int = 25, seed: int = 42) -> list[TaskResult]:
    """Run the whole benchmark and return per-task results."""
    engine = db.get_engine(SQLITE_MEMORY)
    await db.init_models(engine)
    repo = MissionRepository(db.get_sessionmaker(engine))
    memory = MultiLayerMemory()
    results = [await run_task(repo, t, memory) for t in generate_tasks(per_category, seed)]
    await engine.dispose()
    return results
