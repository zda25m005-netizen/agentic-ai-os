"""Bar chart: base vs LoRA across the fine-tune metrics (matplotlib, lazy)."""
from __future__ import annotations

from pathlib import Path

_METRICS = ("exact_match", "format_adherence")
_LABELS = ("exact match", "format adherence")


def plot_comparison(results: dict, out_png: str | Path) -> str:
    """Grouped bar chart of base vs fine-tuned metrics. Returns the PNG path."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    base = [results["base"][m] for m in _METRICS]
    ft = [results["finetuned"][m] for m in _METRICS]
    x = range(len(_METRICS))
    width = 0.35

    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(6, 4))
    plt.bar([i - width / 2 for i in x], base, width, label="base")
    plt.bar([i + width / 2 for i in x], ft, width, label="LoRA fine-tuned")
    plt.xticks(list(x), _LABELS)
    plt.ylim(0, 1)
    plt.ylabel("score")
    plt.title("Base vs LoRA — held-out metrics")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()
    return str(out_png)
