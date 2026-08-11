"""Training report + merge-script tests (no torch; matplotlib is light)."""
import json

from app.finetune import merge as merge_mod
from app.finetune import report


def _write_state(path):
    path.write_text(json.dumps({
        "log_history": [
            {"step": 1, "loss": 2.5},
            {"step": 2, "loss": 1.8},
            {"step": 3, "loss": 1.2},
            {"step": 3, "eval_loss": 1.3},  # no "loss" -> skipped
        ]
    }))
    return path


def test_parse_loss_curve(tmp_path):
    state = _write_state(tmp_path / "trainer_state.json")
    curve = report.parse_loss_curve(state)
    assert [c["step"] for c in curve] == [1, 2, 3]
    assert curve[0]["loss"] == 2.5 and curve[-1]["loss"] == 1.2


def test_plot_loss_curve_writes_png(tmp_path):
    state = _write_state(tmp_path / "trainer_state.json")
    out = report.plot_loss_curve(state, tmp_path / "loss.png")
    assert (tmp_path / "loss.png").exists()
    assert out.endswith("loss.png")


def test_merge_module_imports_without_torch():
    # Lazy heavy imports: importing the module must not require peft/transformers.
    assert callable(merge_mod.merge_adapter)
    assert callable(merge_mod.main)


def test_report_and_merge_have_defaults():
    assert report.DEFAULT_STATE.endswith("trainer_state.json")
    assert report.DEFAULT_PNG.endswith(".png")
