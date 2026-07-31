"""Pure text helpers for graph extraction — no LLM, no I/O.

Kept separate from `extract.py` so the deterministic bits (name cleanup, dedup,
defensive JSON parsing) are trivially unit-tested and reusable by ingest.
"""
from __future__ import annotations

import json
import re

from app.graph.schema import Entity

_JSON_ARRAY_RE = re.compile(r"\[.*\]", re.DOTALL)


def normalize_name(name: str) -> str:
    """Collapse internal whitespace and trim — a stable display form."""
    return " ".join((name or "").split()).strip()


def parse_json_array(raw: str) -> list[dict]:
    """Return a list of dicts from the first JSON array in `raw`, else []."""
    match = _JSON_ARRAY_RE.search(raw or "")
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    return [d for d in data if isinstance(d, dict)] if isinstance(data, list) else []


def dedup_entities(entities: list[Entity]) -> list[Entity]:
    """Merge entities that share a case-insensitive name.

    Keeps first occurrence but upgrades a generic ("Entity") type to a more
    specific one if a later duplicate provides it.
    """
    seen: dict[str, Entity] = {}
    for e in entities:
        key = e.name.casefold()
        if key not in seen:
            seen[key] = e
        elif seen[key].type in ("", "Entity") and e.type not in ("", "Entity"):
            seen[key] = e
    return list(seen.values())
