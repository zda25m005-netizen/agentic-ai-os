"""Memory dynamics: importance, decay, consolidation, conflict resolution.

Static stores (Day 18) aren't enough — a real memory forgets trivia, strengthens
what's used, moves important short-term notes into long-term stores, and resolves
contradictory facts. `MemoryDynamics` layers those behaviors over a
`MultiLayerMemory`:

- **importance / reinforcement** — retrieving an item boosts its importance and
  records the access (frequently used memories stay strong);
- **decay** — importance decays exponentially with time since last access; items
  below a threshold are pruned (procedural skills are exempt — they persist);
- **consolidation** — high-importance working-memory notes are promoted into the
  episodic log and cleared from the transient scratchpad;
- **conflict resolution** — asserting a fact that contradicts a stored one keeps
  the higher-importance value (ties go to the newer assertion).

All deterministic given an injected `now`, so it's fully unit-testable.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from app.memory.multilayer import MemoryItem, MemoryType, MultiLayerMemory


@dataclass
class MemoryDynamics:
    memory: MultiLayerMemory
    decay_rate: float = 0.05          # per hour
    access_boost: float = 0.5
    consolidate_threshold: float = 2.0
    prune_threshold: float = 0.1

    def touch(self, item: MemoryItem, now: float) -> None:
        """Reinforce an item on access: boost importance, record the access."""
        item.access_count += 1
        item.last_access = now
        item.importance += self.access_boost

    def retrieve(self, query: str, now: float, limit: int = 5) -> list[MemoryItem]:
        """Retrieve across layers and reinforce whatever was accessed."""
        hits = self.memory.retrieve(query, limit=limit)
        for h in hits:
            self.touch(h, now)
        return hits

    def decay(self, now: float) -> int:
        """Decay importance by time since last access; prune weak items.

        Returns the number of items pruned. Procedural memory is never pruned.
        """
        pruned = 0
        for store in self.memory.stores():
            for item in store.all():
                dt_hours = max(0.0, (now - item.last_access) / 3600.0)
                item.importance *= math.exp(-self.decay_rate * dt_hours)
                item.last_access = now  # so decay isn't compounded next call
            if store._type != MemoryType.PROCEDURAL:
                keep = [i for i in store.all() if i.importance >= self.prune_threshold]
                pruned += len(store._items) - len(keep)
                store._items = keep
        return pruned

    def consolidate(self, now: float) -> int:
        """Promote important working-memory notes into the episodic log."""
        promoted, remaining = [], []
        for item in self.memory.working.all():
            if item.importance >= self.consolidate_threshold:
                self.memory.episodic.record(
                    item.content, tags=item.tags, importance=item.importance)
                promoted.append(item)
            else:
                remaining.append(item)
        self.memory.working._items = remaining
        return len(promoted)

    def assert_fact(self, key: str, value: str, importance: float, now: float) -> str:
        """Store a semantic fact, resolving conflicts. Returns the action taken.

        new | reinforced | overridden | kept_existing
        """
        existing = next((i for i in self.memory.semantic.all() if i.key == key), None)
        if existing is None:
            self.memory.semantic.learn(key, value, importance)
            return "new"
        if existing.content == value:
            self.touch(existing, now)  # same fact seen again -> reinforce
            return "reinforced"
        if importance >= existing.importance:  # conflict: higher importance wins
            existing.content = value
            existing.importance = importance
            existing.last_access = now
            return "overridden"
        return "kept_existing"
