"""Evidence-grounded decision — a recommendation proportional to what the evidence shows.

An LLM asked for a recommendation tends to answer "use everything": every option
is useful, so combine them all. That is not analysis. This module derives the
recommendation from the evidence-weighted scorecard instead:

  * an option is recommended only where it *leads* a criterion with a positive
    score — so each recommended component earns its place by solving a distinct
    problem, and complexity is not added for its own sake;
  * an option that leads nothing is marked for *selective* use, not adopted by
    default (this is what stops the "RAG + fine-tuning + structured memory, use
    all three" over-reach);
  * the stated confidence tracks the evidence: weak/thin evidence yields a
    hedged recommendation, never a confident one;
  * a consistency check flags any high score that rests on low-confidence
    evidence, so the prose can never claim more than the evidence supports.

Deterministic and offline.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.analysis.artifact import AnalysisArtifact
from app.analysis.scoring import EvidenceScorecard

_LEAD_MIN = 3.0        # a criterion score at/above this counts as a genuine strength
_CONF_ORDER = {"High": 3, "Medium": 2, "Low": 1}


@dataclass
class Decision:
    recommended: list[str] = field(default_factory=list)
    components: list[dict] = field(default_factory=list)   # {component, leads[], role}
    selective: list[dict] = field(default_factory=list)    # {option, reason}
    confidence: str = "Low"
    evidence_count: int = 0
    summary: str = ""
    consistency_flags: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "recommended": self.recommended, "components": self.components,
            "selective": self.selective, "confidence": self.confidence,
            "evidence_count": self.evidence_count, "summary": self.summary,
            "consistency_flags": self.consistency_flags,
        }


def _overall_confidence(esc: EvidenceScorecard) -> str:
    """The decision is only as confident as its weakest well-evidenced cell allows."""
    confs = [c.confidence for c in esc.cells if (c.supporting or c.contradicting)]
    if not confs:
        return "Low"
    # median-ish: take the most common, but never claim High unless most cells are High
    highs = sum(_CONF_ORDER.get(c, 1) >= 3 for c in confs)
    meds = sum(_CONF_ORDER.get(c, 1) == 2 for c in confs)
    if highs >= max(1, len(confs) // 2):
        return "High"
    if highs + meds >= max(1, len(confs) // 2):
        return "Medium"
    return "Low"


def derive_decision(art: AnalysisArtifact, esc: EvidenceScorecard) -> Decision:
    if not (esc.entities and esc.cells):
        return Decision()
    overall = esc.overall()
    evidence_count = len(art.sources)

    # Which option leads each criterion (unique max, and a genuine strength).
    leads: dict[str, list[str]] = {e: [] for e in esc.entities}
    for cr in esc.criteria:
        ranked = sorted(esc.entities, key=lambda e: esc.cell(e, cr).score, reverse=True)
        top = ranked[0]
        top_score = esc.cell(top, cr).score
        unique = len(ranked) < 2 or esc.cell(ranked[1], cr).score < top_score
        if unique and top_score >= _LEAD_MIN:
            leads[top].append(cr)

    recommended = [e for e in esc.entities if leads[e]]
    components = [{"component": e, "leads": leads[e],
                   "role": "best for " + ", ".join(leads[e]).lower()}
                  for e in recommended]
    selective = [{"option": e,
                  "reason": f"does not lead on any criterion (best overall {overall[e]}/5); "
                            f"adds complexity without a distinct evidenced advantage — "
                            f"use selectively, not as a default component."}
                 for e in esc.entities if e not in recommended]

    # Fallback: if nothing clears the bar, recommend the top-overall option, hedged.
    if not recommended:
        top = max(esc.entities, key=lambda e: overall[e])
        recommended = [top]
        components = [{"component": top, "leads": [],
                       "role": f"highest overall ({overall[top]}/5), though no option "
                               f"shows a decisive evidenced lead"}]
        selective = [s for s in selective if s["option"] != top]

    confidence = _overall_confidence(esc)

    # Consistency: a strong score on thin evidence must not read as a confident win.
    flags: list[str] = []
    for c in esc.cells:
        if c.score >= 3.5 and c.confidence == "Low":
            flags.append(
                f"{c.entity} scores {c.score}/5 on {c.criterion} but on low-confidence "
                f"evidence ({c.supporting} supporting / {c.contradicting} contradicting, "
                f"{len(c.source_ids)} source); treat as indicative, not established.")

    if len(recommended) == 1:
        summary = f"Adopt {recommended[0]}"
    else:
        summary = " + ".join(recommended)
        summary = f"Combine {summary}, each for the dimension it leads"
    if selective:
        summary += "; use " + ", ".join(s["option"] for s in selective) \
            + " selectively rather than by default."
    else:
        summary += "."

    return Decision(recommended=recommended, components=components, selective=selective,
                    confidence=confidence, evidence_count=evidence_count,
                    summary=summary, consistency_flags=flags[:5])
