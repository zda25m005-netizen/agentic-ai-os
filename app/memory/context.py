"""MemGPT-style context controller: budget, prioritize, evict, assemble.

Sits in front of the orchestrator at retrieval time. It ranks + budgets retrieved
memories (and any working-context notes) so injected memory can never overflow the
context window, truncates over-long individual items (eviction), and reports
utilization for observability. Deterministic; the current request stays authoritative
(memory is emitted as clearly-labelled ADVISORY context).
"""

from __future__ import annotations

from app.memory.orchestrator import MemoryOrchestrator

_HEADER = "Relevant remembered context (advisory — the current request takes precedence):"


def _tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _clip(text: str, max_chars: int = 240) -> str:
    text = " ".join(text.split())
    return text if len(text) <= max_chars else text[: max_chars - 1].rstrip() + "…"


class ContextController:
    def __init__(self, orch: MemoryOrchestrator, token_budget: int = 600):
        self.orch = orch
        self.token_budget = token_budget

    def build(self, query: str, *, working_notes: list[str] | None = None) -> dict:
        """Assemble a budgeted, advisory context block for `query`."""
        # reserve up to a third of the budget for recent working notes
        wn_budget = self.token_budget // 3 if working_notes else 0
        mem_budget = self.token_budget - wn_budget

        recs, mem_tokens = self.orch.retrieve(query, token_budget=mem_budget, limit=8)

        lines: list[str] = []
        used = 0
        if working_notes:
            for note in working_notes[-5:]:
                clipped = _clip(note)
                t = _tokens(clipped)
                if used + t > wn_budget:
                    break
                lines.append(f"- [working] {clipped}")
                used += t

        evicted = 0
        for r in recs:
            clipped = _clip(r.content)
            t = _tokens(clipped)
            if used + t > self.token_budget:
                evicted += 1
                continue
            lines.append(f"- [{r.memory_type}] {clipped}")
            used += t

        context = (_HEADER + "\n" + "\n".join(lines)) if lines else ""
        return {
            "context": context,
            "records": recs,
            "tokens": used,
            "utilization": round(used / self.token_budget, 3) if self.token_budget else 0.0,
            "evicted": evicted,
            "count": len(lines),
        }
