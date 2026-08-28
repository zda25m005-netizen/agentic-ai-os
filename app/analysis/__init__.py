"""Evidence-first analysis layer.

Turns gathered research into a structured **Analysis Artifact** (sources ->
claims -> metrics/comparisons -> findings) that the report's LLM step *writes
over* — the model organises and explains, it does not invent the analysis. This
is the backbone that separates the DATA/EVIDENCE, ANALYSIS, REASONING and REPORT
layers so the system is demonstrably reasoning over evidence, not free-forming.
"""
from app.analysis.artifact import (
    AnalysisArtifact,
    ArtifactClaim,
    ArtifactFinding,
    ArtifactSource,
    Comparison,
    Metric,
    StatementType,
    Verification,
)

__all__ = [
    "AnalysisArtifact",
    "ArtifactClaim",
    "ArtifactFinding",
    "ArtifactSource",
    "Comparison",
    "Metric",
    "StatementType",
    "Verification",
]
