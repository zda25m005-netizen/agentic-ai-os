"""SOP document models."""

from __future__ import annotations

from pydantic import BaseModel, Field

STYLES = ["academic", "research", "professional", "concise", "personal"]


class SopTarget(BaseModel):
    university: str | None = None
    program: str | None = None
    degree: str | None = None
    country: str | None = None
    field: str | None = None
    opportunity_id: str | None = None
    opportunity_url: str | None = None
    opportunity_description: str | None = None


class SopRequirements(BaseModel):
    word_limit: int | None = None
    char_limit: int | None = None
    prompt: str | None = None
    questions: list[str] = Field(default_factory=list)


class SopDoc(BaseModel):
    id: str
    title: str = "Untitled SOP"
    target: SopTarget = Field(default_factory=SopTarget)
    requirements: SopRequirements = Field(default_factory=SopRequirements)
    style: str = "academic"
    instructions: str = ""
    content: str = ""
    created_at: float | None = None
    updated_at: float | None = None


class SopVersion(BaseModel):
    id: str
    doc_id: str
    label: str
    content: str
    created_at: float


class GenerateReq(BaseModel):
    instructions: str | None = None  # extra one-off instructions for this generation
    style: str | None = None


class FactClaim(BaseModel):
    text: str
    status: str  # verified | needs_verification | unsupported
    note: str = ""


class FactCheckResult(BaseModel):
    claims: list[FactClaim]
    verified: int
    needs_verification: int
    unsupported: int


class QualityReport(BaseModel):
    word_count: int
    char_count: int
    word_limit: int | None = None
    over_limit: bool = False
    coverage: list[dict] = Field(default_factory=list)  # [{section, covered}]
    specificity: float = 0.0
    generic_flags: list[str] = Field(default_factory=list)
    repetition_flags: list[str] = Field(default_factory=list)
