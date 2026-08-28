"""Structured analytical report model — an analyst deliverable, not a transcript.

Rich enough for a real report: an executive snapshot, key findings with a
confidence level and evidence, an (optional, qualitative) competitive scorecard
with an explicit methodology, evidence-coverage stats, a user-facing research
trail, analytical sections, methodology, limitations, and sources. Everything
optional beyond the basics — the builder only fills what the mission actually
supports. Rendering lives in report_pdf; nothing here fabricates data.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Metric:
    label: str
    value: str
    note: str = ""


@dataclass
class Finding:
    title: str
    body: str
    confidence: str = "Analytical"   # High | Medium | Low | Analytical
    evidence: list[str] = field(default_factory=list)


@dataclass
class Table:
    columns: list[str]
    rows: list[list[str]]
    caption: str = ""


@dataclass
class Scorecard:
    dimensions: list[str]
    entities: list[str]
    scores: dict[str, list[int]]     # entity -> per-dimension score 0..5
    methodology: str = "Qualitative analyst assessment (0-5), not a measured statistic."


@dataclass
class EvidenceCoverage:
    sources_analyzed: int
    claims_supported: int
    assessments: int

    @property
    def coverage_pct(self) -> int:
        total = self.claims_supported + self.assessments
        return round(100 * self.claims_supported / total) if total else 0


@dataclass
class ResearchTrail:
    sources_used: int
    sources_excluded: int
    areas: list[str] = field(default_factory=list)
    last_verified: str = ""


@dataclass
class ReportSection:
    heading: str
    paragraphs: list[str] = field(default_factory=list)
    table: Table | None = None


@dataclass
class Report:
    title: str
    subtitle: str = ""
    report_type: str = "RESEARCH_REPORT"
    meta: dict = field(default_factory=dict)
    snapshot: list[Metric] = field(default_factory=list)
    executive_summary: str = ""
    findings: list[Finding] = field(default_factory=list)
    scorecard: Scorecard | None = None
    coverage: EvidenceCoverage | None = None
    trail: ResearchTrail | None = None
    sections: list[ReportSection] = field(default_factory=list)
    strategic_implications: list[str] = field(default_factory=list)
    methodology: str = ""
    limitations: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    appendix: list[ReportSection] = field(default_factory=list)
