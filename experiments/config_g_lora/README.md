# Config G — LLM memory policy LoRA/QLoRA training run

**Status: BLOCKED — training did not run. No trained-policy results exist.**
Date (UTC): 2026-09-08. Machine-readable record: [`run_2026-09-08.json`](run_2026-09-08.json).

This is an honest experiment log. The end-to-end LoRA/QLoRA GRPO training of the config-G
LLM memory policy could **not** be executed in the available environment. Per the run
protocol, training was **not simulated** — the exact blockers are recorded instead, along
with the real baseline metrics that *can* be measured without a model or training.

## Exact blockers (evidence)

| # | Blocker | Severity | Evidence |
|---|---------|----------|----------|
| 1 | No GPU / CUDA | hard | `nvidia-smi` not found; no `/dev/nvidia*`. QLoRA (`bitsandbytes` 4-bit) needs CUDA and has no aarch64 build. |
| 2 | Model weights unreachable | hard | `GET huggingface.co/Qwen/Qwen2.5-0.5B-Instruct/…/config.json` → `Tunnel connection failed: 403 Forbidden`. |
| 3 | ML deps not installed | hard | `torch/transformers/peft/bitsandbytes/accelerate` all MISSING. PyPI is reachable (HTTP 200), so install is possible on a supported host — but that does not fix #1 or #2. |
| 4 | RAM marginal | soft | 3.8 GiB total; a 0.5B fp32 model needs ~2 GiB weights + framework + autograd. |

Environment probed: Linux **aarch64**, 4 CPU cores, 3.8 GiB RAM, **no GPU**, 5.1 GiB disk free.

## Intended configuration (recorded for reproducibility)

- **Model:** `Qwen/Qwen2.5-0.5B-Instruct` (open-weight)
- **Adapter:** LoRA `r=8`, `alpha=16`, `target_modules=[q_proj, v_proj]`; QLoRA 4-bit optional
- **Trainer:** `app.memory.rl.llm_grpo.LLMGRPOTrainer` (GRPO, group-relative advantage on action-token log-probs), AdamW `lr=1e-4`, `group_size=8`
- **Dataset:** `TrajectoryMemoryEnv(n=100, seed=0)` → 401 labelled decision steps
- **Planned run:** 1 epoch, `max_states=64` ⇒ 64 optimizer steps, `seed=0`
- **Checkpoint path:** none written (training did not run)

## Measured baselines (REAL — no training, no model)

These are genuine measurements of the existing non-LLM policies on the real env / lifecycle
eval. They form the **baseline column only**; there is deliberately **no trained-policy
column**.

| Metric | Baseline | How |
|---|---|---|
| policy_action_accuracy (heuristic, 6-action) | **0.98** | `HeuristicPolicy` over 401 env steps, seed 0 |
| policy_action_accuracy (uniform random ref) | 0.1671 | random floor, seed 0 |
| memory_retrieval_accuracy (lifecycle, config D) | **P 0.875 / R 1.0** | `evaluate("lifecycle")` on local fixtures |
| temporal_update (stale leaks) | **0** | same lifecycle eval |
| decision latency (heuristic) | <0.001 ms/decision | `time.perf_counter` over 401 decisions |
| task_success | not measured | needs a downstream task harness |
| token_efficiency | not measured | needs the summarize path under a real budget |

Per-op heuristic accuracy: STORE 1.0, RETRIEVE 1.0, UPDATE 1.0, DISCARD 1.0, NOOP 1.0,
SUMMARIZE 0.896.

> The heuristic baseline is intentionally strong (it encodes the reward structure). The
> point of training the LLM policy is to learn comparable behaviour from reward **without**
> hand-written rules, and to generalize to observations the rules don't cover — which is
> exactly what this blocked run was meant to test.

## How to actually run this (on a supported host)

Requires a CUDA GPU (or ≥16 GiB RAM for a slow CPU LoRA run) **and** network access to
`huggingface.co`.

```bash
pip install -e ".[finetune]"          # torch, transformers, peft, bitsandbytes, accelerate
python - <<'PY'
from app.memory.rl.llm_grpo import LLMGRPOTrainer
from app.memory.trajectory import TrajectoryMemoryEnv
from app.memory.llm_policy import LLMMemoryPolicy
from app.memory.metrics_suite import evaluate_policy_on_env

env = TrajectoryMemoryEnv(n=100, seed=0)

# BEFORE: base model, no adapter
before = evaluate_policy_on_env(LLMMemoryPolicy("Qwen/Qwen2.5-0.5B-Instruct"), env)

# TRAIN: LoRA (add quantized=True for QLoRA on a CUDA box)
rep = LLMGRPOTrainer("Qwen/Qwen2.5-0.5B-Instruct", group_size=8, lr=1e-4, seed=0)\
        .train(env, epochs=1, max_states=64, out_dir="experiments/config_g_lora/adapter")

# AFTER: same base model + trained adapter
after = evaluate_policy_on_env(
    LLMMemoryPolicy("Qwen/Qwen2.5-0.5B-Instruct", adapter_path="experiments/config_g_lora/adapter"), env)

print("train:", rep); print("before:", before); print("after:", after)
PY
```

Record the resulting numbers here alongside the exact seed, dataset size, optimizer steps,
model id, GPU model, and checkpoint path — then flip this file's status to `RUN`.

## Production note

RL is **off by default** (`MEMORY_POLICY_MODE=deterministic`). None of the above changes the
production path: the deterministic policy remains the default and no model is loaded unless
`MEMORY_POLICY_MODE=rl` and `MEMORY_POLICY_BACKEND=llm` are set with a reachable model.
