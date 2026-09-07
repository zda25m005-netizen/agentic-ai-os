"""GRPO training of the LLM memory policy with LoRA/QLoRA (config G, experimental).

This is the genuine RL layer: the six-action decision is emitted by a small open-weight
LLM, and only a LoRA (or QLoRA, 4-bit) adapter is trained by GRPO. The heavy stack
(``torch`` / ``transformers`` / ``peft`` / ``bitsandbytes``) is imported **lazily inside
methods**, so importing this module — and running the whole test suite — needs none of it.
When the stack is absent, ``LLMGRPOTrainer.train`` raises a clear, actionable error instead
of failing at import time.

GRPO recap (same idea as config F, now on token log-probs): for each decision state, sample
a *group* of G actions from the current policy, score each with the trajectory reward,
standardize rewards within the group to get advantages, and take a policy-gradient step that
raises the log-prob of above-average actions. The group mean is the baseline — no critic.

The advantage computation is pure-numpy and lives in ``group_advantages`` so it is unit
tested directly; the torch/LoRA plumbing around it is exercised only on a GPU/CPU box with
the ``finetune`` extra installed (``pip install -e ".[finetune]"``).
"""

from __future__ import annotations

import numpy as np

from app.memory.trajectory.actions import OPS, MemoryOp
from app.memory.trajectory.env import TrajectoryMemoryEnv
from app.memory.trajectory.prompt import build_prompt


def group_advantages(rewards: list[float] | np.ndarray) -> np.ndarray:
    """GRPO group-relative advantage: standardize rewards within the sampled group."""
    r = np.asarray(rewards, dtype=float)
    adv = r - r.mean()
    std = r.std()
    if std > 1e-8:
        adv = adv / std
    return adv


def backend_available() -> bool:
    try:
        import peft  # noqa: F401
        import torch  # noqa: F401
        import transformers  # noqa: F401

        return True
    except Exception:
        return False


class LLMGRPOTrainer:
    """GRPO trainer that fine-tunes a LoRA/QLoRA adapter on the trajectory env.

    Nothing heavy happens until ``train`` is called; construction is cheap and import-safe.
    """

    def __init__(
        self,
        model_name: str = "Qwen/Qwen2.5-0.5B-Instruct",
        *,
        group_size: int = 8,
        lr: float = 1e-4,
        lora_r: int = 8,
        lora_alpha: int = 16,
        quantized: bool = False,  # QLoRA (4-bit) when True
        seed: int = 0,
    ):
        self.model_name = model_name
        self.group_size = group_size
        self.lr = lr
        self.lora_r = lora_r
        self.lora_alpha = lora_alpha
        self.quantized = quantized
        self.seed = seed

    # --- model plumbing (lazy) ----------------------------------------------
    def _build_model(self):  # pragma: no cover - requires the finetune extra + weights
        import torch
        from peft import LoraConfig, get_peft_model
        from transformers import AutoModelForCausalLM, AutoTokenizer

        tok = AutoTokenizer.from_pretrained(self.model_name)
        kwargs = {"torch_dtype": torch.float32}
        if self.quantized:
            # QLoRA: 4-bit base weights, trainable LoRA adapter on top.
            from transformers import BitsAndBytesConfig

            kwargs = {
                "quantization_config": BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=torch.float16,
                )
            }
        model = AutoModelForCausalLM.from_pretrained(self.model_name, **kwargs)
        lora = LoraConfig(
            r=self.lora_r,
            lora_alpha=self.lora_alpha,
            target_modules=["q_proj", "v_proj"],
            task_type="CAUSAL_LM",
        )
        model = get_peft_model(model, lora)
        return tok, model

    # --- training ------------------------------------------------------------
    def train(  # pragma: no cover - requires the finetune extra + model weights
        self,
        env: TrajectoryMemoryEnv | None = None,
        *,
        epochs: int = 1,
        max_states: int | None = None,
        out_dir: str | None = None,
    ) -> dict:
        """Run GRPO over the trajectory env, updating only the LoRA adapter.

        Raises RuntimeError (not ImportError at module load) when the heavy stack is absent,
        so the rest of the app is unaffected by config G being unavailable.
        """
        if not backend_available():
            raise RuntimeError(
                "LLM GRPO training needs torch + transformers + peft. Install the finetune "
                "extra on a GPU/CPU box: pip install -e '.[finetune]'. The default runtime "
                "keeps RL disabled and uses the deterministic/linear policy."
            )
        import torch

        env = env or TrajectoryMemoryEnv(seed=self.seed)
        tok, model = self._build_model()
        model.train()
        opt = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=self.lr)
        rng = np.random.default_rng(self.seed)
        # token ids for each action word, used to score sampled actions
        action_ids = [tok(a, add_special_tokens=False)["input_ids"][0] for a in OPS]

        states = env.states()
        if max_states:
            states = states[:max_states]
        history = []
        for _ in range(epochs):
            for s in states:
                messages = build_prompt(s)
                prompt = tok.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )
                inputs = tok(prompt, return_tensors="pt")
                logits = model(**inputs).logits[0, -1]  # next-token logits
                logp = torch.log_softmax(logits, dim=-1)
                act_logp = torch.stack([logp[i] for i in action_ids])  # log π over 6 ops
                probs = torch.softmax(act_logp.detach(), dim=-1).numpy()
                sampled = rng.choice(len(OPS), size=self.group_size, p=probs / probs.sum())
                rewards = [env.reward(s, MemoryOp(int(a))) for a in sampled]
                adv = group_advantages(rewards)
                loss = -torch.stack(
                    [act_logp[int(a)] * float(A) for a, A in zip(sampled, adv, strict=False)]
                ).mean()
                opt.zero_grad()
                loss.backward()
                opt.step()
            history.append({"loss": float(loss.item())})
        if out_dir:
            model.save_pretrained(out_dir)  # saves ONLY the LoRA adapter
            tok.save_pretrained(out_dir)
        return {"epochs": epochs, "states": len(states), "adapter_dir": out_dir, "history": history}
