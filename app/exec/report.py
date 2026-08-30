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
    source_refs: list[int] = field(default_factory=list)  # 1-based refs into source_records
    unverified_figures: bool = False  # carries quantitative claims with no source backing


@dataclass
class SourceRecord:
    ref: int                         # 1-based citation number
    url: str
    publisher: str = ""
    stype: str = ""                  # Academic | News | Government | ...
    credibility: str = ""            # High | Medium | Low (internal assessment)
    freshness: str = ""              # Recent | Current | Background | Unknown
    citation: str = ""               # formatted reference (authors, year, title, venue)
    relevance: float | None = None   # [0,1] topical relevance to the research question


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
    bottom_line: str = ""                           # the headline analyst conclusion
    problem_definition: str = ""                    # what the topic is / why it matters
    evaluation_framework: list[dict] = field(default_factory=list)  # criterion/definition
    findings: list[Finding] = field(default_factory=list)
    approaches: list[dict] = field(default_factory=list)   # per-option deep dive
    comparative_analysis: str = ""                  # narrative across dimensions
    # claim / evidence / reasoning / trade_off / decision / counter
    reasoning_chains: list[dict] = field(default_factory=list)
    key_insights: list[dict] = field(default_factory=list)       # {insight, confidence}
    evidence_summary: list[dict] = field(default_factory=list)   # {finding, strength, confidence}
    trade_offs: list[dict] = field(default_factory=list)         # {entity, pros[], cons[]}
    scoring_rationale: list[dict] = field(default_factory=list)  # {criterion, reason, confidence}
    # per option x criterion evidence behind each 0-5 score:
    # {entity, criterion, score, supporting, contradicting, confidence, refs, rationale}
    evidence_scores: list[dict] = field(default_factory=list)
    # claim-level traceability: {claim, refs[], verification, confidence}
    evidence_matrix: list[dict] = field(default_factory=list)
    decision_change: list[str] = field(default_factory=list)     # what would change the decision
    # failure/mechanism/probability/impact/detection/mitigation/residual_risk
    failure_analysis: list[dict] = field(default_factory=list)
    scorecard: Scorecard | None = None
    coverage: EvidenceCoverage | None = None
    trail: ResearchTrail | None = None
    sections: list[ReportSection] = field(default_factory=list)
    recommendation: str = ""                       # decisive analyst recommendation
    # evidence-grounded final decision: {recommended[], components[], selective[],
    # confidence, evidence_count, summary, consistency_flags[]}
    decision: dict = field(default_factory=dict)
    decision_rationale: list[dict] = field(default_factory=list)  # requirement/decision/reason
    strategic_implications: list[str] = field(default_factory=list)
    evidence_graph: str = ""                        # ASCII research-evidence-graph diagram
    methodology: str = ""
    limitations: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    source_records: list[SourceRecord] = field(default_factory=list)
    freshness: dict = field(default_factory=dict)
    integrity: dict = field(default_factory=dict)  # honest research-integrity metrics
    critic_flags: list[str] = field(default_factory=list)  # e.g. topic-drift events
    appendix: list[ReportSection] = field(default_factory=list)
