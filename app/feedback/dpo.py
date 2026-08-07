"""Assemble DPO preference pairs from user feedback.

Two sources of (chosen, rejected) preference over a prompt:
  1. a 👎 with a suggested `better_answer` → (chosen=better, rejected=shown)
  2. a query that got both a 👍 and a 👎 answer → (chosen=👍, rejected=👎)

This is **DPO/SFT preference data, not RLHF** — no reward model, no online RL.
Pairs are deduped and invalid ones (empty or chosen==rejected) dropped.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass


@dataclass
class PreferencePair:
    prompt: str
    chosen: str
    rejected: str


def _valid(p: PreferencePair) -> bool:
    return bool(p.prompt and p.chosen and p.rejected) and p.chosen != p.rejected


def build_preference_pairs(feedback_items) -> list[PreferencePair]:
    """Build deduped, valid preference pairs from feedback rows."""
    raw: list[PreferencePair] = []
    up_by_query: dict[str, str] = {}
    down_by_query: dict[str, str] = {}

    for fb in feedback_items:
        query = getattr(fb, "query", "")
        answer = getattr(fb, "answer", "")
        rating = getattr(fb, "rating", "")
        better = getattr(fb, "better_answer", None)
        if rating == "down" and better:
            raw.append(PreferencePair(prompt=query, chosen=better, rejected=answer))
        if rating == "up":
            up_by_query.setdefault(query, answer)
        elif rating == "down":
            down_by_query.setdefault(query, answer)

    for query, up_ans in up_by_query.items():
        if query in down_by_query:
            raw.append(
                PreferencePair(prompt=query, chosen=up_ans, rejected=down_by_query[query])
            )

    seen: set[tuple[str, str, str]] = set()
    out: list[PreferencePair] = []
    for p in raw:
        if not _valid(p):
            continue
        key = (p.prompt, p.chosen, p.rejected)
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def validate_pairs(pairs: list[PreferencePair]) -> list[str]:
    """Return a list of human-readable issues (empty means clean)."""
    issues: list[str] = []
    for i, p in enumerate(pairs):
        if not p.prompt:
            issues.append(f"pair {i}: empty prompt")
        if not p.chosen or not p.rejected:
            issues.append(f"pair {i}: empty chosen/rejected")
        if p.chosen == p.rejected:
            issues.append(f"pair {i}: chosen == rejected")
    return issues


def dataset_stats(pairs: list[PreferencePair]) -> dict:
    """Summary stats for a DPO dataset."""
    if not pairs:
        return {"n_pairs": 0, "n_prompts": 0, "avg_chosen_len": 0, "avg_rejected_len": 0}
    return {
        "n_pairs": len(pairs),
        "n_prompts": len({p.prompt for p in pairs}),
        "avg_chosen_len": round(statistics.mean(len(p.chosen) for p in pairs), 1),
        "avg_rejected_len": round(statistics.mean(len(p.rejected) for p in pairs), 1),
    }
