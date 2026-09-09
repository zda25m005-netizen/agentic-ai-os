"""LLM memory policy (config G) — an open-weight small model picks the memory op.

This is the "real research layer" on top of the toy LinearPolicy (config F): a small
open-weight instruction model (default ``Qwen/Qwen2.5-0.5B-Instruct``), optionally with a
LoRA/QLoRA adapter, reads the agent's observation + memory state and chooses one of the six
ops (STORE / RETRIEVE / UPDATE / SUMMARIZE / DISCARD / NOOP).

Dependency policy — this is the crux of keeping the repo green:
- ``transformers`` / ``peft`` / ``torch`` are imported **lazily**, only inside
  ``_ensure_model``. Importing this module never requires them.
- ``HeuristicPolicy`` is a dependency-free six-action rule set. It is the fallback whenever
  the model backend is unavailable (no torch) or a generation fails, so ``LLMMemoryPolicy``
  is always a usable, testable object — and RL stays disabled by default.

Both policies expose:
    act(state) -> MemoryOp            # the six-action trajectory decision
    decide(feats) -> int              # the resolver's ADD/UPDATE/NOOP (via op mapping)
so the same object can drive both the trajectory env and the existing Mem0 resolver.
"""

from __future__ import annotations

from app.memory.trajectory.actions import MemoryOp, op_to_resolver_action
from app.memory.trajectory.prompt import build_prompt, parse_action


def backend_available() -> bool:
    """True only if the LLM stack (torch + transformers) can be imported."""
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401

        return True
    except Exception:
        return False


class HeuristicPolicy:
    """Dependency-free six-action rule set — the safe fallback and a strong baseline.

    Encodes the same intent the reward function rewards, so it doubles as a sanity ceiling
    for the learned policy in tests and offline eval.
    """

    def act(self, state: dict) -> MemoryOp:
        f = state.get("feats", {})
        ms = state.get("memory_state", {})
        over_budget = f.get("over_budget") or (
            ms.get("budget") and ms.get("size", 0) > ms["budget"]
        )
        if f.get("is_query"):
            return MemoryOp.RETRIEVE
        if f.get("is_correction") and f.get("sim", 0.0) >= 0.25:
            return MemoryOp.UPDATE
        if f.get("is_noise"):
            return MemoryOp.DISCARD
        if f.get("sim", 0.0) >= 0.85:
            return MemoryOp.NOOP
        if over_budget:
            return MemoryOp.SUMMARIZE
        return MemoryOp.STORE

    def decide(self, feats: dict) -> int:
        # Build a minimal state from resolver features so act() can run.
        state = {
            "feats": {
                "sim": feats.get("best_sim", 0.0),
                "is_correction": bool(feats.get("is_correction")),
                "is_noise": False,
                "is_query": False,
                "over_budget": False,
            },
            "memory_state": {},
        }
        if feats.get("exact_match"):
            return op_to_resolver_action(MemoryOp.NOOP)
        return op_to_resolver_action(self.act(state))


class LLMMemoryPolicy:
    """Open-weight LLM policy with an optional LoRA adapter; heuristic fallback."""

    def __init__(
        self,
        model_name: str = "Qwen/Qwen2.5-0.5B-Instruct",
        *,
        adapter_path: str | None = None,
        max_new_tokens: int = 4,
        fallback: HeuristicPolicy | None = None,
    ):
        self.model_name = model_name
        self.adapter_path = adapter_path
        self.max_new_tokens = max_new_tokens
        self.fallback = fallback or HeuristicPolicy()
        self._model = None
        self._tokenizer = None

    # --- availability --------------------------------------------------------
    def available(self) -> bool:
        return backend_available()

    def _ensure_model(self) -> bool:
        """Lazily load tokenizer + model (+ LoRA adapter). Returns False on any failure."""
        if self._model is not None:
            return True
        if not backend_available():
            return False
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            tok = AutoTokenizer.from_pretrained(self.model_name)
            # Use fp16 on GPU, fp32 on CPU; place on CUDA when available (no-op on CPU).
            on_gpu = torch.cuda.is_available()
            dtype = torch.float16 if on_gpu else torch.float32
            model = AutoModelForCausalLM.from_pretrained(self.model_name, torch_dtype=dtype)
            if self.adapter_path:
                from peft import PeftModel

                model = PeftModel.from_pretrained(model, self.adapter_path)
            if on_gpu:
                model = model.to("cuda")
            model.eval()
            self._tokenizer, self._model = tok, model
            return True
        except Exception:
            return False

    # --- inference -----------------------------------------------------------
    def act(self, state: dict) -> MemoryOp:
        """Choose a six-action op for one trajectory decision."""
        if not self._ensure_model():
            return self.fallback.act(state)  # graceful: heuristic when no model
        try:
            import torch

            messages = build_prompt(state)
            prompt = self._tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            inputs = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)
            with torch.no_grad():
                out = self._model.generate(
                    **inputs, max_new_tokens=self.max_new_tokens, do_sample=False
                )
            text = self._tokenizer.decode(
                out[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True
            )
            return parse_action(text)
        except Exception:
            return self.fallback.act(state)

    def decide(self, feats: dict) -> int:
        """Resolver-compatible ADD/UPDATE/NOOP decision (projects the six-action op)."""
        if feats.get("exact_match"):
            return op_to_resolver_action(MemoryOp.NOOP)
        state = {
            "feats": {
                "sim": feats.get("best_sim", 0.0),
                "is_correction": bool(feats.get("is_correction")),
                "is_noise": False,
                "is_query": False,
                "over_budget": False,
            },
            "memory_state": {"has_similar": feats.get("has_best")},
        }
        action = op_to_resolver_action(self.act(state))
        # Same safety clamp as the linear policy: no neighbour -> cannot NOOP/UPDATE.
        from app.memory.policy import ADD, NOOP, UPDATE

        if action in (NOOP, UPDATE) and not feats.get("has_best"):
            return ADD
        return action
