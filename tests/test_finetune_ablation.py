"""Fine-tune ablation report + chart tests."""
from app.finetune import ablation
from app.finetune.ablation_chart import plot_comparison

_IMPROVED = {
    "base": {"n": 4, "exact_match": 0.5, "format_adherence": 0.5},
    "finetuned": {"n": 4, "exact_match": 1.0, "format_adherence": 0.75},
}
_NO_GAIN = {
    "base": {"n": 4, "exact_match": 0.75, "format_adherence": 1.0},
    "finetuned": {"n": 4, "exact_match": 0.5, "format_adherence": 1.0},
}


def test_build_report_has_table_and_deltas():
    md = ablation.build_report(_IMPROVED)
    assert "# Fine-Tuning Ablation" in md
    assert "| Exact match |" in md
    assert "+50 pts" in md          # 0.5 -> 1.0
    assert "![base vs LoRA]" in md   # chart reference


def test_analysis_is_honest_both_ways():
    up = ablation.build_report(_IMPROVED)
    down = ablation.build_report(_NO_GAIN)
    assert "improves" in up
    assert "did not beat" in down    # no cherry-picking


def test_delta_formatting():
    assert ablation._delta(0.5, 1.0) == "+50 pts"
    assert ablation._delta(0.75, 0.5) == "-25 pts"


def test_plot_comparison_writes_png(tmp_path):
    out = plot_comparison(_IMPROVED, tmp_path / "ablation.png")
    assert (tmp_path / "ablation.png").exists()
    assert out.endswith("ablation.png")
