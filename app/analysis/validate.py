"""Report validator (Phase 11): don't ship an unsupported report.

Before rendering, the report is checked against evidence-integrity rules — every
finding has content and (if it states a figure) a source, every number has a
source, sources are well-formed URLs, no empty/duplicate sections, no raw
markdown leaks, and limitations are present. `repair_report` fixes what can be
fixed automatically (drop empty/duplicate sections, scrub unsupported figures,
ensure limitations) so the pipeline repairs rather than ships broken output; any
remaining hard errors are surfaced for the caller.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.exec.report import Report

_FIG = re.compile(r"\d+(?:\.\d+)?\s?%|\$\s?\d")
_MD_LEAK = re.compile(r"(?:^|\n)\s*#{1,6}\s|\*\*\S|(?:^|\n)\s*[-*]\s{1,3}\S")
_URL_OK = re.compile(r"^https?://[^\s]+\.[^\s]+$")
_PCT = re.compile(r"\s*(?:\b(?:at|of|around|about|~)\s+)?\(?\d+(?:\.\d+)?\s?%\)?", re.I)
_CUR = re.compile(r"\s*(?:\b(?:at|of|~)\s+)?\(?\$\s?\d[\d,]*(?:\.\d+)?\)?", re.I)


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _scrub_figures(text: str) -> str:
    s = _CUR.sub("", _PCT.sub("", text or ""))
    s = re.sub(r"\s+([.,;:)])", r"\1", s)
    return re.sub(r"\s{2,}", " ", s).strip()


def validate_report(report: Report, artifact=None) -> ValidationResult:
    """Check evidence-integrity rules; returns errors (block) + warnings (allow)."""
    errors: list[str] = []
    warnings: list[str] = []

    if not report.findings:
        errors.append("report has no findings")
    for f in report.findings:
        if not (f.body or "").strip():
            errors.append(f"empty finding: {f.title!r}")
        if _FIG.search(f.body or "") and not f.source_refs:
            errors.append(f"unsupported figure in finding: {f.title!r}")
        if _MD_LEAK.search(f.body or ""):
            warnings.append(f"raw markdown in finding: {f.title!r}")

    headings = [s.heading for s in report.sections]
    dupes = sorted({h for h in headings if headings.count(h) > 1})
    if dupes:
        errors.append(f"duplicate sections: {dupes}")
    for s in report.sections:
        if not any(p.strip() for p in s.paragraphs) and s.table is None:
            errors.append(f"empty section: {s.heading!r}")

    for s in report.source_records:
        if not _URL_OK.match(s.url):
            errors.append(f"malformed source url: {s.url!r}")
    if _MD_LEAK.search(report.executive_summary or ""):
        warnings.append("raw markdown in executive summary")
    if not report.limitations:
        errors.append("report is missing a Limitations section")

    if artifact is not None:
        for m in artifact.metrics:
            if m.derivation == "reported" and not m.source_ids:
                errors.append(f"number without a source: {m.name!r}")
        for f in artifact.findings:
            if not f.evidence_ids:
                errors.append(f"finding without evidence: {f.id}")
            if not f.confidence:
                errors.append(f"finding without confidence: {f.id}")

    return ValidationResult(ok=not errors, errors=errors, warnings=warnings)


def repair_report(report: Report) -> Report:
    """Fix auto-fixable violations so validation can pass (mutates + returns)."""
    # de-duplicate + drop empty sections
    seen: set[str] = set()
    kept = []
    for s in report.sections:
        if s.heading in seen:
            continue
        if not any(p.strip() for p in s.paragraphs) and s.table is None:
            continue
        seen.add(s.heading)
        kept.append(s)
    report.sections = kept

    # never present an unsupported figure as fact
    for f in report.findings:
        if _FIG.search(f.body or "") and not f.source_refs:
            f.title, f.body = _scrub_figures(f.title), _scrub_figures(f.body)

    # drop empty findings
    report.findings = [f for f in report.findings if (f.body or "").strip()]

    if not report.limitations:
        report.limitations = [
            "This report draws on a limited set of references and may not be exhaustive."]
    return report
