"""SOP Builder API — documents, grounded generation, fact-check, quality, versions, export."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from app.sop import export as sop_export
from app.sop import factcheck, quality, store
from app.sop.generate import SopError, generate, rewrite
from app.sop.models import (
    FactCheckResult,
    GenerateReq,
    QualityReport,
    SopDoc,
    SopRequirements,
    SopTarget,
    SopVersion,
)

router = APIRouter(prefix="/sop", tags=["sop"])


class CreateReq(BaseModel):
    title: str = "Untitled SOP"
    target: SopTarget = SopTarget()
    requirements: SopRequirements = SopRequirements()
    style: str = "academic"


class UpdateReq(BaseModel):
    title: str | None = None
    content: str | None = None
    style: str | None = None
    instructions: str | None = None
    target: SopTarget | None = None
    requirements: SopRequirements | None = None


class RewriteReq(BaseModel):
    text: str
    action: str


class VersionReq(BaseModel):
    label: str = "Draft"


class ExportReq(BaseModel):
    format: str = "pdf"


def _profile_and_resume():
    from app.scholarships import profile as pstore

    prof = pstore.load()
    profile = prof.model_dump() if prof else None
    resume = None
    from app.resume import store as rstore

    rec = rstore.load_profile()
    if rec:
        resume = rec["profile"]
    return profile, resume


def _require(doc_id: str) -> SopDoc:
    doc = store.get(doc_id)
    if not doc:
        raise HTTPException(404, "SOP document not found.")
    return doc


@router.post("", response_model=SopDoc)
def create(req: CreateReq) -> SopDoc:
    return store.create(
        SopDoc(
            id="",
            title=req.title,
            target=req.target,
            requirements=req.requirements,
            style=req.style,
        )
    )


@router.get("/list")
def list_docs() -> dict:
    return {"documents": store.list_docs()}


@router.get("/{doc_id}", response_model=SopDoc)
def get_doc(doc_id: str) -> SopDoc:
    return _require(doc_id)


@router.put("/{doc_id}", response_model=SopDoc)
def update_doc(doc_id: str, req: UpdateReq) -> SopDoc:
    doc = _require(doc_id)
    for field in ("title", "content", "style", "instructions", "target", "requirements"):
        val = getattr(req, field)
        if val is not None:
            setattr(doc, field, val)
    return store.update(doc)


@router.delete("/{doc_id}")
def delete_doc(doc_id: str) -> dict:
    return {"deleted": store.delete(doc_id)}


@router.post("/{doc_id}/generate", response_model=SopDoc)
async def generate_doc(doc_id: str, req: GenerateReq) -> SopDoc:
    doc = _require(doc_id)
    if req.style:
        doc.style = req.style
    if req.instructions is not None:
        doc.instructions = req.instructions
    profile, resume = _profile_and_resume()
    try:
        content = await generate(doc, profile, resume)
    except SopError as exc:
        raise HTTPException(502, str(exc)) from exc
    doc.content = content
    return store.update(doc)


@router.post("/{doc_id}/rewrite")
async def rewrite_selection(doc_id: str, req: RewriteReq) -> dict:
    _require(doc_id)
    try:
        return {"text": await rewrite(req.text, req.action)}
    except SopError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.post("/{doc_id}/check", response_model=FactCheckResult)
def check_facts(doc_id: str) -> FactCheckResult:
    doc = _require(doc_id)
    profile, resume = _profile_and_resume()
    return factcheck.check(doc.content, profile, resume)


@router.get("/{doc_id}/quality", response_model=QualityReport)
def quality_report(doc_id: str) -> QualityReport:
    doc = _require(doc_id)
    return quality.analyze(doc.content, doc.requirements)


@router.get("/{doc_id}/versions")
def versions(doc_id: str) -> dict:
    return {"versions": [v.model_dump() for v in store.list_versions(doc_id)]}


@router.post("/{doc_id}/versions", response_model=SopVersion)
def snapshot(doc_id: str, req: VersionReq) -> SopVersion:
    doc = _require(doc_id)
    return store.add_version(doc_id, req.label, doc.content)


@router.post("/{doc_id}/versions/{vid}/restore", response_model=SopDoc)
def restore(doc_id: str, vid: str) -> SopDoc:
    doc = _require(doc_id)
    v = store.get_version(vid)
    if not v or v.doc_id != doc_id:
        raise HTTPException(404, "Version not found.")
    doc.content = v.content
    return store.update(doc)


@router.post("/{doc_id}/export")
def export_doc(doc_id: str, req: ExportReq) -> Response:
    doc = _require(doc_id)
    data, media, filename = sop_export.export(doc, req.format)
    return Response(
        content=data,
        media_type=media,
        headers={"content-disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/from-phd/{phd_id}", response_model=SopDoc)
def from_phd(phd_id: str) -> SopDoc:
    """Create a new SOP pre-filled from a selected PhD opportunity (target import)."""
    from app.phd.catalog import catalog

    opp = next((o for o in catalog() if o.id == phd_id), None)
    if opp is None:
        raise HTTPException(404, "PhD opportunity not found.")
    target = SopTarget(
        university=opp.institution,
        program=opp.title,
        degree="PhD",
        country=opp.country,
        field=(opp.fields[0] if opp.fields and opp.fields[0] != "all" else None),
        opportunity_id=opp.id,
        opportunity_url=opp.official_application_url,
        opportunity_description=opp.description,
    )
    return store.create(SopDoc(id="", title=f"SOP — {opp.institution}", target=target))
