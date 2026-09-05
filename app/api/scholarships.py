"""Scholarship Finder API — search, student profile, saved scholarships.

Query OR structured filters (filters are authoritative and reset intent). Eligibility
is computed from the user's StudentProfile (saved profile > resume > explicit query
facts) against each scholarship's structured requirements — never fabricated.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.scholarships import profile as pstore
from app.scholarships import store
from app.scholarships.models import (
    FilterSpec,
    ScholarshipSearchResponse,
    StudentProfile,
)
from app.scholarships.parser import (
    COUNTRIES,
    FIELD_DISPLAY,
    field_tags_for,
    intent_from_filters,
    parse_query,
)
from app.scholarships.search import facets, run_search, summarize

router = APIRouter(prefix="/scholarships", tags=["scholarships"])


class SearchReq(BaseModel):
    query: str = ""
    filters: FilterSpec | None = None
    use_resume: bool = True
    use_profile: bool = True
    limit: int = 100


class SaveReq(BaseModel):
    scholarship: dict
    status: str = "Interested"


class StatusReq(BaseModel):
    status: str


@router.post("/search", response_model=ScholarshipSearchResponse)
async def search(req: SearchReq) -> ScholarshipSearchResponse:
    intent = intent_from_filters(req.filters) if req.filters is not None else parse_query(req.query)
    stored = pstore.load() if req.use_profile else None
    resume = None
    if req.use_resume:
        from app.resume import store as rstore

        rec = rstore.load_profile()
        resume = rec["profile"] if rec else None
    effective = pstore.merge_effective(intent, stored, resume)
    schs, statuses, fetched = await run_search(intent, effective, resume, req.limit)
    cfac, ffac = facets(schs)
    return ScholarshipSearchResponse(
        scholarships=schs,
        sources=statuses,
        intent=intent,
        total_fetched=fetched,
        total_after_filter=len(schs),
        summary=summarize(schs),
        country_facets=cfac,
        funding_facets=ffac,
        profile_used=effective,
        profile_incomplete=(stored is None or stored.is_empty()) and resume is None,
    )


# --- student profile --------------------------------------------------------
@router.get("/profile", response_model=StudentProfile)
def get_profile() -> StudentProfile:
    return pstore.load() or StudentProfile()


@router.post("/profile", response_model=StudentProfile)
def set_profile(p: StudentProfile) -> StudentProfile:
    if p.field and not p.field_tags:
        p.field_tags = field_tags_for(p.field)
    pstore.save(p)
    return p


@router.delete("/profile")
def clear_profile() -> dict:
    return {"cleared": pstore.clear()}


@router.post("/profile/prefill", response_model=StudentProfile)
def prefill_profile() -> StudentProfile:
    """Build a StudentProfile from the uploaded résumé (not saved until confirmed)."""
    from app.resume import store as rstore

    rec = rstore.load_profile()
    if not rec:
        raise HTTPException(404, "No résumé uploaded — upload one in the Job Search Agent first.")
    return pstore.from_resume(rec["profile"])


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


# --- saved scholarships -----------------------------------------------------
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
