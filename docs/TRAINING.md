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

## 4. Merge + serve
```bash
make lora-merge       # base + adapter -> artifacts/lora-adapter-merged/
```
Then point the app at it (in `.env`):
```bash
USE_FINETUNED=true
FINETUNED_MODEL_DIR=artifacts/lora-adapter-merged
```
`/chat` will route through the fine-tuned model when it's present, and **fall
back to the API model** if it's missing or local inference fails — never a hard
error. The response's `model` field and `GET /config`'s `active_model` show
which model actually answered (`lora:...` vs the API model).

## 5. Before/after evaluation
```bash
make lora-eval        # base vs artifacts/lora-adapter-merged on the held-out split
```
It scores two metrics on the held-out (val) split and prints a table:
- **Exact match** — is the expected answer contained in the output (normalized)?
- **Format adherence** — concise and clean (no code fences / LaTeX), the style
  the system is graded on.

The harness reports whatever the numbers show — on this small dataset expect
modest **style/format** gains, not new knowledge (see the
[dataset card](../app/finetune/DATASET_CARD.md)). Fill the table below after the run:

| Metric | Base | Fine-tuned |
|---|---|---|
| Exact match | _tbd_ | _tbd_ |
| Format adherence | _tbd_ | _tbd_ |

## Run summary (fill in after the real run)
- Base model: `Qwen/Qwen2.5-0.5B-Instruct`
- LoRA: r=16, alpha=32, target=q/k/v/o_proj, lr=2e-4, 3 epochs
- Train / val examples: _(from run_summary.json)_
- Final training loss: _(from the loss curve)_
- Before/after eval: _(Day 21)_

Weights are not committed (gitignored); publish to the HF Hub or attach to a
GitHub Release if you want them downloadable.
