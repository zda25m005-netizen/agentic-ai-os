# SFT Dataset Card — Agentic AI OS

## Summary
A small supervised fine-tuning (SFT) dataset of instruction/response pairs used
to LoRA-fine-tune a base chat model toward this project's target behavior:
concise, factual answers over the enterprise corpus, and short relational
answers from the knowledge graph.

## Sources
- **`eval/datasets/qa.json`** — hand-built RAG questions with a gold
  `expected_answer` (source: `qa`).
- **`eval/datasets/graph_qa.json`** — relational questions whose
  `expected_facts` are joined into a short answer (source: `graph_qa`).

Both are the same labeled sets the evaluation harness scores against, so the
fine-tune targets exactly what we measure (no train/test leakage into the
held-out eval corpus, which is a *separate* ablation set).

## Format
Chat-format JSONL, one row per line:
```json
{"messages": [
  {"role": "system", "content": "You are a precise enterprise assistant..."},
  {"role": "user", "content": "<question>"},
  {"role": "assistant", "content": "<answer>"}
]}
```
Compatible with TRL `SFTTrainer` and most chat fine-tuning pipelines.

## Size & split
Built by `python -m app.finetune.build_dataset` (or `make sft-data`).
Deterministic 80/20 train/val split (seed 42). Exact counts print at build time;
the set is intentionally small (tens of examples) — this is a **demonstration of
the fine-tuning pipeline and a before/after ablation**, not a large-scale train.

## Limitations & honesty
- Small dataset: expect modest, format-and-style gains, not new knowledge.
- Answers are short/extractive; the fine-tune mainly improves adherence to the
  concise, factual style the system is graded on.
- The before/after comparison (Day 21) reports whatever the metrics show.

## License
Derived from this repository's own hand-authored eval data — MIT, same as the repo.
