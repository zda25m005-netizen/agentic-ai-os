"""Merge a trained LoRA adapter into its base model for standalone serving.

A LoRA adapter is a small set of weights that ride on top of the base model.
For serving it's often simplest to fold them in once (`merge_and_unload`) and
save a single self-contained model. Heavy libs are imported lazily, so this
module imports with no torch and CI stays light.
"""
from __future__ import annotations

import argparse

from app.finetune.config import LoRAConfig


def merge_adapter(
    base_model: str | None = None,
    adapter_dir: str | None = None,
    out_dir: str | None = None,
) -> str:
    """Load base + adapter, merge, and save a standalone model. Returns out_dir."""
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    cfg = LoRAConfig()
    base_model = base_model or cfg.base_model
    adapter_dir = adapter_dir or cfg.output_dir
    out_dir = out_dir or f"{cfg.output_dir}-merged"

    tokenizer = AutoTokenizer.from_pretrained(base_model)
    model = AutoModelForCausalLM.from_pretrained(base_model)
    merged = PeftModel.from_pretrained(model, adapter_dir).merge_and_unload()
    merged.save_pretrained(out_dir)
    tokenizer.save_pretrained(out_dir)
    return out_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge a LoRA adapter into its base.")
    parser.add_argument("--base-model", default=None)
    parser.add_argument("--adapter-dir", default=None)
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args()
    out = merge_adapter(args.base_model, args.adapter_dir, args.out_dir)
    print(f"merged model -> {out}")


if __name__ == "__main__":
    main()
