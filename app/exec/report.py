"""Structured analytical report model — the deliverable, not a task transcript.

A `Report` is what a professional analyst would produce: cover metadata, an
executive summary, key findings, analytical sections (optionally with a table),
methodology, and sources. The report *builder* fills this from real mission
results; the *renderer* (report_pdf) turns it into a professional PDF. Keeping
the model separate from rendering is the whole point — content vs presentation.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Finding:
    title: str
    body: str


@dataclass
class Table:
    columns: list[str]
    rows: list[list[str]]
    caption: str = ""


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
    meta: dict = field(default_factory=dict)          # mission_id, date, sources, …
    executive_summary: str = ""
    findings: list[Finding] = field(default_factory=list)
    sections: list[ReportSection] = field(default_factory=list)
    methodology: str = ""
    sources: list[str] = field(default_factory=list)
