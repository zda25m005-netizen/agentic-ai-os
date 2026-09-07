"""Mem0-style memory lifecycle: extract candidates -> retrieve similar -> resolve.

Pipeline (deterministic by default; optional LLM extraction when policy_mode == 'llm'):

    conversation/answer text
        -> extract_candidates()      # atomic candidate statements
        -> for each: retrieve similar current memories (orchestrator)
        -> resolver: NOOP (near-duplicate) | UPDATE (explicit correction) | ADD

Nothing is fabricated: candidates are extracted verbatim from the text, and the
resolver only supersedes on an explicit correction cue against a similar memory.
"""

from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable

from app.memory.orchestrator import MemoryOrchestrator
from app.memory.policy import ADD, NOOP, UPDATE, DeterministicPolicy, MemoryPolicy

ChatFn = Callable[[list[dict]], Awaitable[str]]

# A statement is a durable candidate if it looks like a stable fact/preference.
_CUES = re.compile(
    r"\b(prefer|prefers|preferred|favou?rite|interested in|research(?:es|ing)?|"
    r"first[- ]choice|considering|wants?|looking for|works? at|studies|studying|"
    r"based in|my |i am|i'm|no longer|now|instead|switched|changed)\b",
    re.I,
)
_CORRECTION = re.compile(
    r"\b(no longer|now|instead|changed|switched|actually|rather than|not .* anymore)\b", re.I
)
_STOP = {
    "the",
    "a",
    "an",
    "is",
    "are",
    "for",
    "to",
    "of",
    "in",
    "on",
    "and",
    "my",
    "i",
    "user",
    "user's",
    "am",
    "now",
    "also",
    "considering",
    "prefer",
    "prefers",
}


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text or "") if s.strip()]


def _tokens(text: str) -> set[str]:
    return {
        w
        for w in re.findall(r"[a-zA-Z][a-zA-Z0-9]+", text.lower())
        if w not in _STOP and len(w) > 2
    }


def _jaccard(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def extract_candidates(text: str, *, source: str = "agent", max_candidates: int = 8) -> list[dict]:
    """Deterministic extraction of atomic candidate memories from text."""
    out: list[dict] = []
    seen: set[str] = set()
    for s in _sentences(text):
        if len(s) < 8 or len(s) > 300 or not _CUES.search(s):
            continue
        norm = s.lower()
        if norm in seen:
            continue
        seen.add(norm)
        out.append(
            {
                "content": s,
                "memory_type": "semantic",
                "confidence": 0.75,
                "source": source,
                "is_correction": bool(_CORRECTION.search(s)),
            }
        )
        if len(out) >= max_candidates:
            break
    return out


async def extract_candidates_llm(
    text: str, chat_fn: ChatFn, *, source: str = "agent"
) -> list[dict]:
    """Optional LLM extraction (used only when policy_mode == 'llm'). Falls back to
    deterministic extraction if the model output is unusable."""
    sys = (
        "Extract atomic, durable memories (facts/preferences about the user) from the text. "
        "Return ONLY a JSON array of short strings, each a single self-contained statement. "
        "Do not invent anything not present in the text."
    )
    try:
        raw = await chat_fn(
            [{"role": "system", "content": sys}, {"role": "user", "content": text[:4000]}]
        )
        m = re.search(r"\[.*\]", raw or "", re.DOTALL)
        arr = json.loads(m.group(0)) if m else []
        cands = [
            {
                "content": str(x).strip(),
                "memory_type": "semantic",
                "confidence": 0.75,
                "source": source,
                "is_correction": bool(_CORRECTION.search(str(x))),
            }
            for x in arr
            if isinstance(x, str) and 8 <= len(str(x)) <= 300
        ]
        return cands or extract_candidates(text, source=source)
    except Exception:
        return extract_candidates(text, source=source)


def resolve_and_ingest(
    orch: MemoryOrchestrator,
    candidates: list[dict],
    *,
    mission_id: int | None = None,
    dup_threshold: float = 0.8,
    correction_threshold: float = 0.25,
    policy: MemoryPolicy | None = None,
) -> dict:
    """Retrieve-similar + resolver. Returns operation counts + details.

    The NOOP/UPDATE/ADD decision is delegated to ``policy`` (config F). The default is a
    ``DeterministicPolicy`` built from the same thresholds, so the behavior is byte-for-byte
    identical to the original rule set — an RL policy only takes over when one is passed in.
    """
    if policy is None:
        policy = DeterministicPolicy(dup_threshold, correction_threshold)
    ops = {"ADD": 0, "UPDATE": 0, "NOOP": 0}
    details: list[dict] = []
    for c in candidates:
        content = c["content"]
        similar, _ = orch.retrieve(content, limit=5)
        best = max(similar, key=lambda r: _jaccard(content, r.content), default=None)
        best_sim = _jaccard(content, best.content) if best else 0.0
        exact = bool(best and content.strip().lower() == best.content.strip().lower())

        action = policy.decide(
            {
                "best_sim": best_sim,
                "is_correction": bool(c.get("is_correction")),
                "has_best": best is not None,
                "exact_match": exact,
            }
        )
        # A learned policy may pick an action illegal for this state; clamp to ADD.
        if action in (NOOP, UPDATE) and best is None:
            action = ADD

        if action == NOOP:
            orch.reinforce(best.id)  # near-duplicate -> reinforce, don't duplicate
            ops["NOOP"] += 1
            details.append({"op": "NOOP", "target": best.id})
        elif action == UPDATE:
            rec = orch.supersede(best.id, content, source=c["source"], confidence=c["confidence"])
            ops["UPDATE"] += 1
            details.append({"op": "UPDATE", "target": best.id, "new": rec.id if rec else None})
        else:
            res = orch.remember(
                content,
                memory_type=c["memory_type"],
                source=c["source"],
                confidence=c["confidence"],
                mission_id=mission_id,
            )
            ops["ADD"] += 1
            details.append({"op": res["operation"], "id": res["record"].id})
    return {"ops": ops, "details": details, "candidates": len(candidates)}
