"""Agent evaluation: measure multi-step task success.

Runs the full agent graph on a set of goals and scores each run on three
axes: did the final answer contain the expected facts (task success), did
the Planner produce enough steps, and did every step complete. Aggregated,
these give a "task success rate" — the agent-layer analogue of the RAG
metrics from Week 3.

The runner takes an injectable `run_fn` (goal -> final state) so tests run
offline; the real command uses `app.agents.graph.run_agent`.
"""
from __future__ import annotations

import asyncio
import json
import statistics
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path

from app.agents.state import AgentState
from eval.scorers import normalize

_DATA_DIR = Path(__file__).parent / "datasets"
TASKS_PATH = _DATA_DIR / "agent_tasks.json"

RunFn = Callable[[str], Awaitable[AgentState]]


@dataclass(frozen=True)
class AgentTask:
    id: str
    goal: str
    expected_keywords: list[str]
    min_steps: int = 1


@dataclass
class AgentEvalReport:
    n: int
    task_success: float
    completion_rate: float
    avg_steps: float
    per_task: list[dict] = field(default_factory=list)


def load_tasks(path: Path = TASKS_PATH) -> list[AgentTask]:
    data = json.loads(Path(path).read_text())
    return [
        AgentTask(
            id=d["id"],
            goal=d["goal"],
            expected_keywords=[k.lower() for k in d["expected_keywords"]],
            min_steps=d.get("min_steps", 1),
        )
        for d in data
    ]


def score_task(task: AgentTask, state: AgentState) -> dict:
    """Score one completed agent run against its task."""
    answer = normalize(state.get("answer", ""))
    plan = state.get("plan", [])
    success = 1.0 if all(normalize(k) in answer for k in task.expected_keywords) else 0.0
    completed = 1.0 if plan and all(s.get("status") == "done" for s in plan) else 0.0
    enough_steps = len(plan) >= task.min_steps
    return {
        "id": task.id,
        "success": success if enough_steps else 0.0,
        "completed": completed,
        "steps": len(plan),
    }


async def run_agent_eval(tasks: list[AgentTask], run_fn: RunFn) -> AgentEvalReport:
    successes, completions, steps, per_task = [], [], [], []
    for task in tasks:
        state = await run_fn(task.goal)
        row = score_task(task, state)
        successes.append(row["success"])
        completions.append(row["completed"])
        steps.append(row["steps"])
        per_task.append(row)
    return AgentEvalReport(
        n=len(tasks),
        task_success=statistics.mean(successes) if successes else 0.0,
        completion_rate=statistics.mean(completions) if completions else 0.0,
        avg_steps=statistics.mean(steps) if steps else 0.0,
        per_task=per_task,
    )


def format_report_md(report: AgentEvalReport) -> str:
    rows = [
        ("Tasks", str(report.n)),
        ("Task success rate", f"{report.task_success:.0%}"),
        ("Step completion rate", f"{report.completion_rate:.0%}"),
        ("Avg steps / task", f"{report.avg_steps:.1f}"),
    ]
    lines = ["| Metric | Score |", "|---|---|"]
    lines += [f"| {name} | {value} |" for name, value in rows]
    return "\n".join(lines)


async def main() -> int:
    from app.agents.graph import run_agent
    from app.core import llm

    if not llm.is_configured():
        print("LLM not configured. Set OPENAI_API_KEY or LLM_BASE_URL.", file=sys.stderr)
        return 1

    tasks = load_tasks()
    report = await run_agent_eval(tasks, run_agent)
    print(format_report_md(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
