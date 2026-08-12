# Fine-Tuning Ablation — Base vs LoRA

> This report is **auto-generated** from a real run. Until the GPU training +
> eval has been done, the numbers below are placeholders. Regenerate with:
> ```bash
> make lora-eval      # writes eval/finetune_results.json
> make lora-report    # writes this file + docs/images/finetune-ablation.png
> ```

- Base model: `Qwen/Qwen2.5-0.5B-Instruct`
- LoRA: r=16, alpha=32, targets=[q_proj, k_proj, v_proj, o_proj], lr=2e-4, epochs=3
- Held-out examples: _tbd_

| Metric | Base | LoRA | Δ |
|---|---|---|---|
| Exact match | _tbd_ | _tbd_ | _tbd_ |
| Format adherence | _tbd_ | _tbd_ | _tbd_ |

![base vs LoRA](images/finetune-ablation.png)

## Analysis

_Auto-written from the deltas by `app/finetune/ablation.py`._ The generator states
whatever the numbers show — improvement **or not** — with no cherry-picking. On a
dataset this small, the expected outcome is a **modest style/format gain**
(concise, factual answers), not new knowledge. If the fine-tune fails to beat the
base on a given run, the report says so plainly and points at the real levers:
more data and more epochs.

## Method (reproducible)

1. `make sft-data` — assemble instruction/response pairs (chat format, seeded split).
2. Train LoRA on a free GPU (`notebooks/lora_finetune_colab.ipynb`).
3. `make lora-merge` — fold the adapter into the base for serving.
4. `make lora-eval` — base vs fine-tuned on the held-out split
   (exact match + format adherence).
5. `make lora-report` — this report + chart.

See [TRAINING.md](TRAINING.md) for the full run guide.
