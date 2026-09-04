"""Resume upload + parsed-profile endpoints.

The resume is uploaded as base64 JSON (no multipart dependency), parsed into a
structured profile via the LLM, and the profile (not the raw file) is stored
server-side. Used by the Job Search Agent to personalize ranking.
"""

from __future__ import annotations

import base64

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.resume import store
from app.resume.extract import UnsupportedResume, extract_resume_text
from app.resume.match import suggested_roles
from app.resume.parser import ResumeParseError, parse_profile, profile_is_sparse

router = APIRouter(prefix="/resume", tags=["resume"])

_MAX_BYTES = 6_000_000


class ResumeUpload(BaseModel):
    filename: str
    content_b64: str


class ProfileOut(BaseModel):
    exists: bool
    filename: str | None = None
    uploaded_at: float | None = None
    profile: dict | None = None
    sparse: bool = False
    suggested_roles: list[str] = []


def _out(rec: dict) -> ProfileOut:
    prof = rec["profile"]
    return ProfileOut(
        exists=True,
        filename=rec["filename"],
        uploaded_at=rec["uploaded_at"],
        profile=prof,
        sparse=profile_is_sparse(prof),
        suggested_roles=suggested_roles(prof),
    )


@router.post("", response_model=ProfileOut)
async def upload_resume(req: ResumeUpload) -> ProfileOut:
    try:
        data = base64.b64decode(req.content_b64, validate=True)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, "Invalid file encoding.") from exc
    if len(data) > _MAX_BYTES:
        raise HTTPException(413, "Resume file is too large (max ~6 MB).")
    try:
        text = extract_resume_text(req.filename, data)
    except UnsupportedResume as exc:
        raise HTTPException(415, str(exc)) from exc
    if not text.strip():
        raise HTTPException(422, "No readable text found in this resume.")
    try:
        profile = await parse_profile(text)
    except ResumeParseError as exc:
        raise HTTPException(502, str(exc)) from exc
    rec = store.save_profile(profile, req.filename)
    return _out(rec)


@router.get("", response_model=ProfileOut)
def get_resume() -> ProfileOut:
    rec = store.load_profile()
    return _out(rec) if rec else ProfileOut(exists=False)


@router.delete("")
def remove_resume() -> dict:
    return {"removed": store.delete_profile()}
