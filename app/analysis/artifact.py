"""The Analysis Artifact: a structured, evidence-first representation of an analysis.

Design goals (why this exists):
  * The LLM must NOT be the source of analytical content. It consumes this
    artifact and only synthesises readable prose over it.
  * Every claim links to sources; every metric records how it was derived;
    every finding separates observation / interpretation / implication so the
    system never presents inference as fact.
  * Scoring is transparent and labelled heuristic — no fake scientific precision.

Reuses `app.exec.evidence` for source typing/credibility so we don't duplicate
that logic. Pure and dependency-free: safe to build deterministically and test.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from urllib.parse import unquote

from app.analysis.reliability import derive_published, score_source
from app.exec.evidence import (
    assess_credibility,
    assess_freshness,
    source_type_from_url,
)


def _academic_label(url: str) -> str:
    """A clean identifier for an academic source lacking a title: arXiv:<id> / doi:<id>."""
    low = url.lower()
    m = re.search(r"arxiv\.org/(?:abs|pdf)/([0-9]+\.[0-9]+)", low)
    if m:
        return f"arXiv:{m.group(1)}"
    m = re.search(r"doi\.org/(10\.[^\s?#]+)", url, re.I)
    if m:
        return f"doi:{m.group(1)}"
    return ""


def normalize_url(url: str) -> str:
    """Canonical form for matching: lowercase host, drop arXiv version + trailing slash."""
    u = (url or "").strip()
    u = re.sub(r"(arxiv\.org/(?:abs|pdf)/[0-9]+\.[0-9]+)v[0-9]+", r"\1", u, flags=re.I)
    return u.rstrip("/")


def _title_from_url(url: str) -> str:
    """A human-readable title from a URL slug, or '' when the slug is not word-like.

    Word slugs (Wikipedia articles, doc pages) become a title so the relevance gate
    can judge them; numeric/id slugs (arXiv ids, hashes) return '' so a real paper
    without metadata is not falsely dropped as off-topic.
    """
    path = url.split("//")[-1].split("?")[0].split("#")[0].rstrip("/")
    slug = path.split("/")[-1] if "/" in path else ""
    slug = unquote(slug).replace("_", " ").replace("-", " ").strip()
    if re.search(r"[A-Za-z]{3,}", slug) and not re.fullmatch(r"[\d.\s]+", slug):
        return slug[:120]
    return ""


class StatementType(str, Enum):  # noqa: UP042
    """The epistemic status of a statement — never present inference as fact."""

    FACT = "Fact"
    OBSERVATION = "Observation"
    INTERPRETATION = "Interpretation"
    INFERENCE = "Inference"
    RECOMMENDATION = "Recommendation"


class Verification(str, Enum):  # noqa: UP042
    VERIFIED = "Verified"  # >= 2 independent, agreeing sources
    PARTIALLY_VERIFIED = "Partially verified"  # 1 credible source
    CONFLICTING = "Conflicting"  # sources disagree
    UNVERIFIED = "Unverified"  # no source


@dataclass
class ArtifactSource:
    """A source with transparent, heuristic reliability (never fake precision)."""

    id: str
    url: str
    title: str = ""
    publisher: str = ""
    published: str | None = None
    retrieved: str | None = None
    source_type: str = "other"
    reliability: float = 0.4
    reliability_basis: str = "heuristic: source-type prior"
    corroboration: float = 1.0  # cross-source agreement factor (refined in Phase 5)
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    venue: str = ""
    snippet: str = ""  # retrieved content, used to gate topical relevance
    relevance: float | None = None  # [0,1] vs the research question; None = unassessed
    relevance_basis: str = ""  # transparent explanation of the relevance score

    def enrich(self, meta: dict) -> None:
        """Attach real bibliographic metadata gathered during research."""
        self.title = str(meta.get("title") or self.title)
        self.authors = list(meta.get("authors") or self.authors)
        self.year = meta.get("year") or self.year
        self.venue = str(meta.get("venue") or self.venue)
        self.snippet = str(meta.get("snippet") or self.snippet)

    def citation(self) -> str:
        """A proper reference string when metadata exists, else a clean id / domain."""
        title = self.title or self.publisher
        # id-only academic sources with no captured title: show arXiv:<id> / doi:<id>
        if not self.title or self.title == self.publisher:
            title = _academic_label(self.url) or title
        if not self.authors:
            return f"{title}{f' ({self.year})' if self.year else ''}."
        lead = self.authors[0] + (" et al." if len(self.authors) > 1 else "")
        yr = f" ({self.year})" if self.year else ""
        ven = f" {self.venue}." if self.venue else ""
        return f"{lead}{yr}. {title}.{ven}"

    @classmethod
    def from_url(
        cls, sid: str, url: str, title: str = "", published: str | None = None
    ) -> ArtifactSource:
        st = source_type_from_url(url)
        dom = (url.split("//")[-1].split("/")[0]) if "//" in url else url
        published = published or derive_published(url)
        fresh = assess_freshness(published)
        reliability, basis = score_source(st.value, fresh, url)
        # A word-like title derived from the URL slug makes an otherwise "unassessable"
        # bare URL judgeable by the relevance gate (so off-topic pages like
        # /wiki/The_Taming_of_the_Shrew can be dropped, not silently cited).
        return cls(
            id=sid,
            url=url,
            title=title or _title_from_url(url) or dom,
            publisher=dom.removeprefix("www."),
            published=published,
            retrieved=datetime.now(UTC).strftime("%Y-%m-%d"),
            source_type=st.value,
            reliability=reliability,
            reliability_basis=basis,
        )

    def rescore(self, corroboration: float) -> None:
        """Recompute reliability once cross-source corroboration is known (Phase 5)."""
        self.corroboration = corroboration
        self.reliability, self.reliability_basis = score_source(
            self.source_type, self.freshness(), self.url, corroboration
        )

    @property
    def credibility(self) -> str:
        return assess_credibility(source_type_from_url(self.url)).value

    def freshness(self, now: datetime | None = None) -> str:
        return assess_freshness(self.published, now)


@dataclass
class ArtifactClaim:
    """An atomic claim tied to its sources, with epistemic status + verification."""

    id: str
    statement: str
    statement_type: StatementType = StatementType.FACT
    entity: str = ""
    category: str = ""
    source_ids: list[str] = field(default_factory=list)
    evidence: str = ""
    verification: Verification = Verification.UNVERIFIED
    confidence: str = "Low"  # evidence confidence label (not a probability)


@dataclass
class Metric:
    """A number that is either reported (with a source) or computed (with a formula)."""

    name: str
    value: float
    unit: str = ""
    entity: str = ""
    source_ids: list[str] = field(default_factory=list)
    derivation: str = "reported"  # e.g. "reported" or "computed: (cur-prev)/prev*100"


@dataclass
class Comparison:
    """A structured comparison across entities on one dimension."""

    dimension: str
    # entity -> {"assessment": str, "evidence_ids": [..], "confidence": str}
    entities: dict[str, dict] = field(default_factory=dict)


@dataclass
class ArtifactFinding:
    """Evidence -> Observation -> Interpretation -> Implication (kept separate)."""

    id: str
    observation: str
    interpretation: str = ""
    implication: str = ""
    evidence_ids: list[str] = field(default_factory=list)
    confidence: str = "Medium"  # evidence confidence label


_CONF_RANK = {"High": 1.0, "Medium": 0.6, "Low": 0.3, "Analytical": 0.3}


@dataclass
class AnalysisArtifact:
    """The structured backbone the report's LLM step writes over."""

    objective: str
    mission_type: str = "RESEARCH_REPORT"
    entities: list[str] = field(default_factory=list)
    dimensions: list[str] = field(default_factory=list)
    sources: list[ArtifactSource] = field(default_factory=list)
    claims: list[ArtifactClaim] = field(default_factory=list)
    metrics: list[Metric] = field(default_factory=list)
    comparisons: list[Comparison] = field(default_factory=list)
    findings: list[ArtifactFinding] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)
    dropped_sources: int = 0  # sources excluded by the relevance gate (off-topic)

    # --- construction helpers ---

    def add_source(self, url: str, title: str = "", published: str | None = None) -> str:
        for s in self.sources:
            if s.url == url:
                return s.id
        sid = f"S{len(self.sources) + 1}"
        self.sources.append(ArtifactSource.from_url(sid, url, title, published))
        return sid

    def source_by_id(self, sid: str) -> ArtifactSource | None:
        return next((s for s in self.sources if s.id == sid), None)

    # --- transparent analytical quality score (internal / observability only) ---

    def quality(self) -> dict:
        """Evaluation metrics for the analysis — heuristic, not calibrated stats."""
        n_claims = len(self.claims) or 1
        supported = [c for c in self.claims if c.source_ids]
        verified = [c for c in self.claims if c.verification == Verification.VERIFIED]
        corrob = [c for c in self.claims if len(c.source_ids) >= 2]
        n_find = len(self.findings) or 1
        reasoned = [f for f in self.findings if f.interpretation and f.implication]
        rel = [self.reliability_of(c) for c in supported]
        return {
            "evidence_coverage": round(len(supported) / n_claims, 2),
            "source_diversity": round(len({s.source_type for s in self.sources}) / 7, 2),
            "source_quality": round(sum(rel) / len(rel), 2) if rel else 0.0,
            "claim_verification": round(len(verified) / n_claims, 2),
            "cross_source_corroboration": round(len(corrob) / n_claims, 2),
            "quantitative_support": round(min(len(self.metrics), 6) / 6, 2),
            "reasoning_depth": round(len(reasoned) / n_find, 2),
            "citation_completeness": round(len(supported) / n_claims, 2),
            "note": "Heuristic evaluation metrics for observability; not calibrated "
            "probabilities and not shown in the user-facing report.",
        }

    def reliability_of(self, claim: ArtifactClaim) -> float:
        rels = [
            s.reliability for sid in claim.source_ids if (s := self.source_by_id(sid)) is not None
        ]
        return max(rels) if rels else 0.0

    # --- what the LLM writing layer is allowed to see ---

    def to_llm_context(self) -> dict:
        """A compact, source-grounded view for the synthesis step (no free invention)."""
        return {
            "objective": self.objective,
            "mission_type": self.mission_type,
            "entities": self.entities,
            "dimensions": self.dimensions,
            "sources": [
                {
                    "id": s.id,
                    "title": s.title,
                    "url": s.url,
                    "type": s.source_type,
                    "reliability": s.reliability,
                }
                for s in self.sources
            ],
            "claims": [
                {
                    "id": c.id,
                    "statement": c.statement,
                    "type": c.statement_type.value,
                    "entity": c.entity,
                    "sources": c.source_ids,
                    "verification": c.verification.value,
                    "confidence": c.confidence,
                }
                for c in self.claims
            ],
            "metrics": [
                {
                    "name": m.name,
                    "value": m.value,
                    "unit": m.unit,
                    "entity": m.entity,
                    "sources": m.source_ids,
                    "derivation": m.derivation,
                }
                for m in self.metrics
            ],
            "findings": [
                {
                    "id": f.id,
                    "observation": f.observation,
                    "interpretation": f.interpretation,
                    "implication": f.implication,
                    "evidence": f.evidence_ids,
                    "confidence": f.confidence,
                }
                for f in self.findings
            ],
            "limitations": self.limitations,
            "uncertainties": self.uncertainties,
        }


def confidence_from_evidence(source_reliabilities: list[float], n_sources: int) -> str:
    """Evidence confidence label from source count + quality (not a probability)."""
    if not source_reliabilities:
        return "Low"
    best = max(source_reliabilities)
    if n_sources >= 2 and best >= 0.8:
        return "High"
    if n_sources >= 2 or best >= 0.8:
        return "Medium"
    return "Low"
