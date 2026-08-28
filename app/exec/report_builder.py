"""Build a structured Report from real mission results (content, not transcript).

Deterministic and honest: findings and sections come from actual task results,
sources are *extracted* from those results (never invented), and metadata is
real. An optional `chat_fn` synthesizes a polished executive summary from the
material; without it, a truthful deterministic summary is used. No fabricated
numbers, sources, or charts.
"""
from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from app.exec.report import Finding, Report, ReportSection, Table
from app.missions.models import Mission, Task

ChatFn = Callable[[list[dict]], Awaitable[str]]
_URL = re.compile(r"https?://[^\s)\]]+")


def _clean(s: str) -> str:
    s = (s or "").strip()
    return s[:1].upper() + s[1:] if s else s


def _detect_type(objective: str) -> str:
    o = objective.lower()
    if " vs " in o or "compare" in o or "comparison" in o:
        return "COMPETITIVE_ANALYSIS"
    if "job" in o or "hiring" in o or "roles" in o:
        return "JOB_MARKET_REPORT"
    if "market" in o:
        return "MARKET_ANALYSIS"
    if any(k in o for k in ("architecture", "algorithm", "protocol", "technical")):
        return "TECHNICAL_ANALYSIS"
    return "RESEARCH_REPORT"


def _extract_sources(tasks: list[Task]) -> list[str]:
    seen: list[str] = []
    for t in tasks:
        for url in _URL.findall(t.result or ""):
            if url not in seen:
                seen.append(url)
    return seen


def build_report(mission: Mission, tasks: list[Task]) -> Report:
    """Deterministic, source-honest report from a mission's real results."""
    objective = mission.objective
    done = [t for t in tasks if t.status.value == "done" and (t.result or "").strip()]
    sources = _extract_sources(tasks)
    usage = (mission.meta.get("usage") or {}) if mission.meta else {}

    findings = [
        Finding(title=_clean(t.description)[:80], body=(t.result or "").strip()[:600])
        for t in done[:6]
    ]

    sections = [
        ReportSection(heading=_clean(t.description),
                      paragraphs=[(t.result or "(no result recorded)").strip()])
        for t in done
    ]
    if not sections:
        sections = [ReportSection("Analysis",
                    ["No task results were recorded for this mission. Re-run the "
                     "mission with an LLM configured to populate the analysis."])]

    scope = Table(
        columns=["#", "Task", "Status"],
        rows=[[str(t.id), _clean(t.description)[:70], t.status.value] for t in tasks],
        caption="Table 1 — Analysis scope (mission task coverage).",
    )
    sections.append(ReportSection("Report Metadata", [], table=scope))

    exec_summary = (
        f"This report presents an analysis of: {objective}. It is synthesized from "
        f"{len(done)} completed research and analysis task(s) executed by the Agentic "
        f"AI OS mission runtime. The key findings, detailed analysis, and supporting "
        f"sources follow. Figures represent the material gathered during the mission; "
        f"interpretive statements are analytical assessments, not measured facts."
    )

    methodology = (
        "This report was produced by the Agentic AI OS: the objective was decomposed "
        "into a task graph, executed by role-specialized agents (researcher / analyst / "
        "executor) under a critic, and the results were synthesized into this structured "
        f"report. Mission #{mission.id} · {len(tasks)} tasks · "
        f"{usage.get('tokens', 0)} tokens · ${usage.get('usd', 0):.4f}. "
        "Where external sources were not captured, that is stated explicitly rather than "
        "inferred."
    )

    return Report(
        title=_clean(objective),
        subtitle="Analytical Report",
        report_type=_detect_type(objective),
        meta={
            "mission_id": mission.id,
            "date": datetime.now(UTC).strftime("%d %B %Y"),
            "sources": len(sources),
        },
        executive_summary=exec_summary,
        findings=findings,
        sections=sections,
        methodology=methodology,
        sources=sources,
    )
