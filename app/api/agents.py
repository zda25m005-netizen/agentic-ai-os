"""REST surface for user-created agents (Phase 3).

Owner-scoped CRUD plus character/template discovery. Running an agent creates a REAL
mission in the existing mission runtime (no fake execution). Kept thin: the repository owns
persistence + owner isolation, the mission runtime owns execution.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.agent_registry.characters import CHARACTERS
from app.agent_registry.models import Agent
from app.agent_registry.repository import AgentRepository
from app.agent_registry.templates import BUILTIN_TEMPLATES, TEMPLATE_MAP
from app.db import session as db
from app.missions.repository import MissionRepository

router = APIRouter(prefix="/agents", tags=["agents"])
characters_router = APIRouter(prefix="/characters", tags=["agents"])

_OWNER = "me"  # single-user today; owner isolation is enforced repository-side.


# --- dependencies (overridable in tests) -----------------------------------
def get_agent_repo() -> AgentRepository:
    return AgentRepository(db.get_sessionmaker())


def get_mission_repo() -> MissionRepository:
    return MissionRepository(db.get_sessionmaker())


def get_owner() -> str:
    return _OWNER


# --- schemas ---------------------------------------------------------------
class AgentIn(BaseModel):
    name: str | None = None
    description: str | None = None
    purpose: str | None = None
    instructions: str | None = None
    character_id: str | None = None
    tools: list[str] | None = None
    memory_config: dict | None = None
    knowledge_sources: list[str] | None = None
    model: dict | None = None  # -> stored as model_cfg (avoids pydantic model_config clash)
    schedule: dict | None = None
    trigger_config: dict | None = None
    approval_policy: dict | None = None
    personality: str | None = None
    template_id: str | None = None
    status: str | None = None


class AgentOut(BaseModel):
    id: str
    owner: str
    name: str
    description: str
    purpose: str
    instructions: str
    character_id: str
    tools: list[str]
    memory_config: dict
    knowledge_sources: list[str]
    model: dict
    schedule: dict
    trigger_config: dict
    approval_policy: dict
    personality: str
    template_id: str | None
    status: str
    created_at: float
    updated_at: float
    last_run_at: float | None = Field(default=None)


def to_out(a: Agent) -> AgentOut:
    return AgentOut(
        id=a.id,
        owner=a.owner,
        name=a.name,
        description=a.description,
        purpose=a.purpose,
        instructions=a.instructions,
        character_id=a.character_id,
        tools=a.tools,
        memory_config=a.memory_config,
        knowledge_sources=a.knowledge_sources,
        model=a.model_cfg,
        schedule=a.schedule,
        trigger_config=a.trigger_config,
        approval_policy=a.approval_policy,
        personality=a.personality,
        template_id=a.template_id,
        status=a.status,
        created_at=a.created_at,
        updated_at=a.updated_at,
        last_run_at=a.last_run_at,
    )


def _in_fields(req: AgentIn) -> dict:
    d = req.model_dump(exclude_unset=True)
    if "model" in d:  # map API 'model' -> ORM 'model_cfg'
        d["model_cfg"] = d.pop("model")
    return d


# --- character + template discovery ----------------------------------------
@characters_router.get("")
def list_characters() -> dict:
    return {"characters": CHARACTERS}


@router.get("/templates")
def list_templates() -> dict:
    return {"templates": BUILTIN_TEMPLATES}


class SpecReq(BaseModel):
    description: str


@router.post("/spec")
async def generate_agent_spec(req: SpecReq) -> dict:
    """Propose an agent specification from a natural-language description (not persisted).

    Deterministic; uses the LLM to refine only when MEMORY_POLICY-style config enables it and
    a model is available. Always returns a usable draft the user can edit before creating.
    """
    from app.agent_registry.spec import generate_spec
    from app.core import llm
    from app.core.config import get_settings

    use_llm = get_settings().memory_policy_mode == "llm" and llm.is_configured()
    spec = await generate_spec(req.description, llm.chat if use_llm else None, use_llm=use_llm)
    return {"spec": spec}


# --- CRUD ------------------------------------------------------------------
@router.get("")
async def list_agents(
    repo: AgentRepository = Depends(get_agent_repo),  # noqa: B008
    owner: str = Depends(get_owner),  # noqa: B008
) -> dict:
    agents = await repo.list(owner)
    return {"agents": [to_out(a).model_dump() for a in agents]}


@router.post("", status_code=201)
async def create_agent(
    req: AgentIn,
    repo: AgentRepository = Depends(get_agent_repo),  # noqa: B008
    owner: str = Depends(get_owner),  # noqa: B008
) -> AgentOut:
    fields = _in_fields(req)
    # Seed from a built-in template when template_id is given and fields are absent.
    tpl = TEMPLATE_MAP.get(req.template_id or "")
    if tpl:
        for k in (
            "name",
            "description",
            "purpose",
            "character_id",
            "tools",
            "memory_config",
            "personality",
            "approval_policy",
        ):
            fields.setdefault(k, tpl.get(k))
    agent = await repo.create(owner, **fields)
    return to_out(agent)


@router.get("/{agent_id}")
async def get_agent(
    agent_id: str,
    repo: AgentRepository = Depends(get_agent_repo),  # noqa: B008
    owner: str = Depends(get_owner),  # noqa: B008
) -> AgentOut:
    agent = await repo.get(owner, agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found.")
    return to_out(agent)


@router.put("/{agent_id}")
async def update_agent(
    agent_id: str,
    req: AgentIn,
    repo: AgentRepository = Depends(get_agent_repo),  # noqa: B008
    owner: str = Depends(get_owner),  # noqa: B008
) -> AgentOut:
    agent = await repo.update(owner, agent_id, **_in_fields(req))
    if not agent:
        raise HTTPException(404, "Agent not found.")
    return to_out(agent)


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    repo: AgentRepository = Depends(get_agent_repo),  # noqa: B008
    owner: str = Depends(get_owner),  # noqa: B008
) -> dict:
    ok = await repo.delete(owner, agent_id)
    if not ok:
        raise HTTPException(404, "Agent not found.")
    return {"deleted": True, "id": agent_id}


# --- lifecycle + execution (real) ------------------------------------------
class RunReq(BaseModel):
    task: str | None = None  # optional override objective


@router.post("/{agent_id}/run")
async def run_agent_endpoint(
    agent_id: str,
    req: RunReq | None = None,
    repo: AgentRepository = Depends(get_agent_repo),  # noqa: B008
    missions: MissionRepository = Depends(get_mission_repo),  # noqa: B008
    owner: str = Depends(get_owner),  # noqa: B008
) -> dict:
    agent = await repo.get(owner, agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found.")
    objective = (req.task if req and req.task else None) or agent.purpose or agent.name
    mission = await missions.create(
        objective=objective,
        meta={"agent_id": agent.id, "owner": owner, "character_id": agent.character_id},
    )
    await repo.touch_run(owner, agent_id)
    return {
        "agent_id": agent.id,
        "mission_id": mission.id,
        "objective": objective,
        "status": "working",
    }


@router.post("/{agent_id}/pause")
async def pause_agent(
    agent_id: str,
    repo: AgentRepository = Depends(get_agent_repo),  # noqa: B008
    owner: str = Depends(get_owner),  # noqa: B008
) -> AgentOut:
    agent = await repo.set_status(owner, agent_id, "paused")
    if not agent:
        raise HTTPException(404, "Agent not found.")
    return to_out(agent)


@router.post("/{agent_id}/resume")
async def resume_agent(
    agent_id: str,
    repo: AgentRepository = Depends(get_agent_repo),  # noqa: B008
    owner: str = Depends(get_owner),  # noqa: B008
) -> AgentOut:
    agent = await repo.set_status(owner, agent_id, "idle")
    if not agent:
        raise HTTPException(404, "Agent not found.")
    return to_out(agent)


async def _agent_missions(agent_id: str, missions: MissionRepository) -> list:
    all_m = await missions.list(limit=200)
    return [m for m in all_m if (m.meta or {}).get("agent_id") == agent_id]


@router.get("/{agent_id}/tasks")
async def agent_tasks(
    agent_id: str,
    repo: AgentRepository = Depends(get_agent_repo),  # noqa: B008
    missions: MissionRepository = Depends(get_mission_repo),  # noqa: B008
    owner: str = Depends(get_owner),  # noqa: B008
) -> dict:
    if not await repo.get(owner, agent_id):
        raise HTTPException(404, "Agent not found.")
    ms = await _agent_missions(agent_id, missions)
    return {
        "tasks": [
            {
                "mission_id": m.id,
                "objective": m.objective,
                "status": m.status.value,
                "created_at": m.created_at,
                "updated_at": m.updated_at,
            }
            for m in ms
        ]
    }


@router.get("/{agent_id}/activity")
async def agent_activity(
    agent_id: str,
    repo: AgentRepository = Depends(get_agent_repo),  # noqa: B008
    missions: MissionRepository = Depends(get_mission_repo),  # noqa: B008
    owner: str = Depends(get_owner),  # noqa: B008
) -> dict:
    if not await repo.get(owner, agent_id):
        raise HTTPException(404, "Agent not found.")
    ms = await _agent_missions(agent_id, missions)
    events = [
        {
            "type": "run",
            "mission_id": m.id,
            "summary": m.objective,
            "status": m.status.value,
            "at": m.updated_at,
        }
        for m in ms
    ]
    events.sort(key=lambda e: e["at"], reverse=True)
    return {"activity": events}


@router.get("/{agent_id}/memory")
async def agent_memory(
    agent_id: str,
    repo: AgentRepository = Depends(get_agent_repo),  # noqa: B008
    owner: str = Depends(get_owner),  # noqa: B008
) -> dict:
    if not await repo.get(owner, agent_id):
        raise HTTPException(404, "Agent not found.")
    # Real counts from the owner's memory store (no fabrication). Empty when none.
    try:
        from app.memory.orchestrator import MemoryOrchestrator

        stats = MemoryOrchestrator(owner=owner).stats()
        return {"count": stats.get("current", 0), "layers": stats.get("layers", {})}
    except Exception:
        return {"count": 0, "layers": {}}
