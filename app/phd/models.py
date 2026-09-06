"""PhD opportunity + search-intent models.

PhdOpportunity intentionally exposes the same structured entry-requirement fields
(nationality_eligibility, degree_levels, fields, min_gpa/gpa_scale, min_ielts,
min_work_experience_years) that scholarships.eligibility.evaluate() reads, so the
eligibility engine is reused directly — no duplication.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.scholarships.models import EligibilityCheck, SourceStatus, StudentProfile  # noqa: F401

OPPORTUNITY_TYPES = [
    "phd_program",
    "funded_phd_position",
    "research_position",
    "fellowship",
    "doctoral_scholarship",
]
FUNDING_TYPES = [
    "fully_funded",
    "funded",
    "salaried",
    "scholarship",
    "partial",
    "self_funded",
    "unknown",
]


class PhdOpportunity(BaseModel):
    id: str
    title: str
    institution: str
    department: str | None = None
    research_group: str | None = None
    country: str
    countries: list[str] = Field(default_factory=list)
    city: str | None = None
    opportunity_type: str = "funded_phd_position"
    fields: list[str] = Field(default_factory=list)  # ["all"] = any field
    research_areas: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    supervisor: str | None = None
    supervisors: list[str] = Field(default_factory=list)
    funding_type: str = "unknown"
    funding_amount: str | None = None
    currency: str | None = None
    tuition_coverage: bool | None = None
    stipend: str | None = None
    salary: str | None = None
    # structured entry requirements (null = not stated) — read by the eligibility engine
    nationality_eligibility: str = "international"
    nationality_note: str | None = None
    degree_levels: list[str] = Field(default_factory=lambda: ["master"])  # required prior degree
    fields_required: list[str] = Field(default_factory=list)
    min_gpa: float | None = None
    gpa_scale: float | None = None
    min_ielts: float | None = None
    min_work_experience_years: int | None = None
    language_requirements: str | None = None
    academic_requirements: str | None = None
    application_deadline: str | None = None  # ISO date if reliably known
    deadline_note: str | None = None
    start_date: str | None = None
    intake: list[str] = Field(default_factory=lambda: ["rolling"])
    duration: str | None = None
    description: str = ""
    source: str = "Curated"
    source_url: str | None = None
    official_university_url: str | None = None
    official_application_url: str = ""
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
    eligibility_checks: list[EligibilityCheck] = Field(default_factory=list)
    application_checklist: list[dict] = Field(default_factory=list)


class PhdIntent(BaseModel):
    raw: str = ""
    field: str | None = None
    field_tags: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    funding: str | None = None  # fully_funded|funded|salaried|scholarship|partial
    opportunity_type: str | None = None
    nationality: str | None = None
    intake: str | None = None
    no_fee: bool = False


class PhdFilterSpec(BaseModel):
    field: str | None = None
    countries: list[str] = Field(default_factory=list)
    funding: str | None = None
    opportunity_type: str | None = None
    nationality: str | None = None
    intake: str | None = None


class PhdSearchResponse(BaseModel):
    opportunities: list[PhdOpportunity]
    sources: list[SourceStatus]
    intent: PhdIntent
    total_fetched: int
    total_after_filter: int
    summary: dict[str, int] = Field(default_factory=dict)
    country_facets: list[dict] = Field(default_factory=list)
    profile_incomplete: bool = False
