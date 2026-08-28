"""Build a rich, honest analytical Report from real mission results.

`build_report` is deterministic (works with no LLM): it extracts sources from the
actual results, tags each finding's confidence from whether it is source-backed,
and computes real evidence-coverage + research-trail stats. `build_report_llm`
adds LLM *synthesis* — an executive snapshot, sharper findings, an optional
qualitative scorecard (explicitly labeled an analyst assessment), and limitations
— strictly from the gathered material. No fabricated numbers or sources; a bad
LLM response falls back to the deterministic report.
"""
from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from app.exec.report import (
    EvidenceCoverage,
    Finding,
    Metric,
    Report,
    ReportSection,
    ResearchTrail,
    Scorecard,
    Table,
)
from app.missions.models import Mission, Task

ChatFn = Callable[[list[dict]], Awaitable[str]]
_URL = re.compile(r"https?://[^\s)\]]+")
_OBJ = re.compile(r"\{.*\}", re.DOTALL)


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


def _urls(text: str) -> list[str]:
    return _URL.findall(text or "")


def _extract_sources(tasks: list[Task]) -> list[str]:
    seen: list[str] = []
    for t in tasks:
        for url in _urls(t.result or ""):
            if url not in seen:
                seen.append(url)
    return seen


def build_report(mission: Mission, tasks: list[Task]) -> Report:
    """Deterministic, source-honest report (no LLM)."""
    objective = mission.objective
    done = [t for t in tasks if t.status.value == "done" and (t.result or "").strip()]
    sources = _extract_sources(tasks)
    usage = (mission.meta.get("usage") or {}) if mission.meta else {}

    findings: list[Finding] = []
    for t in done[:6]:
        ev = _urls(t.result or "")
        findings.append(Finding(
            title=_clean(t.description)[:80], body=(t.result or "").strip()[:600],
            confidence="High" if ev else "Analytical", evidence=ev[:3],
        ))

    supported = sum(1 for f in findings if f.evidence)
    coverage = EvidenceCoverage(
        sources_analyzed=len(sources), claims_supported=supported,
        assessments=len(findings) - supported,
    )
    trail = ResearchTrail(
        sources_used=len(sources), sources_excluded=0,
        areas=[_clean(t.description)[:46] for t in done][:6],
        last_verified=datetime.now(UTC).strftime("%d %b %Y"),
    )

    sections = [
        ReportSection(_clean(t.description), [(t.result or "(no result)").strip()])
        for t in done
    ] or [ReportSection("Analysis",
                        ["No task results were recorded. Re-run with an LLM configured."])]
    sections.append(ReportSection("Report Metadata", [], table=Table(
        ["#", "Task", "Status"],
        [[str(t.id), _clean(t.description)[:70], t.status.value] for t in tasks],
        "Table 1 — Analysis scope (mission task coverage).")))

    snapshot = [
        Metric("Report Type", _detect_type(objective).replace("_", " ").title()),
        Metric("Sources Used", str(len(sources))),
        Metric("Key Findings", str(len(findings))),
    ]

    limitations = [
        "External source verification was limited to links captured during the mission.",
        "Interpretive statements are analytical assessments, not measured facts.",
    ]
    if not sources:
        limitations.insert(
            0, "No external sources were captured; findings rest on model synthesis.")

    return Report(
        title=_clean(objective), subtitle="Analytical Report",
        report_type=_detect_type(objective),
        meta={"mission_id": mission.id,
              "date": datetime.now(UTC).strftime("%d %B %Y"), "sources": len(sources)},
        snapshot=snapshot, executive_summary=_default_summary(objective, len(done)),
        findings=findings, coverage=coverage, trail=trail, sections=sections,
        methodology=_methodology(mission, tasks, usage), limitations=limitations,
        sources=sources,
    )


def _default_summary(objective: str, n: int) -> str:
    return (f"This report presents an analysis of: {objective}. It is synthesized from "
            f"{n} completed research and analysis task(s) executed by the Agentic AI OS "
            f"mission runtime. Findings are tagged by confidence; interpretive statements "
            f"are analytical assessments rather than measured facts.")


def _methodology(mission: Mission, tasks: list[Task], usage: dict) -> str:
    return ("The objective was decomposed into a task graph and executed by "
            "role-specialized agents (researcher / analyst / executor) under a critic, then "
            f"synthesized into this structured report. Mission #{mission.id} · {len(tasks)} "
            f"tasks · {usage.get('tokens', 0)} tokens · ${usage.get('usd', 0):.4f}. Sources "
            "were extracted from gathered results; unverifiable items are stated as such.")


_SYS = (
    "You are a senior research analyst. From the provided mission objective and raw "
    "task results, produce ONLY a JSON object with these keys. "
    "snapshot: a list of objects with label and value (e.g. Market Leader, Strongest "
    "Challenger, Biggest Risk) when relevant. "
    "findings: a list of objects with title, body, and confidence (High, Medium, or "
    "Low). "
    "scorecard (optional): an object with dimensions (list), entities (list), and "
    "scores (map from entity to a list of integers 0-5 per dimension). Scores are a "
    "qualitative analyst assessment only, never a measured statistic. "
    "limitations: a list of strings. "
    "Base everything strictly on the provided material. NEVER invent sources, URLs, "
    "or quantitative market figures."
)


def _synthesize_into(report: Report, data: dict) -> None:
    snap = data.get("snapshot")
    if isinstance(snap, list):
        report.snapshot = [Metric(str(m.get("label", "")), str(m.get("value", "")))
                           for m in snap if isinstance(m, dict)][:4] or report.snapshot
    fnd = data.get("findings")
    if isinstance(fnd, list) and fnd:
        report.findings = [Finding(str(f.get("title", ""))[:80], str(f.get("body", "")),
                                   str(f.get("confidence", "Analytical")))
                           for f in fnd if isinstance(f, dict)][:7]
    sc = data.get("scorecard")
    if isinstance(sc, dict) and sc.get("dimensions") and sc.get("entities"):
        scores = {e: [int(x) for x in sc["scores"].get(e, [])]
                  for e in sc["entities"] if isinstance(sc.get("scores"), dict)}
        if scores:
            report.scorecard = Scorecard(
                dimensions=[str(d) for d in sc["dimensions"]],
                entities=[str(e) for e in sc["entities"]], scores=scores)
    lim = data.get("limitations")
    if isinstance(lim, list) and lim:
        report.limitations = [str(x) for x in lim][:5]


async def build_report_llm(mission: Mission, tasks: list[Task], chat_fn: ChatFn) -> Report:
    """Deterministic base + LLM synthesis (snapshot/findings/scorecard/limitations)."""
    report = build_report(mission, tasks)
    done = [t for t in tasks if (t.result or "").strip()]
    material = f"OBJECTIVE: {mission.objective}\n\n" + "\n\n".join(
        f"[{_clean(t.description)}]\n{(t.result or '').strip()[:1200]}" for t in done[:8]
    )
    try:
        raw = await chat_fn([{"role": "system", "content": _SYS},
                             {"role": "user", "content": material}])
        m = _OBJ.search(raw or "")
        if m:
            _synthesize_into(report, json.loads(m.group(0)))
    except Exception:
        pass  # keep the deterministic report
    return report
