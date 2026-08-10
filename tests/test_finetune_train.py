"""LoRA config / hyperparameter assembly tests — no torch, CI-safe.

We verify the exact kwargs handed to PEFT and TRL, and that `--dry-run` caps the
run at one step, without importing any heavy ML library. `app.finetune.train`
imports lazily, so importing the module here must not require torch either.
"""
import json

from app.finetune import train as train_mod
from app.finetune.config import (
    LoRAConfig,
    peft_config_kwargs,
    training_args_kwargs,
)


def test_config_has_sane_defaults():
    cfg = LoRAConfig()
    assert cfg.base_model
    assert cfg.lora_r > 0 and cfg.lora_alpha >= cfg.lora_r
    assert len(cfg.target_modules) >= 1


def test_peft_config_kwargs():
    kw = peft_config_kwargs(LoRAConfig(lora_r=8, lora_alpha=16))
    assert kw["r"] == 8
    assert kw["lora_alpha"] == 16
    assert kw["task_type"] == "CAUSAL_LM"
    assert "q_proj" in kw["target_modules"]


def test_training_args_full_run():
    kw = training_args_kwargs(LoRAConfig(epochs=3, learning_rate=2e-4))
    assert kw["num_train_epochs"] == 3
    assert kw["learning_rate"] == 2e-4
    assert "max_steps" not in kw  # full run is epoch-based


def test_training_args_dry_run_is_one_step():
    kw = training_args_kwargs(LoRAConfig(), dry_run=True)
    assert kw["max_steps"] == 1
    assert kw["num_train_epochs"] == 1
    assert kw["save_strategy"] == "no"


def test_train_module_imports_without_ml_libs():
    # The module imports (lazy heavy deps); train() exists and requires libs.
    assert hasattr(train_mod, "train")
    assert callable(train_mod.train)


def test_notebook_is_valid_and_targets_gpu():
    from pathlib import Path

    nb = json.loads(
        (Path(__file__).resolve().parents[1]
         / "notebooks/lora_finetune_colab.ipynb").read_text()
    )
    assert nb["metadata"].get("accelerator") == "GPU"
    code = "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
    assert "app.finetune.build_dataset" in code
    assert "app.finetune.train" in code
