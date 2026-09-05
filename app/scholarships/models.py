"""Normalized scholarship + search-intent models."""

from __future__ import annotations

from pydantic import BaseModel, Field

# Controlled vocabularies (kept small + explicit so filtering stays deterministic).
DEGREE_LEVELS = ["bachelor", "master", "phd", "postdoc", "diploma"]
FUNDING_TYPES = ["fully_funded", "partial", "tuition", "stipend"]
NATIONALITY_TAGS = ["international", "commonwealth", "developing", "eu", "specific"]
# eligible | likely | unclear | insufficient | not_eligible
ELIGIBILITY_STATUSES = ["eligible", "likely", "unclear", "insufficient", "not_eligible"]
OPPORTUNITY_TYPES = [
    "scholarship",
    "fellowship",
    "funded_phd_position",
    "research_position",
    "grant",
]


class EligibilityCheck(BaseModel):
    requirement: str
    required_value: str | None = None
    user_value: str | None = None
    status: str  # PASS | FAIL | UNKNOWN | NOT_APPLICABLE
    explanation: str = ""


class StudentProfile(BaseModel):
    """The USER's information — never mixed into scholarship source data."""

    nationality: str | None = None
    degree: str | None = None  # highest/current: bachelor|master|phd
    field: str | None = None  # display
    field_tags: list[str] = Field(default_factory=list)
    gpa: float | None = None
    gpa_scale: float | None = None  # e.g. 10 or 4
    graduation_year: int | None = None
    ielts: float | None = None
    toefl: float | None = None
    experience_years: float | None = None
    skills: list[str] = Field(default_factory=list)
    preferred_countries: list[str] = Field(default_factory=list)

    def is_empty(self) -> bool:
        return not any(
            [
                self.nationality,
                self.degree,
                self.field,
                self.gpa,
                self.ielts,
                self.experience_years,
                self.skills,
            ]
        )


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
    # structured, checkable requirements (null = the source doesn't state it)
    min_gpa: float | None = None
    gpa_scale: float | None = None
    min_ielts: float | None = None
    min_work_experience_years: int | None = None
    opportunity_type: str = "scholarship"  # OPPORTUNITY_TYPES
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
    eligibility_checks: list[EligibilityCheck] = Field(default_factory=list)


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
    country_facets: list[dict] = Field(default_factory=list)  # [{country, count}]
    funding_facets: list[dict] = Field(default_factory=list)
    profile_used: StudentProfile | None = None
    profile_incomplete: bool = False
