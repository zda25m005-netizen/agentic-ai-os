"""Serialize DPO preference pairs to TRL-compatible JSONL.

TRL's DPOTrainer expects rows of {"prompt", "chosen", "rejected"} — one JSON
object per line. `export_jsonl` writes exactly that so the file drops straight
into a training run (Week 4).
"""
from __future__ import annotations

import json
from pathlib import Path

from app.feedback.dpo import PreferencePair


def to_trl(pair: PreferencePair) -> dict:
    """One TRL DPO row."""
    return {"prompt": pair.prompt, "chosen": pair.chosen, "rejected": pair.rejected}


def export_jsonl(pairs: list[PreferencePair], path: str | Path) -> int:
    """Write pairs as JSONL (one row per line). Returns rows written."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for pair in pairs:
            f.write(json.dumps(to_trl(pair), ensure_ascii=False) + "\n")
    return len(pairs)
