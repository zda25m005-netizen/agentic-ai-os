"""LoRA fine-tuning with PEFT + TRL SFTTrainer.

The heavy ML libraries (torch, transformers, peft, trl, datasets) are imported
*lazily* inside functions, so this module imports with no GPU and CI stays
light. Install them via the optional extra:  pip install -e ".[finetune]"

Run on a GPU (Colab/Kaggle):
    python -m app.finetune.build_dataset      # write data/finetune/*.jsonl
    python -m app.finetune.train              # full LoRA run
    python -m app.finetune.train --dry-run    # 1 optimizer step (smoke test)
"""
from __future__ import annotations

import argparse

from app.finetune.config import LoRAConfig, peft_config_kwargs, training_args_kwargs

_MISSING = (
    'Fine-tuning dependencies are not installed. Run: pip install -e ".[finetune]"'
)


def _require_libs() -> None:
    try:
        import datasets  # noqa: F401
        import peft  # noqa: F401
        import torch  # noqa: F401
        import transformers  # noqa: F401
        import trl  # noqa: F401
    except ImportError as exc:  # pragma: no cover - only hit without the extra
        raise SystemExit(_MISSING) from exc


def load_chat_dataset(path: str):
    """Load a chat-format JSONL file as a HF dataset (lazy import)."""
    from datasets import load_dataset

    return load_dataset("json", data_files=path, split="train")


def train(cfg: LoRAConfig | None = None, dry_run: bool = False) -> str:
    """Fine-tune with LoRA and save the adapter. Returns the output dir."""
    _require_libs()
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import SFTConfig, SFTTrainer

    cfg = cfg or LoRAConfig()

    tokenizer = AutoTokenizer.from_pretrained(cfg.base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(cfg.base_model)

    peft_config = LoraConfig(**peft_config_kwargs(cfg))
    train_ds = load_chat_dataset(cfg.train_path)
    sft_config = SFTConfig(
        **training_args_kwargs(cfg, dry_run=dry_run),
        max_seq_length=cfg.max_seq_len,
    )
    trainer = SFTTrainer(
        model=model,
        args=sft_config,
        train_dataset=train_ds,
        peft_config=peft_config,
        processing_class=tokenizer,
    )
    trainer.train()
    trainer.save_model(cfg.output_dir)
    tokenizer.save_pretrained(cfg.output_dir)
    return cfg.output_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="LoRA fine-tune the base model.")
    parser.add_argument(
        "--dry-run", action="store_true", help="one optimizer step (smoke test)"
    )
    args = parser.parse_args()
    out = train(dry_run=args.dry_run)
    print(f"saved LoRA adapter -> {out}")


if __name__ == "__main__":
    main()
