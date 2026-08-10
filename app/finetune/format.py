"""Format SFT examples to a chat template and split train/val.

`to_chat` emits the standard messages shape (system/user/assistant) that
TRL's SFTTrainer and most chat fine-tuning pipelines accept. The split is
seeded, so the same data always produces the same train/val partition.
"""
from __future__ import annotations

import random

from app.finetune.dataset import SYSTEM_PROMPT, SFTExample


def to_chat(example: SFTExample) -> dict:
    """One chat-format training row."""
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": example.instruction},
            {"role": "assistant", "content": example.output},
        ]
    }


def train_val_split(
    examples: list[SFTExample], val_frac: float = 0.2, seed: int = 42
) -> tuple[list[SFTExample], list[SFTExample]]:
    """Deterministically shuffle and split into (train, val)."""
    items = list(examples)
    random.Random(seed).shuffle(items)
    if not items:
        return [], []
    n_val = max(1, round(len(items) * val_frac))
    n_val = min(n_val, len(items) - 1) if len(items) > 1 else 0
    return items[n_val:], items[:n_val]
