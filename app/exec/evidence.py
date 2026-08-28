"""Evidence layer: Source / EvidenceItem / Claim + transparent assessment.

Turns raw research output into a traceable structure so findings can cite sources
and confidence can be *earned* rather than guessed. All scoring here is an
explicit internal heuristic — credibility, freshness, and confidence are labeled
"assessment", never presented as objective measurement. Nothing is fabricated:
if there are no sources, the ledger reports zero coverage honestly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from urllib.parse import urlparse


class SourceType(str, Enum):  # noqa: UP042
    PRIMARY = "primary"
    ACADEMIC = "academic"
    GOVERNMENT = "government"
    NEWS = "news"
    INDUSTRY = "industry"
    COMPANY = "company"
    OTHER = "other"


class Credibility(str, Enum):  # noqa: UP042
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class ClaimType(str, Enum):  # noqa: UP042
    FACT = "Fact"
    ANALYSIS = "Analysis"
    INFERENCE = "Inference"


_ACADEMIC = ("arxiv.org", "doi.org", ".edu", "acm.org", "ieee.org", "nature.com",
             "springer.com", "sciencedirect.com")
_NEWS = ("reuters.com", "bloomberg.com", "techcrunch.com", "theverge.com",
         "nytimes.com", "wsj.com", "cnbc.com", "ft.com", "wired.com", "arstechnica.com")
_INDUSTRY = ("gartner.com", "idc.com", "mckinsey.com", "statista.com", "forrester.com")


def _domain(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").lower().removeprefix("www.")
    except Exception:
        return ""


def source_type_from_url(url: str) -> SourceType:
    d = _domain(url)
    if d.endswith(".gov"):
        return SourceType.GOVERNMENT
    if any(k in d for k in _ACADEMIC):
        return SourceType.ACADEMIC
    if any(k in d for k in _NEWS):
        return SourceType.NEWS
    if any(k in d for k in _INDUSTRY):
        return SourceType.INDUSTRY
    if d:
        return SourceType.COMPANY  # a named domain, treated as a primary/company source
    return SourceType.OTHER


_CRED = {
    SourceType.GOVERNMENT: Credibility.HIGH,
    SourceType.ACADEMIC: Credibility.HIGH,
    SourceType.PRIMARY: Credibility.HIGH,
    SourceType.COMPANY: Credibility.MEDIUM,
    SourceType.INDUSTRY: Credibility.MEDIUM,
    SourceType.NEWS: Credibility.MEDIUM,
    SourceType.OTHER: Credibility.LOW,
}


def assess_credibility(stype: SourceType) -> Credibility:
    """Internal source-quality heuristic (labeled, not an objective measure)."""
    return _CRED.get(stype, Credibility.LOW)


def assess_freshness(published: str | None, now: datetime | None = None) -> str:
    """Recent (<30d) / Current (<12mo) / Background (older) / Unknown."""
    if not published:
        return "Unknown"
    try:
        dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
    except ValueError:
        return "Unknown"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    days = ((now or datetime.now(UTC)) - dt).days
    if days < 30:
        return "Recent"
    if days < 365:
        return "Current"
    return "Background"


@dataclass
class Source:
    url: str
    title: str = ""
    publisher: str = ""
    published: str | None = None
    retrieved: str | None = None
    stype: SourceType = SourceType.OTHER
    credibility: Credibility = Credibility.LOW

    @classmethod
    def from_url(cls, url: str, title: str = "") -> Source:
        st = source_type_from_url(url)
        return cls(url=url, title=title or _domain(url), publisher=_domain(url),
                   retrieved=datetime.now(UTC).strftime("%Y-%m-%d"),
                   stype=st, credibility=assess_credibility(st))


@dataclass
class EvidenceItem:
    claim: str
    evidence: str
    source_idx: int          # index into the ledger's sources
    entity: str = ""
    topic: str = ""


@dataclass
class Claim:
    text: str
    claim_type: ClaimType = ClaimType.ANALYSIS
    source_idx: list[int] = field(default_factory=list)

    def confidence(self, sources: list[Source]) -> Credibility:
        """Earned confidence: source count + quality (not a random value)."""
        cred = [sources[i].credibility for i in self.source_idx if 0 <= i < len(sources)]
        if not cred:
            return Credibility.LOW
        highs = sum(1 for c in cred if c == Credibility.HIGH)
        if len(cred) >= 2 and highs >= 1:
            return Credibility.HIGH
        if highs >= 1 or len(cred) >= 2:
            return Credibility.MEDIUM
        return Credibility.LOW


@dataclass
class EvidenceLedger:
    sources: list[Source] = field(default_factory=list)
    claims: list[Claim] = field(default_factory=list)

    def add_source(self, url: str, title: str = "") -> int:
        for i, s in enumerate(self.sources):
            if s.url == url:
                return i
        self.sources.append(Source.from_url(url, title))
        return len(self.sources) - 1

    def coverage(self) -> dict:
        total = len(self.claims)
        supported = sum(1 for c in self.claims if c.source_idx)
        conf = [c.confidence(self.sources) for c in self.claims]
        high = sum(1 for c in conf if c == Credibility.HIGH)
        med = sum(1 for c in conf if c == Credibility.MEDIUM)
        pct = round(100 * supported / total) if total else 0
        return {
            "sources_analyzed": len(self.sources),
            "major_claims": total,
            "claims_supported": supported,
            "unsupported": total - supported,
            "high_confidence": high,
            "medium_confidence": med,
            "coverage_pct": pct,
        }

    def freshness(self, now: datetime | None = None) -> dict:
        buckets = {"Recent": 0, "Current": 0, "Background": 0, "Unknown": 0}
        for s in self.sources:
            buckets[assess_freshness(s.published, now)] += 1
        return buckets
