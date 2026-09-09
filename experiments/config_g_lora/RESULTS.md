# Config G — first real trained-policy results

**Status: COMPLETED.** Controlled pilot experiment (not publication-level evidence).
Run date (UTC): 2026-09-09. Machine-readable: [`results.json`](results.json).

**Research question:** *Can a learned LLM memory policy learn when to STORE, RETRIEVE,
UPDATE, SUMMARIZE, DISCARD, or NOOP, and does this improve memory-conditioned agent
performance?*

## Setup (as actually run)

| | |
|---|---|
| Model | `Qwen/Qwen2.5-0.5B-Instruct` |
| Adapter | **QLoRA 4-bit** (nf4), LoRA r=8, α=16, target_modules=[q_proj, v_proj] |
| Trainer | `LLMGRPOTrainer` (GRPO, group-relative advantage), AdamW lr=1e-4, group_size=8 |
| Data | `TrajectoryMemoryEnv(n=100, seed=0)` → 401 decision steps |
| Schedule | epochs=1, max_states=64 ⇒ **64 optimizer steps**, seed=0 |
| Hardware | Tesla T4 (15.6 GB), CUDA 12.8, torch 2.10, transformers 5.17, peft 0.20, bitsandbytes 0.50 |
| Training time | **20.1 s** (final GRPO loss ≈ 0.0) |

## Headline result — policy action accuracy (same env for all four)

| Policy | policy_action_accuracy |
|---|---|
| A — random reference | 0.1671 |
| B — heuristic (rules) | 0.98 |
| C — base Qwen (no adapter) | **0.3491** |
| D — trained Qwen + QLoRA | **0.98** |

**Δ base → trained = +0.6309.** Δ trained − heuristic = **0.00**.

The real story is the **base → trained jump (0.35 → 0.98)**: 64 GRPO steps of QLoRA taught
the 0.5B model the six-action memory decision from reward alone, reaching the same label-fit
ceiling as the hand-written heuristic. It does **not** beat the heuristic — it *matches* it.

### Per-op accuracy (why the numbers move)

The base model only ever answered `UPDATE`/`NOOP` correctly (STORE, RETRIEVE, SUMMARIZE,
DISCARD all 0.0) — it defaulted to a couple of ops. After training it gets STORE 1.0,
RETRIEVE 1.0, UPDATE 1.0, DISCARD 1.0, NOOP 1.0, SUMMARIZE 0.896 — i.e. it learned the ops
it was previously blind to. The residual gap is SUMMARIZE (0.896), the hardest case (it
depends on the over-budget signal), and it caps both the heuristic and the trained policy at
0.98.

### Label-derived error rates (from the env's optimal actions)

| | random | heuristic | base LLM | trained LLM |
|---|---|---|---|---|
| unnecessary_write_rate | 0.0399 | 0.0 | 0.0 | 0.0 |
| unnecessary_retrieval_rate | 0.1122 | 0.0 | 0.0 | 0.0 |
| stale_memory_leak_rate | 0.3649 | 0.0 | 0.0 | 0.0 |

## Latency — an honest cost to flag

| Policy | mean ms/decision | p95 ms |
|---|---|---|
| heuristic | 0.001 | 0.001 |
| base LLM | 103.8 | 112.4 |
| trained LLM (QLoRA adapter) | **1740.1** | 1900.7 |

The trained (adapter) policy is ~**17× slower per decision** than the base model here — a
real regression, most likely unmerged-LoRA + 4-bit dequant overhead on the T4. Worth noting:
matching the heuristic's accuracy at ~1.7 s/decision (vs ~0 ms for the rules) is not a
production win — it's a **learning-signal** result. Merging the adapter (`merge_and_unload`)
and/or fp16 inference should cut this substantially; not attempted in this pilot.

## Not measured (honestly)

`memory_retrieval_precision/recall/f1`, `temporal_update_accuracy`, `task_success`,
`token_efficiency`, `memory_induced_error_rate` — all `not_measured`. They require a
downstream-task / retrieved-vs-gold harness the trajectory env does not produce. Not
fabricated.

## Limitations

- Synthetic labelled env (n=100, 401 steps); single seed; single epoch; 64 optimizer steps.
- "policy_action_accuracy" is a *policy action* metric on the local decision env — **not**
  retrieval accuracy, task success, or "memory accuracy".
- Trained accuracy equals the heuristic ceiling; the contribution is base→trained learning,
  not surpassing rules.

## Honest one-line summary (CV / README safe)

> A QLoRA-fine-tuned 0.5B LLM memory controller trained with GRPO learned the six-action
> memory decision from reward, improving policy-action accuracy from 0.35 (base) to 0.98
> (matching a hand-written heuristic) on a 401-step controlled pilot — at a current
> inference-latency cost that would need adapter merging before production use.

## Reproduce

See [`KAGGLE_RUN.md`](KAGGLE_RUN.md). Deterministic policy remains the production default;
this experiment does not change the default path or any agent.
