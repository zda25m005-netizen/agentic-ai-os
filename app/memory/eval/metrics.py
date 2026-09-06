"""Metric computation for the memory eval harness (all computed, none fabricated)."""

from __future__ import annotations


def _present(text: str, needles: list[str]) -> list[str]:
    low = text.lower()
    return [n for n in needles if n.lower() in low]


def score_scenario(scenario: dict, retrieved_texts: list[str], tokens: int) -> dict:
    blob = " || ".join(retrieved_texts)
    relevant = scenario.get("relevant", [])
    irrelevant = scenario.get("irrelevant", [])
    stale = scenario.get("stale", [])

    rel_found = _present(blob, relevant)
    recall = (len(rel_found) / len(relevant)) if relevant else 1.0
    # precision proxy: of the retrieved items, how many contain a relevant needle
    hit_items = (
        sum(1 for t in retrieved_texts if _present(t, relevant))
        if relevant
        else len(retrieved_texts)
    )
    precision = (
        (hit_items / len(retrieved_texts)) if retrieved_texts else (1.0 if not relevant else 0.0)
    )

    stale_present = _present(blob, stale)
    irr_present = _present(blob, irrelevant)
    return {
        "id": scenario["id"],
        "category": scenario["category"],
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "stale_leak": len(stale_present),  # want 0
        "irrelevant_leak": len(irr_present),  # want 0
        "retrieved": len(retrieved_texts),
        "tokens": tokens,
        "passed": recall >= 0.5 and not stale_present,
    }


def aggregate(rows: list[dict]) -> dict:
    n = len(rows) or 1
    return {
        "scenarios": len(rows),
        "passed": sum(1 for r in rows if r["passed"]),
        "avg_precision": round(sum(r["precision"] for r in rows) / n, 3),
        "avg_recall": round(sum(r["recall"] for r in rows) / n, 3),
        "total_stale_leak": sum(r["stale_leak"] for r in rows),
        "total_irrelevant_leak": sum(r["irrelevant_leak"] for r in rows),
        "avg_retrieved_tokens": round(sum(r["tokens"] for r in rows) / n, 1),
    }
