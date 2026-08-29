"""Quantitative engine: extract real numbers and COMPUTE derived metrics.

Numbers only ever come from the research text (each carries its source); the
engine then computes growth rates, ratios and cross-entity percentage
differences with an explicit formula recorded in `derivation`. Nothing is
fabricated: if the evidence has no usable numbers, callers should state
"quantitative comparison was not possible from the available evidence" rather
than inventing figures.
"""
from __future__ import annotations

import re

from app.analysis.artifact import Metric

_PCT = re.compile(r"([A-Za-z][\w \-]{2,30}?)\s+(\d+(?:\.\d+)?)\s?%")
_CUR = re.compile(
    r"([A-Za-z][\w \-]{2,30}?)\s+\$\s?(\d+(?:\.\d+)?)\s?(billion|million|b|m|k)?", re.I)
_UNITED = re.compile(r"([A-Za-z][\w \-]{2,30}?)\s+(\d+(?:\.\d+)?)\s?(ms|gb|mb|tb|tokens|x)\b", re.I)
_MULT = {"billion": 1e9, "million": 1e6, "b": 1e9, "m": 1e6, "k": 1e3}


def _name(raw: str) -> str:
    return " ".join(raw.strip().split()[-3:]).strip().lower()


def extract_metrics(text: str, source_ids: list[str], entity: str = "") -> list[Metric]:
    """Pull reported numbers (with units + a source) out of research text."""
    out: list[Metric] = []
    for m in _PCT.finditer(text or ""):
        out.append(Metric(_name(m.group(1)), float(m.group(2)), "%", entity,
                          list(source_ids), "reported"))
    for m in _CUR.finditer(text or ""):
        val = float(m.group(2)) * _MULT.get((m.group(3) or "").lower(), 1)
        out.append(Metric(_name(m.group(1)), val, "USD", entity, list(source_ids), "reported"))
    for m in _UNITED.finditer(text or ""):
        out.append(Metric(_name(m.group(1)), float(m.group(2)), m.group(3).lower(), entity,
                          list(source_ids), "reported"))
    return out


def growth_rate(previous: float, current: float) -> Metric | None:
    """Percentage change previous -> current, with the formula recorded."""
    if previous == 0:
        return None
    val = (current - previous) / previous * 100
    return Metric("growth rate", round(val, 2), "%",
                  derivation=f"computed: (current-previous)/previous*100 = "
                             f"({current}-{previous})/{previous}*100")


def ratio(a: float, b: float, name: str = "ratio") -> Metric | None:
    if b == 0:
        return None
    return Metric(name, round(a / b, 3), "x", derivation=f"computed: {a}/{b}")


def derived_comparisons(metrics: list[Metric]) -> list[Metric]:
    """For a metric reported for >=2 entities, compute each entity's % vs the min."""
    by_name: dict[str, list[Metric]] = {}
    for m in metrics:
        if m.entity and m.derivation == "reported":
            by_name.setdefault((m.name, m.unit), []).append(m)
    out: list[Metric] = []
    for (name, unit), group in by_name.items():
        entities = {m.entity: m.value for m in group}
        if len(entities) < 2:
            continue
        base = min(entities.values())
        if base == 0:
            continue
        for ent, val in entities.items():
            pct = round((val - base) / base * 100, 1)
            out.append(Metric(f"{name} vs lowest", pct, "%", ent,
                              [s for m in group if m.entity == ent for s in m.source_ids],
                              derivation=f"computed: ({val}-{base})/{base}*100 [{unit}]"))
    return out
