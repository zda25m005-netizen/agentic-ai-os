"""LoRA fine-tuning configuration and hyperparameter assembly.

Pure Python (no torch/transformers), so it imports and unit-tests with no GPU.
`peft_config_kwargs` / `training_args_kwargs` produce the exact kwargs the
training script feeds to PEFT's LoraConfig and TRL's SFTConfig — keeping the
"what" (hyperparameters) separate from the "how" (the heavy trainer).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LoRAConfig:
    # A small, permissive, chat-tuned base — fits a free Colab/Kaggle GPU.
    base_model: str = "Qwen/Qwen2.5-0.5B-Instruct"
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    target_modules: tuple[str, ...] = ("q_proj", "k_proj", "v_proj", "o_proj")
    learning_rate: float = 2e-4
    epochs: int = 3
    batch_size: int = 2
    grad_accum: int = 4
    max_seq_len: int = 1024
    seed: int = 42
    train_path: str = "data/finetune/train.jsonl"
    val_path: str = "data/finetune/val.jsonl"
    output_dir: str = "artifacts/lora-adapter"


def peft_config_kwargs(cfg: LoRAConfig) -> dict:
    """kwargs for peft.LoraConfig."""
    return {
        "r": cfg.lora_r,
        "lora_alpha": cfg.lora_alpha,
        "lora_dropout": cfg.lora_dropout,
        "target_modules": list(cfg.target_modules),
        "bias": "none",
        "task_type": "CAUSAL_LM",
    }


def training_args_kwargs(cfg: LoRAConfig, dry_run: bool = False) -> dict:
    """kwargs for TRL's SFTConfig / TrainingArguments.

    `dry_run` caps the run at a single optimizer step (one epoch), so the whole
    pipeline can be smoke-tested on a GPU in seconds without real training.
    """
    args = {
        "output_dir": cfg.output_dir,
        "per_device_train_batch_size": cfg.batch_size,
        "gradient_accumulation_steps": cfg.grad_accum,
        "learning_rate": cfg.learning_rate,
        "num_train_epochs": cfg.epochs,
        "logging_steps": 1,
        "save_strategy": "epoch",
        "seed": cfg.seed,
        "report_to": "none",
    }
    if dry_run:
        args["max_steps"] = 1
        args["num_train_epochs"] = 1
        args["save_strategy"] = "no"
    return args
