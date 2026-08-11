"""Before/after evaluation for the LoRA fine-tune.

Compares a base model vs the fine-tuned model on the held-out split, scoring
exact-match quality and format adherence (concise, no code fences/LaTeX — the
style the system is graded on). The core takes an injectable `generate_fn`
(instruction -> answer), so it's deterministic and unit-tested with fakes; the
real run plugs in a HuggingFace generator (see `finetune_runner.py`).
"""
from __future__ import annotations

import re
import statistics

from eval.scorers import answer_match

# code fences ``` or LaTeX math \( \[ $$ — penalized as format violations
_FORMAT_VIOLATION = re.compile(r"```|\\\(|\\\[|\$\$")

GenerateFn = "callable"  # instruction: str -> answer: str


def format_adherence(answer: str, max_words: int = 60) -> float:
    """1.0 for a concise, clean answer; 0.5 if too long; 0.0 if empty/violating."""
    a = (answer or "").strip()
    if not a or _FORMAT_VIOLATION.search(a):
        return 0.0
    return 1.0 if len(a.split()) <= max_words else 0.5


def load_heldout() -> list[tuple[str, str]]:
    """The held-out (val) split as (instruction, expected_answer) pairs."""
    from app.finetune.dataset import build_examples
    from app.finetune.format import train_val_split

    _, val = train_val_split(build_examples(), val_frac=0.2, seed=42)
    return [(e.instruction, e.output) for e in val]


def evaluate(items: list[tuple[str, str]], generate_fn) -> dict:
    """Score one model over `items`: mean exact-match and format adherence."""
    exact: list[float] = []
    fmt: list[float] = []
    for instruction, expected in items:
        answer = generate_fn(instruction)
        exact.append(answer_match(expected, answer))
        fmt.append(format_adherence(answer))
    n = len(items)
    return {
        "n": n,
        "exact_match": statistics.mean(exact) if n else 0.0,
        "format_adherence": statistics.mean(fmt) if n else 0.0,
    }


def compare(items: list[tuple[str, str]], base_gen, finetuned_gen) -> dict:
    """Evaluate base vs fine-tuned over the same held-out items."""
    return {"base": evaluate(items, base_gen), "finetuned": evaluate(items, finetuned_gen)}


def format_comparison_table(results: dict) -> str:
    """Render a Markdown before/after table."""
    base, ft = results["base"], results["finetuned"]
    lines = [
        "| Metric | Base | Fine-tuned |",
        "|---|---|---|",
        f"| Exact match | {base['exact_match']:.0%} | {ft['exact_match']:.0%} |",
        f"| Format adherence | {base['format_adherence']:.0%} | "
        f"{ft['format_adherence']:.0%} |",
    ]
    return "\n".join(lines)
