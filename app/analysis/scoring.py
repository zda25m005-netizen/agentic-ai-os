"""Evidence-weighted scoring — derive every 0-5 score from the evidence, not a model.

A score a model simply asserts is unfalsifiable. Here each score is built from
the artifact's own claims: for every option x criterion we find the claims that
speak to that criterion, classify each as *supporting* or *contradicting* (word
polarity with negation handling and a few cost/latency phrase rules), weight them
by source reliability, and produce a Laplace-smoothed 0-5 score with the
supporting/contradicting counts and an evidence-confidence label. The number is
then explainable — "3 supporting / 1 contradicting, Medium confidence" — and
cannot be inflated beyond what the evidence supports. Fully deterministic.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.analysis.artifact import AnalysisArtifact, ArtifactClaim, confidence_from_evidence

# criterion -> terms that indicate a claim is *about* that criterion
_CRITERIA: dict[str, set[str]] = {
    "Relevance": {"relevan", "accura", "ground", "faithful", "factual", "quality",
                  "precision", "recall", "correct", "context", "retriev", "fresh",
                  "knowledge", "hallucinat", "up-to-date", "current"},
    "Efficiency": {"efficien", "cost", "cheap", "expensive", "latenc", "fast", "slow",
                   "comput", "resource", "overhead", "train", "inference", "speed",
                   "budget", "memory", "gpu"},
    "Scalability": {"scal", "throughput", "large", "grow", "volume", "corpus", "index",
                    "storage", "footprint", "capacity", "concurrent", "billion"},
    "Maintainability": {"maintain", "updat", "complex", "simple", "operational",
                        "deploy", "monitor", "debug", "reproduc", "governance"},
}
_DEFAULT_CRITERIA = ["Relevance", "Efficiency", "Scalability"]

# Word *stems* (matched with startswith) so "improves"/"scalable"/"expensive" all
# hit. Bare "high"/"low" are deliberately omitted — their polarity depends on the
# noun ("low latency" good, "low accuracy" bad) and is handled by phrase rules.
_POS_STEMS = ("strong", "fast", "efficien", "robust", "accura", "effective",
              "better", "best", "improv", "scalab", "scales", "fresh", "reliab",
              "good", "superior", "advantag", "benefit", "lightweight", "flexib",
              "power", "excellent", "easy", "simple", "precis", "ground", "faithful")
_NEG_STEMS = ("weak", "poor", "slow", "expensiv", "costly", "limit", "fail",
              "degrad", "overhead", "hard", "difficult", "brittle", "stale",
              "unreliab", "bottleneck", "drawback", "disadvantag", "fragile",
              "struggl", "lack", "hallucinat", "outdated", "error")
# phrase rules where a bare word would mislead ("low latency" is good, not bad)
_GOOD_PHRASE = re.compile(
    r"\b(low|lower|reduc\w*|less|minimal|cheap\w*)\s+"
    r"(latenc\w*|cost|compute|overhead|resource\w*|memory|footprint)", re.I)
_BAD_PHRASE = re.compile(
    r"\b(high|higher|more|increas\w*|greater|heavy|significant)\s+"
    r"(latenc\w*|cost|compute|overhead|resource\w*|memory|footprint)", re.I)
_NEGATORS = {"not", "no", "never", "cannot", "without", "hardly", "rarely",
             "isn't", "doesn't", "won't", "don't", "n't"}


@dataclass
class CriterionScore:
    entity: str
    criterion: str
    score: float                 # 0-5, Laplace-smoothed from evidence polarity
    supporting: int
    contradicting: int
    confidence: str              # High | Medium | Low, from source count + quality
    source_ids: list[str] = field(default_factory=list)
    rationale: str = ""


@dataclass
class EvidenceScorecard:
    criteria: list[str]
    entities: list[str]
    cells: list[CriterionScore]

    def cell(self, entity: str, criterion: str) -> CriterionScore | None:
        return next((c for c in self.cells
                     if c.entity == entity and c.criterion == criterion), None)

    def matrix(self) -> dict[str, list[float]]:
        return {e: [(self.cell(e, cr).score if self.cell(e, cr) else 2.5)
                    for cr in self.criteria] for e in self.entities}

    def overall(self) -> dict[str, float]:
        m = self.matrix()
        return {e: round(sum(v) / len(v), 2) if v else 2.5 for e, v in m.items()}


def _polarity(statement: str) -> int:
    """+1 supporting, -1 contradicting, 0 neutral for the entity's standing.

    Polarity is counted per word with *local* negation: a negator in the three
    preceding tokens flips just that word (so "does not scale" is negative while
    "expensive to train" stays negative), avoiding the sentence-global flip that
    mis-scores compound claims.
    """
    s = statement.lower()
    words = re.findall(r"[a-z']+", s)
    pos = neg = 0
    for i, w in enumerate(words):
        is_pos = any(w.startswith(st) for st in _POS_STEMS)
        is_neg = any(w.startswith(st) for st in _NEG_STEMS)
        if not (is_pos or is_neg):
            continue
        if any(n in _NEGATORS for n in words[max(0, i - 3):i]):
            is_pos, is_neg = is_neg, is_pos
        pos += is_pos
        neg += is_neg
    pos += len(_GOOD_PHRASE.findall(s))
    neg += len(_BAD_PHRASE.findall(s))
    if pos > neg:
        return 1
    if neg > pos:
        return -1
    return 0


def _mentions(claim: ArtifactClaim, entity: str, ewords: set[str]) -> bool:
    if claim.entity and claim.entity.lower() == entity.lower():
        return True
    s = claim.statement.lower()
    return bool(ewords) and sum(w in s for w in ewords) / len(ewords) >= 0.5


def _about(statement: str, criterion: str) -> bool:
    s = statement.lower()
    return any(k in s for k in _CRITERIA.get(criterion, set()))


def score_artifact(art: AnalysisArtifact,
                   criteria: list[str] | None = None) -> EvidenceScorecard:
    """Build an evidence-weighted scorecard from the artifact's claims."""
    entities = art.entities or []
    crits = criteria or [c for c in (art.dimensions or []) if c in _CRITERIA] or _DEFAULT_CRITERIA
    ewords = {e: {w for w in re.findall(r"[a-z0-9]+", e.lower()) if len(w) > 2}
              for e in entities}
    rel_of = {s.id: s.reliability for s in art.sources}

    cells: list[CriterionScore] = []
    for e in entities:
        e_claims = [c for c in art.claims if _mentions(c, e, ewords[e])]
        for cr in crits:
            rel = [c for c in e_claims if _about(c.statement, cr)]
            sup_w = con_w = 0.0
            sup = con = 0
            sids: set[str] = set()
            for c in rel:
                pol = _polarity(c.statement)
                w = max((rel_of.get(s, 0.4) for s in c.source_ids), default=0.4)
                w = max(w, 0.3)
                sids.update(c.source_ids)
                if pol > 0:
                    sup += 1
                    sup_w += w
                elif pol < 0:
                    con += 1
                    con_w += w
            # Laplace-smoothed proportion -> 2.5 with no signal, ->5 as support dominates
            score = round(5.0 * (sup_w + 0.5) / (sup_w + con_w + 1.0), 1)
            conf = confidence_from_evidence([rel_of.get(s, 0.4) for s in sids], len(sids))
            if not rel:
                conf = "Low"
                rationale = "No direct evidence for this criterion; neutral prior."
            else:
                rationale = (f"{sup} supporting / {con} contradicting claim(s) "
                             f"across {len(sids)} source(s).")
            cells.append(CriterionScore(
                entity=e, criterion=cr, score=score, supporting=sup, contradicting=con,
                confidence=conf, source_ids=sorted(sids), rationale=rationale))
    return EvidenceScorecard(criteria=crits, entities=entities, cells=cells)
