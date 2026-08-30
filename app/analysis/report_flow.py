"""Evidence-first report flow (Phase 12): artifact -> LLM synthesis -> validate.

This is where the LLM finally enters — but only as a *writing* layer over the
already-built evidence graph. It may add interpretation/implication to existing
findings and write the executive summary / problem definition / recommendation,
all grounded in the artifact; it may NOT introduce facts, numbers, sources, or
claims. The result is repaired + validated before rendering, so the pipeline
never ships an unsupported report. A bad or missing LLM leaves a fully valid
deterministic report.
"""
from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from app.analysis.artifact import AnalysisArtifact
from app.analysis.pipeline import build_analysis_artifact
from app.analysis.scoring import _mentions, _polarity, score_artifact
from app.analysis.to_report import artifact_to_report
from app.analysis.validate import repair_report
from app.exec.report import Report
from app.exec.report_builder import _default_summary, _synthesize_into
from app.missions.models import Mission, Task

ChatFn = Callable[[list[dict]], Awaitable[str]]
_OBJ = re.compile(r"\{.*\}", re.DOTALL)

# Shared preamble + hard grounding rules used by every focused synthesis call.
_ANALYST = (
    "You are a senior research analyst writing a rigorous, evidence-grounded report. "
    "You are given STRUCTURED evidence as JSON. Organise and EXPLAIN it; do NOT invent. "
)
_RULES = (
    " STRICT RULES: base every statement on the provided evidence; NEVER add facts, "
    "numbers, statistics, sources or claims not in the input; do not state specific "
    "percentages or market figures as fact; do not contradict the verification status; "
    "be specific and cite the evidence you rely on rather than writing generically. "
    "Return ONLY a valid JSON object, no prose outside it."
)

# Call 1 — narrative framing over the whole artifact.
_SYS_NARRATIVE = (
    _ANALYST + "Return ONLY JSON with: "
    "bottom_line: ONE decisive 1-2 sentence judgement (not a definition). "
    "executive_summary, problem_definition, comparative_analysis (strings). "
    "evaluation_framework: [{criterion, definition}]. "
    "key_insights: 3-6 {insight, confidence} non-obvious, evidence-backed takeaways. "
    "evidence_summary: [{finding, strength (Strong/Moderate/Weak), confidence (High/"
    "Medium/Low)}]. "
    "decision_change: 2-4 strings answering 'what evidence would change the "
    "recommendation?'." + _RULES
)

# Call 2 — per-option deep dives, fed each option's own evidence bundle.
_SYS_APPROACHES = (
    _ANALYST + "You are given the research question and, for each option, its evidence "
    "bundle (claims with verification/confidence, per-criterion scores, and counter-"
    "evidence). Write a deep dive for EACH option grounded in its bundle. Return ONLY "
    "JSON with: approaches: [{name, how_it_works, advantages[], disadvantages[], "
    "failure_modes[], mitigations[]}] one per option using the real names, 3-5 concrete "
    "failure_modes each; failure_analysis: [{option, failure, mechanism, probability, "
    "impact, detection, mitigation, residual_risk}] with 3-5 rows PER option. Every "
    "advantage/failure must trace to a claim in that option's bundle." + _RULES
)

# Call 3 — tight reasoning chains + decision, fed bundles + scores + the decision.
_SYS_REASONING = (
    _ANALYST + "You are given the question, per-option evidence bundles, the evidence-"
    "weighted scores, and the derived decision. Produce tight reasoning. Return ONLY "
    "JSON with: reasoning_chains: [{claim, evidence, reasoning, trade_off, counter, "
    "decision}] — each Decision MUST reference a specific score or claim; each chain "
    "MUST include counter (contradicting evidence, or 'none found'); keep them crisp, "
    "no filler. recommendation: a decisive paragraph consistent with the decision AND, "
    "for design/architecture questions, a multi-line ASCII architecture diagram inside "
    "a ```code fence``` (plain ASCII -> | + _ only, NO unicode), showing each component "
    "layer and data flow and why NOT put everything in one mechanism. "
    "decision_rationale: [{requirement, decision, reason}]. "
    "reasoning: [{finding_id, interpretation, implication}] keyed to the given finding "
    "ids." + _RULES
)


def _parse(raw: str) -> dict:
    m = _OBJ.search(raw or "")
    if not m:
        return {}
    try:
        data = json.loads(m.group(0))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _apply_synthesis(art: AnalysisArtifact, data: dict) -> None:
    by_id = {f.id: f for f in art.findings}
    for r in data.get("reasoning", []) if isinstance(data.get("reasoning"), list) else []:
        if not isinstance(r, dict):
            continue
        f = by_id.get(str(r.get("finding_id", "")))
        if f:
            f.interpretation = str(r.get("interpretation", "")).strip()
            f.implication = str(r.get("implication", "")).strip()


def _evidence_bundles(art: AnalysisArtifact) -> list[dict]:
    """Per-option grounded evidence: claims (+verification/refs), scores, counter-evidence.

    Feeding each synthesis call the specific evidence for the option it is writing
    about forces grounded, specific prose instead of generic filler.
    """
    esc = score_artifact(art)
    ref_of = {s.id: i + 1 for i, s in enumerate(art.sources)}
    ewords = {e: {w for w in re.findall(r"[a-z0-9]+", e.lower()) if len(w) > 2}
              for e in art.entities}
    bundles = []
    for e in art.entities:
        claims = [c for c in art.claims if _mentions(c, e, ewords[e])]
        bundles.append({
            "option": e,
            "claims": [{
                "statement": c.statement.strip()[:240],
                "verification": c.verification.value, "confidence": c.confidence,
                "refs": sorted({ref_of[s] for s in c.source_ids if s in ref_of}),
            } for c in claims][:8],
            "counter_evidence": [c.statement.strip()[:200] for c in claims
                                 if _polarity(c.statement) < 0][:4],
            "scores": [{"criterion": cell.criterion, "score": cell.score,
                        "supporting": cell.supporting, "contradicting": cell.contradicting,
                        "confidence": cell.confidence}
                       for cell in esc.cells if cell.entity == e],
        })
    return bundles


async def _call(chat_fn: ChatFn, system: str, payload: dict) -> dict:
    try:
        raw = await chat_fn([
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload)[:8000]},
        ])
        return _parse(raw)
    except Exception:
        return {}


async def synthesize_over_artifact(art: AnalysisArtifact, chat_fn: ChatFn) -> dict:
    """Decomposed synthesis: focused calls (narrative / approaches / reasoning) merged.

    Small models spread thin across a 15-field mega-prompt; three tight calls, each
    fed only what it needs (approaches + reasoning get per-option evidence bundles),
    produce sharper write-ups and tighter reasoning chains. Runs concurrently; any
    call that fails just contributes nothing.
    """
    ctx = art.to_llm_context()
    bundles = _evidence_bundles(art)
    findings = [{"id": f.id, "observation": f.observation} for f in art.findings]
    reason_ctx = {"objective": art.objective, "options": bundles,
                  "findings": findings,
                  "note": "Scores and decision are fixed upstream; explain, do not change."}

    narrative, approaches, reasoning = await asyncio.gather(
        _call(chat_fn, _SYS_NARRATIVE, ctx),
        _call(chat_fn, _SYS_APPROACHES, {"objective": art.objective, "options": bundles}),
        _call(chat_fn, _SYS_REASONING, reason_ctx),
    )
    merged: dict = {}
    for part in (narrative, approaches, reasoning):
        if isinstance(part, dict):
            merged.update(part)
    return merged


async def build_report_evidence_first(
    mission: Mission, tasks: list[Task], chat_fn: ChatFn | None = None,
) -> Report:
    """Assemble the artifact, let the LLM write over it, then repair + return."""
    art = build_analysis_artifact(mission, tasks)

    synth: dict = {}
    if chat_fn is not None and art.findings:
        try:
            synth = await synthesize_over_artifact(art, chat_fn)
            _apply_synthesis(art, synth)
        except Exception:
            synth = {}   # a bad LLM response must never break the report

    status = (mission.meta or {}).get("status", "Completed")
    date = datetime.now(UTC).strftime("%d %B %Y")
    report = artifact_to_report(art, date=date, status=status)

    # Merge the LLM's structured synthesis (scorecard -> charts, approaches, failure
    # matrix, framework, decision rationale) WITHOUT touching the evidence-grounded
    # findings — `_synthesize_into` only replaces findings if the LLM returned some,
    # and we never ask it to, so the grounded findings are preserved.
    if synth:
        synth.pop("findings", None)
        # Scores are evidence-derived (set in artifact_to_report); never let the LLM
        # assign or overwrite them, so every 0-5 traces to supporting/contradicting
        # claims rather than model opinion.
        synth.pop("scorecard", None)
        synth.pop("scoring_rationale", None)
        _synthesize_into(report, synth)
    report.executive_summary = (synth.get("executive_summary") or "").strip() \
        or _default_summary(mission.objective, len(art.findings))
    report.problem_definition = (synth.get("problem_definition") or "").strip()
    report.bottom_line = (synth.get("bottom_line") or "").strip()
    chains = synth.get("reasoning_chains")
    if isinstance(chains, list):
        report.reasoning_chains = [
            {k: str(c.get(k, "")) for k in ("claim", "evidence", "reasoning",
                                            "trade_off", "counter", "decision")}
            for c in chains if isinstance(c, dict) and c.get("claim")][:8]

    def _dicts(key: str, fields: tuple[str, ...], req: str, limit: int = 8) -> list[dict]:
        v = synth.get(key)
        if not isinstance(v, list):
            return []
        out = []
        for d in v:
            if isinstance(d, dict) and d.get(req):
                out.append({f: (d.get(f) if isinstance(d.get(f), list) else str(d.get(f, "")))
                            for f in fields})
        return out[:limit]

    report.key_insights = _dicts("key_insights", ("insight", "confidence"), "insight", 6)
    report.evidence_summary = _dicts(
        "evidence_summary", ("finding", "strength", "confidence"), "finding")
    report.trade_offs = _dicts("trade_offs", ("entity", "pros", "cons"), "entity", 5)
    # scoring_rationale is evidence-derived in artifact_to_report; do not overwrite.
    dc = synth.get("decision_change")
    if isinstance(dc, list):
        report.decision_change = [str(x) for x in dc if str(x).strip()][:5]

    # Recommendation must be proportional to the evidence. If the LLM gave none,
    # fall back to the evidence-grounded decision summary (never "use everything").
    dec = report.decision or {}
    if not report.recommendation.strip() and dec.get("summary"):
        report.recommendation = (
            f"{dec['summary']} Confidence: {dec.get('confidence', 'Low')} "
            f"(grounded in {dec.get('evidence_count', 0)} validated source(s)).")

    repair_report(report)
    return report
