"""Source reliability model: factor-based, transparent, configurable."""
from app.analysis.artifact import ArtifactSource
from app.analysis.reliability import (
    ReliabilityConfig,
    derive_published,
    score_source,
    specificity_factor,
)


def test_score_is_product_of_labelled_factors():
    score, basis = score_source("academic", "Recent", "https://arxiv.org/abs/2005.11401")
    assert 0.9 <= score <= 1.0
    assert "authority" in basis and "recency" in basis and "specificity" in basis


def test_authority_ordering():
    gov, _ = score_source("government", "Current", "https://x.gov/a/b")
    company, _ = score_source("company", "Current", "https://x.com/a/b")
    other, _ = score_source("other", "Current", "https://x.io/a/b")
    assert gov > company > other


def test_homepage_less_specific_than_deep_page():
    assert specificity_factor("https://reuters.com/") < specificity_factor(
        "https://reuters.com/tech/nvidia-cuda")


def test_derive_published_from_arxiv():
    assert derive_published("https://arxiv.org/abs/2005.11401") == "2020-05-01"
    assert derive_published("https://en.wikipedia.org/wiki/CUDA") is None


def test_corroboration_penalty_and_rescore():
    s = ArtifactSource.from_url("S1", "https://en.wikipedia.org/wiki/CUDA")
    base = s.reliability
    s.rescore(0.5)                       # weak corroboration lowers reliability
    assert s.reliability < base
    assert "corroboration" in s.reliability_basis and s.corroboration == 0.5


def test_config_is_editable():
    cfg = ReliabilityConfig()
    cfg.authority["company"] = 0.99
    score, _ = score_source("company", "Recent", "https://x.com/a/b", cfg=cfg)
    assert score >= 0.98
