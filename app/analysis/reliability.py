"""Transparent, configurable source-reliability model.

Reliability is a product of interpretable factors rather than a magic number:

    reliability = authority x recency x specificity x corroboration

Every factor is a labelled heuristic in [0, 1]; the resulting `basis` string is
carried on the source so the report/observability layer can show exactly how the
score was derived (no fake scientific precision). Corroboration defaults to 1.0
and is refined in Phase 5 (cross-source agreement). All priors are configurable.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Authority priors by source type (0..1). Deliberately conservative and editable.
_AUTHORITY = {
    "government": 0.95, "academic": 0.95, "primary": 0.90,
    "industry": 0.80, "news": 0.75, "company": 0.70, "other": 0.40,
}
_RECENCY = {"Recent": 1.0, "Current": 0.92, "Background": 0.78, "Unknown": 0.85}


@dataclass
class ReliabilityConfig:
    authority: dict[str, float] = field(default_factory=lambda: dict(_AUTHORITY))
    recency: dict[str, float] = field(default_factory=lambda: dict(_RECENCY))
    specificity_specific: float = 1.0   # a deep, specific page
    specificity_homepage: float = 0.75  # a domain root / landing page


DEFAULT = ReliabilityConfig()


def authority_factor(source_type: str, cfg: ReliabilityConfig = DEFAULT) -> float:
    return cfg.authority.get(source_type, 0.4)


def recency_factor(freshness: str, cfg: ReliabilityConfig = DEFAULT) -> float:
    return cfg.recency.get(freshness, 0.85)


def specificity_factor(url: str, cfg: ReliabilityConfig = DEFAULT) -> float:
    """A specific article/page scores higher than a bare homepage."""
    after_domain = (url.split("//", 1)[-1].split("/", 1)[1:] or [""])[0].strip("/")
    return cfg.specificity_specific if after_domain else cfg.specificity_homepage


def derive_published(url: str) -> str | None:
    """Best-effort publication date from the URL (e.g. arXiv ID encodes YYMM)."""
    m = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{2})(\d{2})\.\d", url, re.I)
    if m:
        return f"20{m.group(1)}-{m.group(2)}-01"
    return None


def score_source(
    source_type: str, freshness: str, url: str,
    corroboration: float = 1.0, cfg: ReliabilityConfig = DEFAULT,
) -> tuple[float, str]:
    """Return (reliability in [0,1], human-readable basis string)."""
    a = authority_factor(source_type, cfg)
    r = recency_factor(freshness, cfg)
    sp = specificity_factor(url, cfg)
    score = max(0.0, min(1.0, a * r * sp * corroboration))
    basis = (f"heuristic: authority {a:.2f} x recency {r:.2f} x specificity {sp:.2f}"
             + (f" x corroboration {corroboration:.2f}" if corroboration != 1.0 else ""))
    return round(score, 3), basis
