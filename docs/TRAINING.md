# LoRA Fine-Tuning — Run Guide

How to actually run the fine-tune (the code is in `app/finetune/`, the notebook
in `notebooks/lora_finetune_colab.ipynb`). Training needs a GPU; everything else
runs and tests locally with no torch.

## 1. Build the dataset (local, no GPU)
```bash
make sft-data                     # writes data/finetune/train.jsonl + val.jsonl
```

## 2. Train (free GPU — Colab or Kaggle)
Open the notebook, pick a **GPU runtime**, and run the cells. Or from a GPU shell:
```bash
pip install -e ".[finetune]"
python -m app.finetune.train --dry-run    # 1 optimizer step, verifies the pipeline
python -m app.finetune.train              # full run -> artifacts/lora-adapter/
```
Base model: `Qwen/Qwen2.5-0.5B-Instruct` (small, chat-tuned, fits a free GPU).
Expect roughly 10–20 minutes on a T4 for the current small dataset.

**Outputs** (in `artifacts/lora-adapter/`, gitignored):
- the LoRA adapter weights + tokenizer
- `trainer_state.json` (loss history)
- `run_summary.json` (base model, LoRA rank/alpha, example count)

## 3. Capture the loss curve
```bash
make lora-plot        # reads trainer_state.json -> docs/images/lora-loss.png
```

## 4. Merge for serving (optional)
```bash
make lora-merge       # base + adapter -> artifacts/lora-adapter-merged/
```

## 5. Before/after evaluation
Compare base vs fine-tuned on the held-out set (Day 21). The harness reports
whatever the numbers show — expect modest, style/format gains on this small
dataset, not new knowledge (see the [dataset card](../app/finetune/DATASET_CARD.md)).

## Run summary (fill in after the real run)
- Base model: `Qwen/Qwen2.5-0.5B-Instruct`
- LoRA: r=16, alpha=32, target=q/k/v/o_proj, lr=2e-4, 3 epochs
- Train / val examples: _(from run_summary.json)_
- Final training loss: _(from the loss curve)_
- Before/after eval: _(Day 21)_

Weights are not committed (gitignored); publish to the HF Hub or attach to a
GitHub Release if you want them downloadable.
