"""Memory API — exposes the canonical MemoryOrchestrator over HTTP.

Backs the frontend Memory page with REAL records (previously it used sample data).
Single-user 'me' owner for now; the store is owner-isolated so multi-user is a
drop-in later.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.memory.orchestrator import MemoryOrchestrator
from app.memory.records import MemoryRecord

router = APIRouter(prefix="/memory", tags=["memory"])
_OWNER = "me"


def _orch() -> MemoryOrchestrator:
    return MemoryOrchestrator(owner=_OWNER)


def _iso(ts: float | None) -> str | None:
    return datetime.fromtimestamp(ts, tz=UTC).isoformat() if ts else None


def to_ui(r: MemoryRecord) -> dict:
    return {
        "id": r.id,
        "layer": r.memory_type,
        "content": r.content,
        "importance": round(min(1.0, r.importance / 3.0), 3),
        "strength": r.strength(),
        "confidence": round(r.confidence, 3),
        "status": r.status,
        "createdAt": _iso(r.created_at),
        "lastRetrieved": _iso(r.last_accessed_at),
        "retrievals": r.access_count,
        "source": r.source,
        "provenance": r.provenance,
        "mission": {"id": r.mission_id, "title": f"Mission {r.mission_id}"}
        if r.mission_id
        else None,
        "tags": r.tags,
        "pinned": r.pinned,
        "supersedes": r.supersedes_id,
    }


class AddReq(BaseModel):
    content: str
    layer: str = "semantic"
    key: str | None = None
    tags: list[str] = Field(default_factory=list)
    source: str = "user"
    confidence: float = 0.8
    importance: float = 1.0
    pinned: bool = False
    provenance: str | None = None


class UpdateReq(BaseModel):
    content: str | None = None
    tags: list[str] | None = None
    importance: float | None = None
    pinned: bool | None = None


class SearchReq(BaseModel):
    query: str
    token_budget: int | None = None
    limit: int = 8


@router.get("/list")
def list_memory(
    layer: str | None = None, status: str | None = None, include_archived: bool = False
) -> dict:
    from app.memory import store

    recs = store.query(_OWNER, layer=layer, status=status, include_archived=include_archived)
    return {"memories": [to_ui(r) for r in recs], "stats": _orch().stats()}


@router.post("")
def add_memory(req: AddReq) -> dict:
    res = _orch().remember(
        req.content,
        memory_type=req.layer,
        key=req.key,
        tags=req.tags,
        source=req.source,
        confidence=req.confidence,
        importance=req.importance,
        pinned=req.pinned,
        provenance=req.provenance,
    )
    return {
        "operation": res["operation"],
        "rationale": res["rationale"],
        "memory": to_ui(res["record"]),
    }


@router.post("/search")
def search_memory(req: SearchReq) -> dict:
    recs, tokens = _orch().retrieve(req.query, limit=req.limit, token_budget=req.token_budget)
    return {"memories": [to_ui(r) for r in recs], "tokens": tokens}


@router.get("/context")
def context(query: str, budget: int = 600) -> dict:
    ctx = _orch().build_context(query, token_budget=budget)
    return {"context": ctx["context"], "tokens": ctx["tokens"], "count": len(ctx["records"])}


@router.get("/stats")
def stats() -> dict:
    return _orch().stats()


@router.put("/{mem_id}")
def update_memory(mem_id: str, req: UpdateReq) -> dict:
    r = _orch().update(
        mem_id, content=req.content, tags=req.tags, importance=req.importance, pinned=req.pinned
    )
    if not r:
        raise HTTPException(404, "Memory not found.")
    return to_ui(r)


@router.post("/{mem_id}/reinforce")
def reinforce(mem_id: str) -> dict:
    r = _orch().reinforce(mem_id)
    if not r:
        raise HTTPException(404, "Memory not found.")
    return to_ui(r)


@router.post("/{mem_id}/forget")
def forget(mem_id: str) -> dict:
    return {"forgotten": _orch().forget(mem_id)}


@router.post("/{mem_id}/restore")
def restore(mem_id: str) -> dict:
    r = _orch().restore(mem_id)
    if not r:
        raise HTTPException(404, "Memory not found.")
    return to_ui(r)


@router.delete("/{mem_id}")
def delete_memory(mem_id: str, hard: bool = False) -> dict:
    return {"deleted": _orch().forget(mem_id, hard=hard)}
