"""REST surface for the mission runtime: create, inspect, drive, pause/resume.

A thin HTTP layer over the mission package — the repository owns persistence and
the state machine, the runtime owns execution, and this router just translates
between them and JSON. Dependencies (`get_mission_repo`, `get_chat_fn`,
`get_executor`) are injected so tests can run the whole surface offline.
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core import llm
from app.db import session as db
from app.exec.pdf import PdfDoc, Section, build_pdf
from app.missions.agents import build_executor
from app.missions.builder import build_mission
from app.missions.executor import TaskExecutor
from app.missions.models import Mission, Task
from app.missions.repository import MissionRepository
from app.missions.runtime import MissionRuntime
from app.missions.state import InvalidTransition, MissionStatus
from app.missions.task_graph import progress

router = APIRouter(prefix="/missions", tags=["missions"])

ChatFn = Callable[[list[dict]], Awaitable[str]]


# --- dependencies (overridden in tests) ---

def get_mission_repo() -> MissionRepository:
    return MissionRepository(db.get_sessionmaker())


def get_chat_fn() -> ChatFn:
    return llm.chat


def get_executor() -> TaskExecutor:
    return build_executor(MissionRepository(db.get_sessionmaker()))


# --- schemas ---

class CreateMissionRequest(BaseModel):
    goal: str
    priority: int = 0


class TaskOut(BaseModel):
    id: int
    description: str
    status: str
    depends_on: list[int]
    result: str | None = None


class MissionOut(BaseModel):
    id: int
    objective: str
    status: str
    priority: int
    deadline: float | None = None
    settled: int = Field(..., description="tasks that are done/skipped/failed")
    total: int
    tasks: list[TaskOut]
    usage: dict = Field(default_factory=dict, description="usd/tokens/llm_calls so far")
    created_at: float | None = None


class TickOut(BaseModel):
    mission_id: int
    status: str
    ran: list[int]
    failed: list[int]


# --- assembly ---

def _task_out(t: Task) -> TaskOut:
    return TaskOut(
        id=t.id, description=t.description, status=t.status.value,
        depends_on=t.depends_on, result=t.result,
    )


def _mission_out(m: Mission, tasks: list[Task]) -> MissionOut:
    settled, total = progress(tasks)
    return MissionOut(
        id=m.id, objective=m.objective, status=m.status.value, priority=m.priority,
        deadline=m.deadline, settled=settled, total=total,
        tasks=[_task_out(t) for t in tasks],
        usage=(m.meta.get("usage") or {}) if m.meta else {},
        created_at=m.created_at,
    )


async def _load_or_404(repo: MissionRepository, mission_id: int) -> Mission:
    mission = await repo.get(mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail=f"mission {mission_id} not found")
    return mission


# --- read endpoints ---

@router.get("", response_model=list[MissionOut])
async def list_missions(
    status: MissionStatus | None = Query(default=None),  # noqa: B008
    repo: MissionRepository = Depends(get_mission_repo),  # noqa: B008
) -> list[MissionOut]:
    """List missions (newest priority first), optionally filtered by status."""
    missions = await repo.list(status=status)
    out = []
    for m in missions:
        out.append(_mission_out(m, await repo.get_tasks(m.id)))
    return out


@router.get("/{mission_id}", response_model=MissionOut)
async def get_mission(
    mission_id: int,
    repo: MissionRepository = Depends(get_mission_repo),  # noqa: B008
) -> MissionOut:
    """Fetch a mission with its task DAG and progress."""
    mission = await _load_or_404(repo, mission_id)
    return _mission_out(mission, await repo.get_tasks(mission_id))


@router.get("/{mission_id}/tasks", response_model=list[TaskOut])
async def get_mission_tasks(
    mission_id: int,
    repo: MissionRepository = Depends(get_mission_repo),  # noqa: B008
) -> list[TaskOut]:
    """Fetch just the tasks of a mission."""
    await _load_or_404(repo, mission_id)
    return [_task_out(t) for t in await repo.get_tasks(mission_id)]


def _mission_pdf(mission: Mission, tasks: list[Task]) -> bytes:
    """Build a report PDF from a mission's real objective, tasks, and results."""
    usage = (mission.meta.get("usage") or {}) if mission.meta else {}
    settled, total = progress(tasks)
    sections = [
        Section("Summary",
                f"Status: {mission.status.value}\nTasks: {settled}/{total} settled\n"
                f"Tokens: {usage.get('tokens', 0)}   Cost: ${usage.get('usd', 0):.4f}"),
    ]
    for t in tasks:
        deps = ", ".join(f"#{d}" for d in t.depends_on) or "none"
        body = (t.result or "(no result)") + f"\n\n[status: {t.status.value} · depends on: {deps}]"
        sections.append(Section(f"Task #{t.id}: {t.description}", body))
    return build_pdf(PdfDoc(title=f"Mission #{mission.id}: {mission.objective}", sections=sections))


@router.get("/{mission_id}/report.pdf")
async def mission_report_pdf(
    mission_id: int,
    repo: MissionRepository = Depends(get_mission_repo),  # noqa: B008
) -> Response:
    """Generate and download a real PDF report of the mission (the pdf.create tool)."""
    mission = await _load_or_404(repo, mission_id)
    pdf = _mission_pdf(mission, await repo.get_tasks(mission_id))
    return Response(
        content=pdf, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="mission-{mission_id}.pdf"'},
    )


@router.get("/{mission_id}/stream")
async def stream_mission(
    mission_id: int,
    interval: float = Query(default=1.0, ge=0.1, le=10.0),  # noqa: B008
    max_seconds: float = Query(default=600.0, ge=1.0),  # noqa: B008
    repo: MissionRepository = Depends(get_mission_repo),  # noqa: B008
) -> StreamingResponse:
    """Server-Sent Events stream of a mission's live state until it terminates."""
    await _load_or_404(repo, mission_id)

    async def events():
        last = None
        elapsed = 0.0
        while elapsed <= max_seconds:
            mission = await repo.get(mission_id)
            if mission is None:
                break
            payload = _mission_out(mission, await repo.get_tasks(mission_id)).model_dump()
            snap = json.dumps(payload, sort_keys=True)
            if snap != last:  # only push on change
                last = snap
                yield f"data: {snap}\n\n"
            if mission.status in (MissionStatus.COMPLETED, MissionStatus.FAILED):
                yield "event: done\ndata: {}\n\n"
                return
            await asyncio.sleep(interval)
            elapsed += interval

    return StreamingResponse(events(), media_type="text/event-stream")


# --- create + drive endpoints ---

@router.post("", response_model=MissionOut, status_code=201)
async def create_mission(
    req: CreateMissionRequest,
    repo: MissionRepository = Depends(get_mission_repo),  # noqa: B008
    chat_fn: ChatFn = Depends(get_chat_fn),  # noqa: B008
) -> MissionOut:
    """Turn a raw goal into a persisted mission with a wired task DAG."""
    try:
        mission = await build_mission(repo, req.goal, chat_fn=chat_fn, priority=req.priority)
    except Exception as exc:  # planning/LLM failure -> 502, not a 500
        raise HTTPException(status_code=502, detail=f"could not plan mission: {exc}") from exc
    return _mission_out(mission, await repo.get_tasks(mission.id))


@router.post("/{mission_id}/tick", response_model=TickOut)
async def tick_mission(
    mission_id: int,
    repo: MissionRepository = Depends(get_mission_repo),  # noqa: B008
    executor: TaskExecutor = Depends(get_executor),  # noqa: B008
) -> TickOut:
    """Advance the mission by one DAG layer and report what ran."""
    await _load_or_404(repo, mission_id)
    result = await MissionRuntime(repo, executor).tick(mission_id)
    return TickOut(
        mission_id=mission_id, status=result.status.value,
        ran=result.ran, failed=result.failed,
    )


@router.post("/{mission_id}/run", response_model=MissionOut)
async def run_mission(
    mission_id: int,
    max_ticks: int = Query(default=100, ge=1, le=1000),  # noqa: B008
    repo: MissionRepository = Depends(get_mission_repo),  # noqa: B008
    executor: TaskExecutor = Depends(get_executor),  # noqa: B008
) -> MissionOut:
    """Drive the mission to a terminal (or paused) state, then return it."""
    await _load_or_404(repo, mission_id)
    mission = await MissionRuntime(repo, executor).run(mission_id, max_ticks=max_ticks)
    return _mission_out(mission, await repo.get_tasks(mission_id))


@router.post("/{mission_id}/pause", response_model=MissionOut)
async def pause_mission(
    mission_id: int,
    repo: MissionRepository = Depends(get_mission_repo),  # noqa: B008
) -> MissionOut:
    """Pause an active mission (rejected with 409 if the transition is illegal)."""
    return await _transition(repo, mission_id, MissionStatus.PAUSED)


@router.post("/{mission_id}/resume", response_model=MissionOut)
async def resume_mission(
    mission_id: int,
    repo: MissionRepository = Depends(get_mission_repo),  # noqa: B008
) -> MissionOut:
    """Resume a paused mission back to active."""
    return await _transition(repo, mission_id, MissionStatus.ACTIVE)


async def _transition(
    repo: MissionRepository, mission_id: int, target: MissionStatus
) -> MissionOut:
    await _load_or_404(repo, mission_id)
    try:
        mission = await repo.set_status(mission_id, target)
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _mission_out(mission, await repo.get_tasks(mission_id))
