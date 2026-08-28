"""Evidence layer: source typing, credibility, freshness, confidence, ledger."""
from datetime import UTC, datetime

from app.exec.evidence import (
    Claim,
    ClaimType,
    Credibility,
    EvidenceLedger,
    Source,
    SourceType,
    assess_credibility,
    assess_freshness,
    source_type_from_url,
)

NOW = datetime(2026, 8, 28, tzinfo=UTC)


def test_source_type_from_url():
    assert source_type_from_url("https://arxiv.org/abs/1") == SourceType.ACADEMIC
    assert source_type_from_url("https://data.gov/x") == SourceType.GOVERNMENT
    assert source_type_from_url("https://reuters.com/a") == SourceType.NEWS
    assert source_type_from_url("https://gartner.com/r") == SourceType.INDUSTRY
    assert source_type_from_url("https://nvidia.com/ai") == SourceType.COMPANY
    assert source_type_from_url("not a url") == SourceType.OTHER


def test_credibility_heuristic_labeled():
    assert assess_credibility(SourceType.ACADEMIC) == Credibility.HIGH
    assert assess_credibility(SourceType.NEWS) == Credibility.MEDIUM
    assert assess_credibility(SourceType.OTHER) == Credibility.LOW


def test_freshness_buckets():
    assert assess_freshness(None) == "Unknown"
    assert assess_freshness("2026-08-20", NOW) == "Recent"       # < 30d
    assert assess_freshness("2026-02-01", NOW) == "Current"      # < 12mo
    assert assess_freshness("2023-01-01", NOW) == "Background"   # older
    assert assess_freshness("garbage", NOW) == "Unknown"


def test_source_from_url_populates_metadata():
    s = Source.from_url("https://arxiv.org/abs/2401")
    assert s.stype == SourceType.ACADEMIC and s.credibility == Credibility.HIGH
    assert s.publisher == "arxiv.org"


def test_claim_confidence_is_earned():
    hi = Source.from_url("https://arxiv.org/a")     # High
    med = Source.from_url("https://nvidia.com/b")   # Medium (company)
    srcs = [hi, med]
    assert Claim("x", source_idx=[0, 1]).confidence(srcs) == Credibility.HIGH   # 2 + a High
    assert Claim("x", source_idx=[1]).confidence(srcs) == Credibility.LOW        # 1 medium only
    assert Claim("x", source_idx=[]).confidence(srcs) == Credibility.LOW         # unsupported
    assert Claim("x", source_idx=[0]).confidence(srcs) == Credibility.MEDIUM     # 1 High


def test_ledger_dedupes_and_reports_coverage():
    led = EvidenceLedger()
    a = led.add_source("https://arxiv.org/a")
    b = led.add_source("https://nvidia.com/b")
    assert led.add_source("https://arxiv.org/a") == a   # dedup
    led.claims = [
        Claim("Supported fact", ClaimType.FACT, [a, b]),
        Claim("Analytical view", ClaimType.ANALYSIS, [b]),
        Claim("Pure inference", ClaimType.INFERENCE, []),
    ]
    cov = led.coverage()
    assert cov["sources_analyzed"] == 2
    assert cov["major_claims"] == 3 and cov["claims_supported"] == 2
    assert cov["unsupported"] == 1
    assert cov["high_confidence"] == 1        # the 2-source claim with a High
    assert 0 <= cov["coverage_pct"] <= 100


def test_ledger_freshness_distribution():
    led = EvidenceLedger()
    led.sources = [Source("u1", published="2026-08-20"), Source("u2", published=None)]
    fr = led.freshness(NOW)
    assert fr["Recent"] == 1 and fr["Unknown"] == 1


def test_empty_ledger_is_honest():
    cov = EvidenceLedger().coverage()
    assert cov["sources_analyzed"] == 0 and cov["coverage_pct"] == 0
