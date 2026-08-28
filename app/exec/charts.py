"""Vector charts (matplotlib) built strictly from the qualitative Scorecard.

Every chart is derived only from the analyst 0-5 scores already in the report —
no numbers are invented, and if there is no scorecard (or matplotlib is missing)
the functions return None so the renderer simply omits the figure. Output is a
vector PDF suitable for `\\includegraphics` under pdflatex. All figures are
explicitly captioned as qualitative assessments by the renderer.
"""
from __future__ import annotations

import io

from app.exec.report import Scorecard

# Restrained, consistent palette (navy / steel / amber / green / plum).
_PALETTE = ["#14213d", "#2d4d7a", "#c4840a", "#178c56", "#6a4c93", "#8a5a2b"]


def _plt():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        return plt
    except Exception:
        return None


def _scores(sc: Scorecard, entity: str) -> list[float]:
    row = sc.scores.get(entity, [])
    return [float(row[i]) if i < len(row) else 0.0 for i in range(len(sc.dimensions))]


def bar_chart_pdf(sc: Scorecard | None) -> bytes | None:
    """Grouped bar chart: dimensions on x, one bar group per entity."""
    plt = _plt()
    if plt is None or sc is None or not sc.dimensions or not sc.entities:
        return None
    n_dim, n_ent = len(sc.dimensions), len(sc.entities)
    width = 0.8 / max(n_ent, 1)
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    x = list(range(n_dim))
    for j, ent in enumerate(sc.entities):
        offs = [xi + (j - (n_ent - 1) / 2) * width for xi in x]
        ax.bar(offs, _scores(sc, ent), width=width, label=ent,
               color=_PALETTE[j % len(_PALETTE)])
    ax.set_xticks(x)
    ax.set_xticklabels(sc.dimensions, fontsize=9)
    ax.set_ylim(0, 5)
    ax.set_ylabel("Qualitative score (0-5)", fontsize=9)
    ax.set_axisbelow(True)
    ax.grid(axis="y", color="#dfe3ea", linewidth=0.7)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.legend(fontsize=8, frameon=False, ncol=min(n_ent, 3), loc="upper center",
              bbox_to_anchor=(0.5, 1.14))
    return _to_pdf(plt, fig)


def radar_chart_pdf(sc: Scorecard | None) -> bytes | None:
    """Radar/spider chart, one polygon per entity. Needs >= 3 dimensions."""
    plt = _plt()
    if plt is None or sc is None or len(sc.dimensions) < 3 or not sc.entities:
        return None
    import math
    n = len(sc.dimensions)
    angles = [i / n * 2 * math.pi for i in range(n)]
    angles += angles[:1]  # close the loop
    fig, ax = plt.subplots(figsize=(4.8, 4.8), subplot_kw={"polar": True})
    for j, ent in enumerate(sc.entities):
        vals = _scores(sc, ent)
        vals += vals[:1]
        col = _PALETTE[j % len(_PALETTE)]
        ax.plot(angles, vals, color=col, linewidth=1.8, label=ent)
        ax.fill(angles, vals, color=col, alpha=0.08)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(sc.dimensions, fontsize=8)
    ax.set_ylim(0, 5)
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_yticklabels(["1", "2", "3", "4", "5"], fontsize=7, color="#6e7480")
    ax.legend(fontsize=8, frameon=False, loc="upper right", bbox_to_anchor=(1.25, 1.10))
    return _to_pdf(plt, fig)


def _pick_axes(dims: list[str]) -> tuple[int, int] | None:
    """Choose two dimensions for a trade-off plot (cost-like vs quality-like)."""
    if len(dims) < 2:
        return None
    low = [d.lower() for d in dims]

    def find(keys):
        for i, d in enumerate(low):
            if any(k in d for k in keys):
                return i
        return None
    x = find(("cost", "complexity", "maintain", "latency"))
    y = find(("accuracy", "quality", "fresh", "reliab", "personal"))
    if x is None or y is None or x == y:
        x, y = 0, 1
    return x, y


def tradeoff_chart_pdf(sc: Scorecard | None) -> bytes | None:
    """Scatter of two evaluation dimensions (e.g. cost vs accuracy), one point/entity."""
    plt = _plt()
    if plt is None or sc is None or not sc.entities:
        return None
    axes = _pick_axes(sc.dimensions)
    if axes is None:
        return None
    xi, yi = axes
    fig, ax = plt.subplots(figsize=(5.6, 4.2))
    for j, e in enumerate(sc.entities):
        s = _scores(sc, e)
        col = _PALETTE[j % len(_PALETTE)]
        ax.scatter([s[xi]], [s[yi]], s=140, color=col, zorder=3, label=e)
        ax.annotate(e, (s[xi], s[yi]), textcoords="offset points", xytext=(8, 6),
                    fontsize=8, color=col)
    ax.set_xlabel(f"{sc.dimensions[xi]} (0-5)", fontsize=9)
    ax.set_ylabel(f"{sc.dimensions[yi]} (0-5)", fontsize=9)
    ax.set_xlim(-0.3, 5.3)
    ax.set_ylim(-0.3, 5.3)
    ax.set_axisbelow(True)
    ax.grid(color="#dfe3ea", linewidth=0.7)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    return _to_pdf(plt, fig)


def _to_pdf(plt, fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="pdf", bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def scorecard_assets(sc: Scorecard | None) -> dict[str, bytes]:
    """All chart assets for a scorecard, keyed by the filename the template uses."""
    assets: dict[str, bytes] = {}
    bar = bar_chart_pdf(sc)
    if bar:
        assets["chart_bar.pdf"] = bar
    radar = radar_chart_pdf(sc)
    if radar:
        assets["chart_radar.pdf"] = radar
    tradeoff = tradeoff_chart_pdf(sc)
    if tradeoff:
        assets["chart_tradeoff.pdf"] = tradeoff
    return assets
