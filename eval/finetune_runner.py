"""Real before/after runner: generate with HuggingFace models and compare.

Heavy libs (torch/transformers) are imported lazily, so this module imports with
no GPU. `make lora-eval` runs base vs the merged fine-tuned model over the
held-out split and prints the comparison table.
"""
from __future__ import annotations

import argparse

from app.finetune.config import LoRAConfig
from app.finetune.dataset import SYSTEM_PROMPT
from eval.finetune_eval import compare, format_comparison_table, load_heldout


def hf_generate_fn(model_dir: str, max_new_tokens: int = 64):
    """Return a generate_fn(instruction)->answer backed by a HF chat model."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForCausalLM.from_pretrained(model_dir)
    model.eval()

    def generate(instruction: str) -> str:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": instruction},
        ]
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = tokenizer(prompt, return_tensors="pt")
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
        text = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        return text.strip()

    return generate


def main() -> None:
    parser = argparse.ArgumentParser(description="Before/after LoRA evaluation.")
    parser.add_argument("--base-model", default=LoRAConfig().base_model)
    parser.add_argument("--finetuned-dir", default=f"{LoRAConfig().output_dir}-merged")
    args = parser.parse_args()

    items = load_heldout()
    base_gen = hf_generate_fn(args.base_model)
    ft_gen = hf_generate_fn(args.finetuned_dir)
    results = compare(items, base_gen, ft_gen)
    print(format_comparison_table(results))


if __name__ == "__main__":
    main()
