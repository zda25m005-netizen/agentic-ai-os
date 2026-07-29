"""Memory manager: one interface over episodic + semantic memory.

`remember` writes a run to both the durable episodic log (SQLite) and the
semantic index (vectors); `recall` returns semantically similar past runs,
formatted for injection into a planner prompt. A process-wide default lets
graph nodes use memory without threading it through every call, and it's
settable for tests.
"""
from __future__ import annotations

from app.memory.episodic import EpisodicMemory
from app.memory.semantic import MemoryHit, SemanticMemory


class MemoryManager:
    """Unified episodic + semantic memory."""

    def __init__(self, episodic: EpisodicMemory, semantic: SemanticMemory):
        self.episodic = episodic
        self.semantic = semantic

    async def remember(self, goal: str, answer: str) -> None:
        self.episodic.save(goal, answer)
        await self.semantic.add(goal, answer)

    async def recall(self, query: str, limit: int = 3) -> list[MemoryHit]:
        return await self.semantic.recall(query, limit=limit)

    @staticmethod
    def format_recall(hits: list[MemoryHit]) -> str:
        """Render recalled runs as context lines for a prompt."""
        if not hits:
            return ""
        lines = ["Relevant past work:"]
        for i, h in enumerate(hits, start=1):
            lines.append(f"[{i}] Goal: {h.goal} -> {h.answer}")
        return "\n".join(lines)


_default: MemoryManager | None = None


def get_memory() -> MemoryManager | None:
    """Return the process-wide memory manager, if one is set."""
    return _default


def set_memory(manager: MemoryManager | None) -> None:
    """Install (or clear) the process-wide memory manager."""
    global _default
    _default = manager
