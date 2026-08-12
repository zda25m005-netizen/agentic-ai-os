"""Generate the fine-tuning ablation report (base vs LoRA) from eval results.

`build_report` renders a Markdown report with a metrics table, deltas, and an
auto-written, honest analysis (it says whatever the numbers show — improvement
or not). The CLI reads the results JSON produced by `make lora-eval` and writes
the report + a comparison chart.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.finetune.config import LoRAConfig

DEFAULT_RESULTS = "eval/finetune_results.json"
DEFAULT_REPORT = "docs/FINETUNE_ABLATION.md"
DEFAULT_CHART = "docs/images/finetune-ablation.png"


def _pct(x: float) -> str:
    return f"{x:.0%}"


def _delta(base: float, ft: float) -> str:
    d = (ft - base) * 100
    return f"{'+' if d >= 0 else ''}{d:.0f} pts"


def analysis(base: dict, ft: dict) -> str:
    improved = (
        ft["exact_match"] > base["exact_match"]
        or ft["format_adherence"] > base["format_adherence"]
    )
    if improved:
        return (
            "The LoRA fine-tune improves the graded style/accuracy on the held-out "
            "split. Gains are modest — consistent with the small dataset — so the model "
            "is learning the concise, factual answer *format* the system is graded on, "
            "not new knowledge."
        )
    return (
        "On this run the LoRA fine-tune did not beat the base model on the held-out "
        "metrics. Reported as-is: with so few examples this is a plausible outcome. The "
        "honest next levers are more training data and more epochs, not a bigger claim."
    )


def build_report(results: dict, meta: dict | None = None) -> str:
    base, ft = results["base"], results["finetuned"]
    cfg = LoRAConfig()
    meta = meta or {}
    return "\n".join([
        "# Fine-Tuning Ablation — Base vs LoRA",
        "",
        f"- Base model: `{meta.get('base_model', cfg.base_model)}`",
        f"- LoRA: r={cfg.lora_r}, alpha={cfg.lora_alpha}, "
        f"targets={list(cfg.target_modules)}, lr={cfg.learning_rate}, epochs={cfg.epochs}",
        f"- Held-out examples: {base.get('n', '?')}",
        "",
        "| Metric | Base | LoRA | Δ |",
        "|---|---|---|---|",
        f"| Exact match | {_pct(base['exact_match'])} | {_pct(ft['exact_match'])} | "
        f"{_delta(base['exact_match'], ft['exact_match'])} |",
        f"| Format adherence | {_pct(base['format_adherence'])} | "
        f"{_pct(ft['format_adherence'])} | "
        f"{_delta(base['format_adherence'], ft['format_adherence'])} |",
        "",
        "![base vs LoRA](images/finetune-ablation.png)",
        "",
        "## Analysis",
        "",
        analysis(base, ft),
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the fine-tune ablation report.")
    parser.add_argument("--results", default=DEFAULT_RESULTS)
    parser.add_argument("--out", default=DEFAULT_REPORT)
    args = parser.parse_args()

    path = Path(args.results)
    if not path.exists():
        print(f"No results at {path}. Run `make lora-eval` first (it writes this file).")
        return
    results = json.loads(path.read_text())
    from app.finetune.ablation_chart import plot_comparison

    plot_comparison(results, DEFAULT_CHART)
    Path(args.out).write_text(build_report(results))
    print(f"wrote {args.out} + {DEFAULT_CHART}")


if __name__ == "__main__":
    main()
