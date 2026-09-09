# Running the Config-G experiment on Kaggle GPU

This is the **first real** LoRA/QLoRA GRPO training run of the Config-G LLM memory policy.
It is a **controlled pilot experiment**, not publication-level evidence.

**Research question:** *Can a learned LLM memory policy learn when to STORE, RETRIEVE, UPDATE,
SUMMARIZE, DISCARD, or NOOP, and does this improve memory-conditioned agent performance?*

Notebook: [`kaggle_config_g_lora.ipynb`](kaggle_config_g_lora.ipynb)

## 1. Kaggle setup (one time)

1. Go to https://www.kaggle.com/code → **New Notebook** → **File ▸ Import Notebook** and upload
   `experiments/config_g_lora/kaggle_config_g_lora.ipynb`.
2. **Enable GPU:** right sidebar **Settings ▸ Accelerator ▸ GPU T4 x1** (P100 also fine).
   Without a GPU the notebook stops and records `BLOCKED_NOT_RUN` — it will not simulate training.
3. **Internet on:** **Settings ▸ Internet ▸ On** (needed to clone the repo + download the model).
4. **Add the HF token secret:** **Add-ons ▸ Secrets ▸ Add secret**
   - Name (exactly): `HF_TOKEN`
   - Value: a *read* token from https://huggingface.co/settings/tokens
   - The notebook reads it via `UserSecretsClient`; it is never printed or committed.

## 2. Is `HF_TOKEN` required?

`Qwen/Qwen2.5-0.5B-Instruct` is a public model, so download usually works even without a token.
The notebook still **verifies model access** and, per the run protocol, **stops on 401/403** rather
than silently switching models. Adding `HF_TOKEN` is recommended (avoids rate limits / future gating).

## 3. Run

Press **Run All**. Order of operations:

1. Environment check (Python/OS/arch/CPU/RAM/disk/GPU/CUDA/torch). No GPU ⇒ STOP.
2. Clone `https://github.com/zda25m005-netizen/agentic-ai-os.git`, install `peft` (+ `bitsandbytes`
   if available), put the repo on `sys.path`. QLoRA is used only if `bitsandbytes` imports on this
   box; otherwise plain LoRA runs and is recorded as `quantization: "none"`.
3. HF auth + model-access verification.
4. Load the existing Config-G code and build the shared eval env.
5. Baseline eval: **A** random, **B** heuristic, **C** base Qwen (real generations).
6. **One real LoRA/QLoRA GRPO training run** (saves the adapter).
7. Trained eval **D** on the *same* env.
8. Write `results.json`, print the `CONFIG G REAL EXPERIMENT` summary.

Runtime: a few minutes on a T4 (0.5B model, 401 eval steps ×3 policies, 64 training steps).

## 4. Exact experiment configuration

| | |
|---|---|
| Model | `Qwen/Qwen2.5-0.5B-Instruct` |
| Dataset | `TrajectoryMemoryEnv(n=100, seed=0)` → 401 decision steps |
| LoRA | r=8, α=16, target_modules=[q_proj, v_proj] |
| Quantization | QLoRA 4-bit if `bitsandbytes` available, else `none` (recorded) |
| Optimizer | AdamW, lr=1e-4 |
| GRPO | group_size=8 |
| Schedule | epochs=1, max_states=64 ⇒ 64 optimizer steps |
| Seed | 0 |

## 5. Fair before/after

The **same** `env` (same trajectories, seed, states) is used for baseline and trained eval — the
env is built once and reused. Compared: A random · B heuristic · C base LLM · D trained LLM.

## 6. Metrics (honest scope)

Directly reported: **policy_action_accuracy** (overall + per-op) and **decision_latency**.
Label-derived from the env's optimal actions: **unnecessary_write_rate**,
**unnecessary_retrieval_rate**, **stale_memory_leak_rate**. Recorded as **`not_measured`** (with a
reason): memory retrieval P/R/F1, temporal_update_accuracy, task_success, token_efficiency,
memory_induced_error_rate — these need a downstream-task / retrieved-vs-gold harness that this
trajectory env does not produce. Nothing is fabricated.

## 7. Outputs

- `results.json` → written to `agentic-ai-os/experiments/config_g_lora/results.json` **and**
  `/kaggle/working/results.json` (download this from the Kaggle output panel).
- LoRA adapter → `agentic-ai-os/experiments/config_g_lora/adapter/` (ephemeral Kaggle output,
  **not** committed to git).

## 8. What to send back

Paste the printed **`CONFIG G REAL EXPERIMENT`** block and attach **`results.json`**. I'll then
record the first real trained-policy numbers into the repo (updating `run_2026-09-08.json` /
the docs) and flip the status from `BLOCKED_NOT_RUN` to `COMPLETED`.

## Notes

- RL stays disabled in production (`MEMORY_POLICY_MODE=deterministic`); this experiment does not
  change the default path or any agent.
- If `bitsandbytes` fails to import on the Kaggle image, that is expected on some builds — the
  notebook falls back to plain LoRA and records `quantization: "none"`. That is a real result, not
  a failure.
