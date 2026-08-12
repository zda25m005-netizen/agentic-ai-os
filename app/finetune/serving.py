"""Serve the fine-tuned model when available, else fall back to the API model.

Routing rule: if `USE_FINETUNED` is on AND a merged adapter exists on disk, run
local inference; otherwise use the API LLM. If local generation fails at runtime
(e.g. torch not installed on this box), we fall back to the API and report which
model actually answered — so serving never hard-fails.
"""
from __future__ import annotations

import os
from pathlib import Path

from app.core.config import get_settings


def finetuned_available() -> bool:
    """True only if enabled and a usable model directory exists on disk."""
    s = get_settings()
    if not s.use_finetuned:
        return False
    d = s.finetuned_model_dir
    return os.path.isdir(d) and os.path.isfile(os.path.join(d, "config.json"))


def model_label() -> str:
    """Which model *would* answer right now: 'finetuned' or 'api'."""
    return "finetuned" if finetuned_available() else "api"


def model_display_name(label: str) -> str:
    """Human/metrics-friendly name for a served model label."""
    s = get_settings()
    if label == "finetuned":
        return f"lora:{Path(s.finetuned_model_dir).name}"
    return s.llm_model


_local = None


def _load_local():
    global _local
    if _local is None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        d = get_settings().finetuned_model_dir
        tok = AutoTokenizer.from_pretrained(d)
        model = AutoModelForCausalLM.from_pretrained(d)
        model.eval()
        _local = (tok, model, torch)
    return _local


def generate_local(messages: list[dict], max_new_tokens: int = 128) -> str:
    """Local inference through the fine-tuned model (lazy heavy imports)."""
    tok, model, torch = _load_local()
    prompt = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tok(prompt, return_tensors="pt")
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    gen = out[0][inputs["input_ids"].shape[1]:]
    return tok.decode(gen, skip_special_tokens=True).strip()


async def answer(
    messages: list[dict],
    api_chat=None,
    local_generate=None,
    available: bool | None = None,
) -> tuple[str, str]:
    """Return (text, model_label). Prefer fine-tuned; fall back to API on any issue.

    The three dependencies are injectable so routing/fallback are unit-tested
    without torch or a live API.
    """
    from app.core import llm

    api_chat = api_chat or llm.chat
    local_generate = local_generate or generate_local
    is_available = available if available is not None else finetuned_available()

    if is_available:
        try:
            return local_generate(messages), "finetuned"
        except Exception:  # noqa: BLE001 - degrade to the API, never hard-fail
            pass
    return await api_chat(messages), "api"
