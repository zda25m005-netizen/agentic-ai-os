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

import json
import re
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from app.analysis.artifact import AnalysisArtifact
from app.analysis.pipeline import build_analysis_artifact
from app.analysis.to_report import artifact_to_report
from app.analysis.validate import repair_report
from app.exec.report import Report
from app.exec.report_builder import _default_summary, _synthesize_into
from app.missions.models import Mission, Task

ChatFn = Callable[[list[dict]], Awaitable[str]]
_OBJ = re.compile(r"\{.*\}", re.DOTALL)

_SYS_SYNTH = (
    "You are a senior research analyst. You are given a STRUCTURED analysis as JSON "
    "(sources, verified claims, findings). Organise and EXPLAIN this evidence in a "
    "professional report. Return ONLY a JSON object with these keys: "
    "bottom_line: ONE decisive 1-2 sentence analyst conclusion (a judgement, not a "
    "definition of a technology). "
    "executive_summary, problem_definition, comparative_analysis (each a string). "
    "recommendation: a decisive paragraph AND, for design/architecture questions, a "
    "multi-line component ARCHITECTURE DIAGRAM inside a ```code fence``` using ONLY "
    "plain ASCII (-> | + _ and words; NO unicode box-drawing), showing each memory/"
    "component layer and the data flow, plus a short explanation of what goes into "
    "each layer and why NOT put everything in one mechanism. "
    "reasoning_chains: a list of {claim, evidence, reasoning, trade_off, decision} — "
    "for each major design decision, give the Claim, the Evidence it rests on, the "
    "technical Reasoning, the Trade-off, and the Decision. This justifies the "
    "scorecard; do not assign a score without a supporting reasoning chain. "
    "reasoning: a list of {finding_id, interpretation, implication}. "
    "evaluation_framework: a list of {criterion, definition}. "
    "approaches: a list of {name, how_it_works, advantages[], disadvantages[], "
    "failure_modes[], mitigations[]}, one per entity, using the real entity names. "
    "failure_analysis: a risk register of {failure, mechanism, probability, impact, "
    "detection, mitigation, residual_risk}. "
    "key_insights: 3-6 high-value {insight, confidence} items, each a non-obvious "
    "evidence-backed takeaway. "
    "evidence_summary: a list of {finding, strength (Strong/Moderate/Weak), "
    "confidence (High/Medium/Low)}. "
    "trade_offs: a list of {entity, pros (list), cons (list)}, one per option. "
    "scoring_rationale: for each scorecard criterion, {criterion, reason, confidence} "
    "explaining HOW the 0-5 scores were derived from the evidence. "
    "decision_change: 2-4 strings answering 'what evidence would change this "
    "recommendation?'. "
    "For every major claim also give counter_evidence in the reasoning chain (a "
    "'counter' field) so the analysis is not one-sided; if none exists, say so. "
    "scorecard: {dimensions[], entities[], scores{entity:[0-5 per dimension]}} — the "
    "0-5 scores are a QUALITATIVE analyst assessment of the evidence, never a "
    "measured statistic. decision_rationale: a list of {requirement, decision, reason}. "
    "STRICT RULES: base everything on the provided findings/claims; NEVER add facts, "
    "numbers, statistics, sources, or claims not in the input; do not state specific "
    "percentages/market figures as fact; do not contradict the verification status."
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


async def synthesize_over_artifact(art: AnalysisArtifact, chat_fn: ChatFn) -> dict:
    raw = await chat_fn([
        {"role": "system", "content": _SYS_SYNTH},
        {"role": "user", "content": json.dumps(art.to_llm_context())[:8000]},
    ])
    return _parse(raw)


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
    report.scoring_rationale = _dicts(
        "scoring_rationale", ("criterion", "reason", "confidence"), "criterion")
    dc = synth.get("decision_change")
    if isinstance(dc, list):
        report.decision_change = [str(x) for x in dc if str(x).strip()][:5]

    repair_report(report)
    return report
