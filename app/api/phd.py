"""PhD Finder API — search, detail, saved. Reuses the shared StudentProfile."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.phd import store
from app.phd.catalog import catalog
from app.phd.models import PhdFilterSpec, PhdOpportunity, PhdSearchResponse
from app.phd.parser import intent_from_filters, parse_query
from app.phd.search import build_checklist, facets, run_search, summarize
from app.scholarships.eligibility import evaluate
from app.scholarships.parser import COUNTRIES, FIELD_DISPLAY

router = APIRouter(prefix="/phd", tags=["phd"])


class SearchReq(BaseModel):
    query: str = ""
    filters: PhdFilterSpec | None = None
    use_resume: bool = True
    use_profile: bool = True
    limit: int = 100


class SaveReq(BaseModel):
    opportunity: dict
    status: str = "Interested"
    notes: str = ""


class StatusReq(BaseModel):
    status: str


def _profile_and_resume(use_profile: bool, use_resume: bool):
    from app.scholarships import profile as pstore

    stored = pstore.load() if use_profile else None
    resume = None
    if use_resume:
        from app.resume import store as rstore

        rec = rstore.load_profile()
        resume = rec["profile"] if rec else None
    return stored, resume, pstore


@router.post("/search", response_model=PhdSearchResponse)
async def search(req: SearchReq) -> PhdSearchResponse:
    intent = intent_from_filters(req.filters) if req.filters is not None else parse_query(req.query)
    stored, resume, pstore = _profile_and_resume(req.use_profile, req.use_resume)
    from app.scholarships.models import ScholarshipIntent

    sch_intent = ScholarshipIntent(
        nationality=intent.nationality, field=intent.field, field_tags=intent.field_tags
    )
    effective = pstore.merge_effective(sch_intent, stored, resume)
    opps, statuses, fetched = await run_search(intent, effective, resume, req.limit)
    return PhdSearchResponse(
        opportunities=opps,
        sources=statuses,
        intent=intent,
        total_fetched=fetched,
        total_after_filter=len(opps),
        summary=summarize(opps),
        country_facets=facets(opps),
        profile_incomplete=(stored is None or stored.is_empty()) and resume is None,
    )


@router.get("/{pid}", response_model=PhdOpportunity)
def detail(pid: str) -> PhdOpportunity:
    opp = next((o for o in catalog() if o.id == pid), None)
    if opp is None:
        raise HTTPException(404, "PhD opportunity not found.")
    from app.scholarships import profile as pstore

    prof = pstore.load()
    if prof:
        opp.eligibility_status, opp.eligibility_checks = evaluate(opp, prof)
    opp.application_checklist = build_checklist(opp)
    return opp


@router.get("/meta/filters")
def filters() -> dict:
    return {
        "countries": ["All Countries", *COUNTRIES.keys(), "Other"],
        "fields": list(FIELD_DISPLAY.values()),
        "funding": ["fully_funded", "funded", "salaried", "scholarship", "partial", "self_funded"],
        "opportunity_types": [
            "phd_program",
            "funded_phd_position",
            "research_position",
            "fellowship",
            "doctoral_scholarship",
        ],
        "intakes": ["2026", "2027", "2028"],
    }


@router.get("/saved/list")
def saved() -> dict:
    return {"saved": store.list_saved()}


@router.post("/saved")
def save_one(req: SaveReq) -> dict:
    url = str(req.opportunity.get("official_application_url", ""))
    if url and not url.startswith(("http://", "https://")):
        raise HTTPException(400, "Refusing to save an opportunity with an unsafe URL.")
    store.save(req.opportunity, req.status, req.notes)
    return {"saved": True}


@router.post("/saved/{pid}/status")
def update_status(pid: str, req: StatusReq) -> dict:
    return {"updated": store.set_status(pid, req.status)}


@router.delete("/saved/{pid}")
def remove_saved(pid: str) -> dict:
    return {"removed": store.remove(pid)}
