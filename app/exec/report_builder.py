"""Build a rich, honest analytical Report from real mission results.

`build_report` is deterministic (works with no LLM): it extracts sources from the
actual results, tags each finding's confidence from whether it is source-backed,
and computes real evidence-coverage stats. `build_report_llm`
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

from app.exec.evidence import Claim, ClaimType, EvidenceLedger, assess_freshness
from app.exec.report import (
    EvidenceCoverage,
    Finding,
    Metric,
    Report,
    ReportSection,
    Scorecard,
    SourceRecord,
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


# the researcher appends a trailing "Sources:\n<url>..." block; URLs go to the
# register, so strip the leftover label/block from displayed prose.
_SOURCES_BLOCK = re.compile(r"\n+\s*sources?\s*:\s*(?:\n.*)?$", re.IGNORECASE | re.DOTALL)


def _strip_sources_block(text: str) -> str:
    return _SOURCES_BLOCK.sub("", text or "").strip()


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

    # Evidence ledger: register each finding's URLs as sources, tag each finding as a
    # claim, and let confidence be *earned* from source count + quality (not guessed).
    now = datetime.now(UTC)
    ledger = EvidenceLedger()
    findings: list[Finding] = []
    for t in done[:6]:
        idxs = [ledger.add_source(u) for u in _urls(t.result or "")]
        claim = Claim(_clean(t.description)[:80], ClaimType.ANALYSIS, idxs)
        ledger.claims.append(claim)
        conf = claim.confidence(ledger.sources).value if idxs else "Analytical"
        findings.append(Finding(
            title=_clean(t.description)[:80],
            body=_strip_sources_block(t.result or "")[:600],
            confidence=conf, evidence=[ledger.sources[i].url for i in idxs][:3],
            source_refs=[i + 1 for i in idxs],  # 1-based, for claim traceability
        ))

    sources = [s.url for s in ledger.sources]
    source_records = [
        SourceRecord(
            ref=i + 1, url=s.url, publisher=s.publisher,
            stype=s.stype.value.title(), credibility=s.credibility.value,
            freshness=assess_freshness(s.published, now),
        )
        for i, s in enumerate(ledger.sources)
    ]
    freshness = ledger.freshness(now)
    cov = ledger.coverage()
    coverage = EvidenceCoverage(
        sources_analyzed=cov["sources_analyzed"], claims_supported=cov["claims_supported"],
        assessments=cov["unsupported"],
    )

    sections = [
        ReportSection(_clean(t.description),
                      [_strip_sources_block(t.result or "") or "(no result)"])
        for t in done
    ] or [ReportSection("Analysis",
                        ["No analysis content was available for this report."])]

    snapshot = [
        Metric("Report Type", _detect_type(objective).replace("_", " ").title()),
        Metric("Sources Used", str(len(sources))),
        Metric("Key Findings", str(len(findings))),
    ]

    limitations = [
        "External source verification was limited to the sources gathered for this report.",
        "Interpretive statements are analytical assessments, not measured facts.",
    ]
    if not sources:
        limitations.insert(
            0, "No external sources were available; findings rest on analytical synthesis.")

    report = Report(
        title=_clean(objective), subtitle="Analytical Report",
        report_type=_detect_type(objective),
        meta={"date": datetime.now(UTC).strftime("%d %B %Y"), "sources": len(sources),
              "status": (mission.meta or {}).get("status", "Completed")},
        snapshot=snapshot, executive_summary=_default_summary(objective, len(done)),
        findings=findings, coverage=coverage, sections=sections,
        methodology=_methodology(), limitations=limitations,
        sources=sources, source_records=source_records, freshness=freshness,
        critic_flags=_critic_flags(mission),
    )
    apply_integrity(report)
    return report


def _critic_flags(mission: Mission) -> list[str]:
    """Human-readable critic events (e.g. topic drift) from the mission telemetry."""
    out: list[str] = []
    for fl in (mission.meta.get("critic_flags") or []) if mission.meta else []:
        if not isinstance(fl, dict):
            continue
        tid = fl.get("task_id", "?")
        note = str(fl.get("note", "")).strip()
        out.append(f"Topic drift on Task #{tid}: {note} The task was regenerated to "
                   f"refocus on the mission objective.")
    return out


# numbers presented as facts: percentages and currency figures
_FIGURE = re.compile(r"\d+(?:\.\d+)?\s?%|\$\s?\d")
_WORD4 = re.compile(r"[A-Za-z]{4,}")
# scrub an unsupported percentage/currency figure (with any leading "at/of/~")
_PCT = re.compile(r"\s*(?:\b(?:at|of|around|about|approximately|reaching|up to|~)\s+)?"
                  r"\(?\d+(?:\.\d+)?\s?%\)?", re.IGNORECASE)
_CUR = re.compile(r"\s*(?:\b(?:at|of|around|about|~)\s+)?\(?\$\s?\d[\d,]*(?:\.\d+)?\)?",
                  re.IGNORECASE)
_GUARDRAIL = (
    "Unsupported quantitative figures (e.g. percentages) generated during analysis were "
    "removed from the findings; only qualitative, evidence-tagged assessments are shown."
)


def _scrub_figures(text: str) -> str:
    """Remove fabricated percentage/currency figures from text presented as fact."""
    s = _CUR.sub("", _PCT.sub("", text or ""))
    s = re.sub(r"\s+([.,;:)])", r"\1", s)
    return re.sub(r"\s{2,}", " ", s).strip()


def _source_terms(sr) -> set[str]:
    """Significant terms describing a source (from its URL slug + publisher)."""
    slug = sr.url.rstrip("/").rsplit("/", 1)[-1].replace("_", " ").replace("-", " ")
    return {w.lower() for w in _WORD4.findall(f"{slug} {sr.publisher or ''}")}


def _conf_from_refs(refs: list[int], by_ref: dict) -> str:
    """Earned confidence from source count + credibility (mirrors Claim.confidence)."""
    creds = [by_ref[r].credibility for r in refs if r in by_ref]
    if not creds:
        return "Analytical"
    highs = sum(1 for c in creds if c == "High")
    if len(creds) >= 2 and highs >= 1:
        return "High"
    if highs >= 1 or len(creds) >= 2:
        return "Medium"
    return "Low"


def apply_integrity(report: Report) -> None:
    """Single source of truth: derive EVERY evidence metric from one graph.

    Links each finding to the sources on its topic, recomputes per-finding
    confidence purely from that backing (overriding any LLM-asserted label so
    confidence is earned, not claimed), then rebuilds coverage, the integrity
    block, and the overall confidence from the same numbers — so they can never
    contradict each other. Never fabricates: with no sources, gaps show plainly.
    """
    srs = report.source_records
    by_ref = {sr.ref: sr for sr in srs}

    # 1) Attach source refs to findings that lack them, by topical overlap.
    for f in report.findings:
        if not f.source_refs and srs:
            fterms = {w.lower() for w in _WORD4.findall(f"{f.title} {f.body}")}
            f.source_refs = [sr.ref for sr in srs if _source_terms(sr) & fterms][:3]

    # 2) Never present an unsupported figure as fact: scrub percentages/currency from
    #    findings that have no source backing (keep them where a source is cited).
    scrubbed = False
    for f in report.findings:
        if not f.source_refs and _FIGURE.search(f"{f.title} {f.body}"):
            f.title, f.body = _scrub_figures(f.title), _scrub_figures(f.body)
            scrubbed = True
    for m in report.snapshot:  # headline snapshot values must stay qualitative
        if _FIGURE.search(m.value):
            m.value = _scrub_figures(m.value) or m.value
            scrubbed = True

    # 3) Confidence comes ONLY from the evidence graph, not the LLM's label.
    for f in report.findings:
        f.confidence = _conf_from_refs(f.source_refs, by_ref)
        f.unverified_figures = (not f.source_refs) and bool(_FIGURE.search(f.body or ""))

    total = len(report.findings)
    supported = sum(1 for f in report.findings if f.source_refs)
    unverified = sum(1 for f in report.findings if f.unverified_figures)
    highs = sum(1 for f in report.findings if f.confidence == "High")
    mediums = sum(1 for f in report.findings if f.confidence == "Medium")

    # 3) Coverage is rebuilt from the same findings so it matches the integrity box.
    report.coverage = EvidenceCoverage(
        sources_analyzed=len(srs), claims_supported=supported, assessments=total - supported)
    pct = report.coverage.coverage_pct

    # 4) Overall confidence is a function of the graph, not an LLM assertion.
    if supported and pct >= 60 and highs >= 1:
        overall = "High"
    elif supported:
        overall = "Medium"
    else:
        overall = "Analytical"

    report.integrity = {
        "sources_analyzed": len(srs),
        "claims_extracted": total,
        "claims_supported": supported,
        "unsupported": total - supported,
        "coverage_pct": pct,
        "high_confidence": highs,
        "medium_confidence": mediums,
        "unverified_figures": unverified,
        "overall_confidence": overall,
    }
    if (scrubbed or unverified) and not any(
            "quantitative figures" in x for x in report.limitations):
        report.limitations.insert(0, _GUARDRAIL)


def _default_summary(objective: str, n: int) -> str:
    return (f"This report analyzes {objective[:1].lower() + objective[1:]}. Findings are "
            "tagged by the strength of their supporting evidence; interpretive statements "
            "are analytical assessments rather than measured facts.")


def _methodology() -> str:
    return ("The analysis draws on sources gathered through targeted research on the "
            "objective. Each source was classified by type and credibility, and every "
            "finding is tagged by the strength of its supporting evidence. Quantitative "
            "claims without a supporting source are marked as unverified; interpretive "
            "statements are analytical assessments rather than measured facts.")


_SYS = (
    "You are a senior research analyst. From the provided mission objective and raw "
    "task results, produce ONLY a JSON object with these keys. "
    "snapshot: a list of objects with label and value (e.g. Market Leader, Strongest "
    "Challenger, Biggest Risk) when relevant. "
    "findings: a list of objects with title, body, and confidence (High, Medium, or "
    "Low). "
    "problem_definition: 1-2 sentences defining the topic and why it matters. "
    "approaches (optional): a list of objects, one per option in the objective, each "
    "with name, how_it_works (string), advantages (list), disadvantages (list), "
    "failure_modes (list), mitigations (list). Use the objective's real option names. "
    "comparative_analysis (optional): a short paragraph comparing the options across "
    "the relevant dimensions (accuracy, freshness, cost, scalability, reliability). "
    "failure_analysis (optional): a list of objects with failure, impact, mitigation. "
    "scorecard (optional): an object with dimensions (list), entities (list), and "
    "scores (map from entity to a list of integers 0-5 per dimension). Scores are a "
    "qualitative analyst assessment only, never a measured statistic. "
    "recommendation: one decisive paragraph stating what to do and, when the objective "
    "is a design/architecture question, the recommended component pipeline in words "
    "(e.g. 'Router -> Structured store + Vector retrieval -> Composer -> LLM'). "
    "decision_rationale: a list of objects with requirement, decision, and reason. "
    "strategic_implications: a list of 2-4 strings, each a sharp 'so what' insight. "
    "limitations: a list of strings. "
    "CRITICAL naming: name snapshot and scorecard entities using the ACTUAL options in "
    "the objective (e.g. 'Vector Retrieval (RAG)', 'Fine-Tuning', 'Structured Memory'), "
    "never generic placeholders like 'Approach A/B/C', and use the same names everywhere. "
    "Base everything strictly on the provided material. NEVER invent sources or URLs, and "
    "NEVER state specific percentages, dollar amounts, or market-share numbers as fact; "
    "use qualitative language and the 0-5 scores instead."
)


def _norm_approach(a: dict) -> dict:
    def _lst(key: str) -> list[str]:
        v = a.get(key)
        return [str(x) for x in v][:6] if isinstance(v, list) else []
    return {
        "name": str(a.get("name", ""))[:80],
        "how_it_works": str(a.get("how_it_works", "")),
        "advantages": _lst("advantages"),
        "disadvantages": _lst("disadvantages"),
        "failure_modes": _lst("failure_modes"),
        "mitigations": _lst("mitigations"),
    }


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
    pd = data.get("problem_definition")
    if isinstance(pd, str) and pd.strip():
        report.problem_definition = pd.strip()
    ap = data.get("approaches")
    if isinstance(ap, list) and ap:
        report.approaches = [
            _norm_approach(a) for a in ap if isinstance(a, dict) and a.get("name")][:5]
    ca = data.get("comparative_analysis")
    if isinstance(ca, str) and ca.strip():
        report.comparative_analysis = ca.strip()
    fa = data.get("failure_analysis")
    if isinstance(fa, list) and fa:
        report.failure_analysis = [
            {"failure": str(d.get("failure", "")), "impact": str(d.get("impact", "")),
             "mitigation": str(d.get("mitigation", ""))}
            for d in fa if isinstance(d, dict) and d.get("failure")][:8]
    rec = data.get("recommendation")
    if isinstance(rec, str) and rec.strip():
        report.recommendation = rec.strip()
    dr = data.get("decision_rationale")
    if isinstance(dr, list) and dr:
        report.decision_rationale = [
            {"requirement": str(d.get("requirement", "")), "decision": str(d.get("decision", "")),
             "reason": str(d.get("reason", ""))}
            for d in dr if isinstance(d, dict) and d.get("requirement")][:8]
    si = data.get("strategic_implications")
    if isinstance(si, list) and si:
        report.strategic_implications = [str(x) for x in si][:4]
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
    apply_integrity(report)  # recompute after synthesis replaces findings/limitations
    return report
