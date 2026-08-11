"""Training report: extract and plot the loss curve from a TRL/HF run.

After training, HF/TRL writes `trainer_state.json` (with `log_history`) into the
output dir. `parse_loss_curve` reads it — pure and unit-testable; `plot_loss_curve`
renders a PNG with matplotlib (imported lazily so CI/import need no plotting lib).
"""
from __future__ import annotations

import json
from pathlib import Path

DEFAULT_STATE = "artifacts/lora-adapter/trainer_state.json"
DEFAULT_PNG = "docs/images/lora-loss.png"


def parse_loss_curve(trainer_state_path: str | Path) -> list[dict]:
    """Return [{"step", "loss"}, ...] from a trainer_state.json log history."""
    data = json.loads(Path(trainer_state_path).read_text())
    curve: list[dict] = []
    for entry in data.get("log_history", []):
        if "loss" in entry and "step" in entry:
            curve.append({"step": entry["step"], "loss": float(entry["loss"])})
    return curve


def plot_loss_curve(trainer_state_path: str | Path, out_png: str | Path) -> str:
    """Render the training loss curve to a PNG. Returns the output path."""
    curve = parse_loss_curve(trainer_state_path)
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    steps = [c["step"] for c in curve]
    losses = [c["loss"] for c in curve]
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(6, 4))
    plt.plot(steps, losses, marker="o")
    plt.xlabel("step")
    plt.ylabel("training loss")
    plt.title("LoRA fine-tuning loss")
    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()
    return str(out_png)


def main() -> None:
    out = plot_loss_curve(DEFAULT_STATE, DEFAULT_PNG)
    print(f"loss curve -> {out}")


if __name__ == "__main__":
    main()
