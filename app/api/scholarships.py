"""Scholarship Finder API — search + saved-scholarship persistence.

Follows the Job Search Agent conventions: query OR structured filters (filters are
authoritative and reset intent), optional resume personalization, deterministic
hard filtering, honest source health.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.scholarships import store
from app.scholarships.models import FilterSpec, ScholarshipSearchResponse
from app.scholarships.parser import (
    COUNTRIES,
    FIELD_DISPLAY,
    intent_from_filters,
    parse_query,
)
from app.scholarships.search import run_search, summarize

router = APIRouter(prefix="/scholarships", tags=["scholarships"])


class SearchReq(BaseModel):
    query: str = ""
    filters: FilterSpec | None = None
    use_resume: bool = False
    limit: int = 100


class SaveReq(BaseModel):
    scholarship: dict
    status: str = "Interested"


class StatusReq(BaseModel):
    status: str


@router.post("/search", response_model=ScholarshipSearchResponse)
async def search(req: SearchReq) -> ScholarshipSearchResponse:
    intent = intent_from_filters(req.filters) if req.filters is not None else parse_query(req.query)
    profile = None
    if req.use_resume:
        from app.resume import store as rstore

        rec = rstore.load_profile()
        profile = rec["profile"] if rec else None
    schs, statuses, fetched = await run_search(intent, profile, req.limit)
    return ScholarshipSearchResponse(
        scholarships=schs,
        sources=statuses,
        intent=intent,
        total_fetched=fetched,
        total_after_filter=len(schs),
        summary=summarize(schs),
    )


@router.get("/filters")
def filters() -> dict:
    return {
        "countries": ["All Countries", *COUNTRIES.keys(), "Other"],
        "degrees": ["bachelor", "master", "phd", "postdoc", "diploma"],
        "fields": list(FIELD_DISPLAY.values()),
        "funding": ["fully_funded", "partial", "tuition", "stipend"],
        "scholarship_types": ["government", "university", "research", "fellowship", "exchange"],
        "intakes": ["2026", "2027", "2028"],
    }


@router.get("/saved")
def saved() -> dict:
    return {"saved": store.list_saved()}


@router.post("/saved")
def save_one(req: SaveReq) -> dict:
    url = str(req.scholarship.get("application_url", ""))
    if url and not url.startswith(("http://", "https://")):
        raise HTTPException(400, "Refusing to save a scholarship with an unsafe application URL.")
    store.save(req.scholarship, req.status)
    return {"saved": True}


@router.post("/saved/{sid}/status")
def update_status(sid: str, req: StatusReq) -> dict:
    return {"updated": store.set_status(sid, req.status)}


@router.delete("/saved/{sid}")
def remove_saved(sid: str) -> dict:
    return {"removed": store.remove(sid)}
