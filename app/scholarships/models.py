"""Normalized scholarship + search-intent models."""

from __future__ import annotations

from pydantic import BaseModel, Field

# Controlled vocabularies (kept small + explicit so filtering stays deterministic).
DEGREE_LEVELS = ["bachelor", "master", "phd", "postdoc", "diploma"]
FUNDING_TYPES = ["fully_funded", "partial", "tuition", "stipend"]
NATIONALITY_TAGS = ["international", "commonwealth", "developing", "eu", "specific"]
ELIGIBILITY_STATUSES = ["eligible", "likely", "unclear", "not_eligible"]


class Scholarship(BaseModel):
    id: str
    title: str
    provider: str
    institution: str | None = None
    country: str
    countries: list[str] = Field(default_factory=list)
    degree_levels: list[str] = Field(default_factory=list)
    fields: list[str] = Field(default_factory=list)  # ["all"] = open to any field
    scholarship_type: str | None = (
        None  # government|university|external|research|fellowship|exchange
    )
    funding_type: str = "partial"  # fully_funded|partial|tuition|stipend
    tuition_coverage: bool | None = None
    stipend: str | None = None
    travel_coverage: bool | None = None
    accommodation_coverage: bool | None = None
    insurance_coverage: bool | None = None
    nationality_eligibility: str = "international"  # NATIONALITY_TAGS
    nationality_note: str | None = None
    academic_requirements: str | None = None
    language_requirements: str | None = None
    work_experience_requirement: str | None = None
    deadline: str | None = None  # ISO date when reliably known, else None
    deadline_note: str | None = None  # e.g. "Annual — typically Nov; verify on official page"
    intake: list[str] = Field(default_factory=lambda: ["annual"])
    duration: str | None = None
    description: str = ""
    source: str = "Curated"
    source_url: str | None = None
    scholarship_detail_url: str | None = None
    application_url: str = ""
    official_provider_url: str | None = None
    apply_direct: bool = True
    last_verified_at: str | None = None
    is_verified: bool = False
    sources: list[str] = Field(default_factory=list)
    # computed at search time:
    match_score: float | None = None
    match_breakdown: dict[str, float] = Field(default_factory=dict)
    match_reason: str | None = None
    eligibility_status: str | None = None
    eligibility_reasons: list[str] = Field(default_factory=list)


class ScholarshipIntent(BaseModel):
    raw: str = ""
    field: str | None = None  # display, e.g. "Artificial Intelligence"
    field_tags: list[str] = Field(default_factory=list)  # normalized match tags
    countries: list[str] = Field(default_factory=list)
    degree: str | None = None  # one of DEGREE_LEVELS
    funding: str | None = None  # one of FUNDING_TYPES
    nationality: str | None = None  # e.g. "India"
    intake: str | None = None  # e.g. "2027"
    scholarship_type: str | None = None
    no_ielts: bool = False


class FilterSpec(BaseModel):
    """Structured, individually-removable filters — authoritative when present."""

    field: str | None = None
    countries: list[str] = Field(default_factory=list)
    degree: str | None = None
    funding: str | None = None
    nationality: str | None = None
    intake: str | None = None
    scholarship_type: str | None = None
    no_ielts: bool = False


class SourceStatus(BaseModel):
    source: str
    status: str  # ok | error
    count: int = 0
    note: str | None = None


class ScholarshipSearchResponse(BaseModel):
    scholarships: list[Scholarship]
    sources: list[SourceStatus]
    intent: ScholarshipIntent
    total_fetched: int
    total_after_filter: int
    summary: dict[str, int] = Field(default_factory=dict)
