"""Rich memory object model + lifecycle (production-grade metadata).

This is the canonical record the MemoryOrchestrator persists. It layers full
provenance / temporal-validity / lifecycle metadata over the existing five-layer
concept (working/episodic/semantic/procedural/organizational) without replacing
the in-memory `multilayer`/`dynamics` modules, which remain the fast scratchpad +
decay engine behind the orchestrator.
"""

from __future__ import annotations

import time
import uuid

from pydantic import BaseModel, Field

# Reuse the existing five-layer vocabulary.
LAYERS = ["working", "episodic", "semantic", "procedural", "organizational"]
# Lifecycle: CAPTURED -> CANDIDATE -> VERIFIED -> ACTIVE -> REINFORCED ->
#            UPDATED/SUPERSEDED -> ARCHIVED. Historical facts are never hard-deleted
#            when they are superseded — they move to SUPERSEDED/ARCHIVED and stay
#            queryable for temporal reasoning.
STATUSES = [
    "captured",
    "candidate",
    "verified",
    "active",
    "reinforced",
    "updated",
    "superseded",
    "archived",
]


def _now() -> float:
    return time.time()


class MemoryRecord(BaseModel):
    id: str = Field(default_factory=lambda: f"mem-{uuid.uuid4().hex[:12]}")
    memory_type: str = "semantic"  # one of LAYERS
    content: str = ""
    key: str | None = None
    tags: list[str] = Field(default_factory=list)
    source: str = "agent"  # who created it (agent name / "user" / mission)
    source_id: str | None = None
    agent_id: str | None = None
    mission_id: int | None = None
    conversation_id: str | None = None
    owner: str = "me"  # user/workspace isolation key
    confidence: float = 0.7  # 0..1
    importance: float = 1.0  # decays over time; reinforced on access
    created_at: float = Field(default_factory=_now)
    updated_at: float = Field(default_factory=_now)
    last_accessed_at: float | None = None
    access_count: int = 0
    status: str = "active"  # one of STATUSES
    valid_from: float | None = None
    valid_until: float | None = None  # None = currently valid
    supersedes_id: str | None = None
    provenance: str | None = None  # short human-readable origin, e.g. "user said 2026-09"
    embedding_reference: str | None = None  # qdrant point id when semantically indexed
    pinned: bool = False

    def strength(self, decay_rate: float = 0.05, now: float | None = None) -> float:
        """Normalized 0..1 freshness: importance decayed since last access."""
        import math

        base = self.last_accessed_at or self.created_at
        dt_hours = max(0.0, ((now or _now()) - base) / 3600.0)
        decayed = self.importance * math.exp(-decay_rate * dt_hours)
        return round(max(0.0, min(1.0, decayed / max(self.importance, 1.0))), 3)

    def is_current(self, now: float | None = None) -> bool:
        return self.status not in ("superseded", "archived") and (
            self.valid_until is None or (now or _now()) < self.valid_until
        )
