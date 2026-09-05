"""StudentProfile persistence + assembly.

The effective profile used for eligibility is built from (in priority order):
the user's saved StudentProfile, then their uploaded resume, then explicit facts
stated in the current query. Nothing is invented — unknown fields stay None.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.scholarships.models import ScholarshipIntent, StudentProfile

DB_PATH = Path("scholarship_profile.db")  # overridable in tests
_OWNER = "me"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS student_profile (owner TEXT PRIMARY KEY, data TEXT)")
    return conn


def load() -> StudentProfile | None:
    with _conn() as conn:
        row = conn.execute("SELECT data FROM student_profile WHERE owner=?", (_OWNER,)).fetchone()
    return StudentProfile(**json.loads(row[0])) if row else None


def save(profile: StudentProfile) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO student_profile (owner, data) VALUES (?, ?) "
            "ON CONFLICT(owner) DO UPDATE SET data=excluded.data",
            (_OWNER, profile.model_dump_json()),
        )


def clear() -> bool:
    with _conn() as conn:
        return conn.execute("DELETE FROM student_profile WHERE owner=?", (_OWNER,)).rowcount > 0


def from_resume(resume: dict) -> StudentProfile:
    """Map a parsed résumé profile onto a StudentProfile (only what it actually states)."""
    from app.scholarships.parser import field_tags_for

    text = " ".join(
        resume.get("industries", []) + resume.get("job_titles", []) + resume.get("skills", [])
    )
    tags = field_tags_for(text)
    field = None
    if tags:
        from app.scholarships.parser import FIELD_DISPLAY

        field = FIELD_DISPLAY.get(tags[0])
    degree = None
    edu = " ".join(resume.get("education", [])).lower()
    if "phd" in edu or "doctor" in edu:
        degree = "phd"
    elif any(k in edu for k in ("master", "m.tech", "msc", "m.sc", "mba")):
        degree = "master"
    elif any(k in edu for k in ("bachelor", "b.tech", "bsc", "b.sc")):
        degree = "bachelor"
    return StudentProfile(
        degree=degree,
        field=field,
        field_tags=tags,
        skills=resume.get("skills", []),
        experience_years=resume.get("experience_years"),
    )


def merge_effective(
    intent: ScholarshipIntent, stored: StudentProfile | None, resume: dict | None
) -> StudentProfile:
    """Assemble the effective profile: saved profile > resume > query facts (gap-fill)."""
    p = stored.model_copy(deep=True) if stored else StudentProfile()
    if resume:
        rp = from_resume(resume)
        for f in ("degree", "field", "experience_years"):
            if getattr(p, f) is None:
                setattr(p, f, getattr(rp, f))
        if not p.field_tags:
            p.field_tags = rp.field_tags
        if not p.skills:
            p.skills = rp.skills
    # explicit query facts fill remaining gaps
    if intent.nationality and not p.nationality:
        p.nationality = intent.nationality
    if intent.degree and not p.degree:
        p.degree = intent.degree
    if intent.field and not p.field:
        p.field = intent.field
    if intent.field_tags and not p.field_tags:
        p.field_tags = list(intent.field_tags)
    return p
