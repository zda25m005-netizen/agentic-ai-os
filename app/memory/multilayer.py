"""Multi-layer memory: five stores with distinct roles, one retrieval interface.

v1 gave the agent episodic (SQLite) + semantic (Qdrant) recall. A long-horizon
system needs more than that, so this adds a cognitively-inspired **five-layer**
memory the mission runtime can use, all in-memory and dependency-free:

- **working** — short-term scratchpad, capacity-bounded (evicts oldest);
- **episodic** — an append-only log of what happened, in time order;
- **semantic** — durable facts keyed for lookup (learning a key updates it);
- **procedural** — learned "how to" procedures (a named sequence of steps);
- **organizational** — knowledge shared across missions/agents.

`retrieve` searches every layer and ranks by importance then recency. Importance
scoring, consolidation, decay, and conflict resolution land on Day 19.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class MemoryType(str, Enum):  # noqa: UP042 - str+Enum for portable values
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    ORGANIZATIONAL = "organizational"


@dataclass
class MemoryItem:
    id: int
    type: MemoryType
    content: str
    key: str | None = None
    tags: tuple[str, ...] = ()
    importance: float = 1.0
    created_at: float = field(default_factory=time.time)

    def matches(self, query: str) -> bool:
        q = query.lower()
        return (
            q in self.content.lower()
            or (self.key is not None and q in self.key.lower())
            or any(q in t.lower() for t in self.tags)
        )


class _Store:
    """Base store: an ordered list of items + substring/tag search."""

    _type = MemoryType.EPISODIC

    def __init__(self) -> None:
        self._items: list[MemoryItem] = []
        self._next_id = 1

    def _add(self, content: str, *, key: str | None = None,
             tags: tuple[str, ...] = (), importance: float = 1.0) -> MemoryItem:
        item = MemoryItem(self._next_id, self._type, content, key, tuple(tags), importance)
        self._next_id += 1
        self._items.append(item)
        return item

    def all(self) -> list[MemoryItem]:
        return list(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def search(self, query: str, limit: int = 5) -> list[MemoryItem]:
        hits = [i for i in self._items if i.matches(query)]
        hits.sort(key=lambda i: (i.importance, i.created_at), reverse=True)
        return hits[:limit]


class WorkingMemory(_Store):
    _type = MemoryType.WORKING

    def __init__(self, capacity: int = 7) -> None:
        super().__init__()
        self.capacity = capacity

    def note(self, content: str, tags: tuple[str, ...] = ()) -> MemoryItem:
        item = self._add(content, tags=tags)
        if len(self._items) > self.capacity:  # keep only the most recent
            self._items = self._items[-self.capacity:]
        return item

    def recent(self, n: int | None = None) -> list[MemoryItem]:
        return list(self._items[-(n or self.capacity):])

    def clear(self) -> None:
        self._items = []


class EpisodicStore(_Store):
    _type = MemoryType.EPISODIC

    def record(self, content: str, tags: tuple[str, ...] = (),
               importance: float = 1.0) -> MemoryItem:
        return self._add(content, tags=tags, importance=importance)

    def recent(self, n: int = 5) -> list[MemoryItem]:
        return list(self._items[-n:])


class SemanticStore(_Store):
    _type = MemoryType.SEMANTIC

    def learn(self, key: str, value: str, importance: float = 1.0) -> MemoryItem:
        for item in self._items:  # keyed -> update in place (no duplicates)
            if item.key == key:
                item.content = value
                item.importance = importance
                return item
        return self._add(value, key=key, importance=importance)

    def get(self, key: str) -> str | None:
        return next((i.content for i in self._items if i.key == key), None)


class ProceduralStore(_Store):
    _type = MemoryType.PROCEDURAL

    def learn(self, name: str, steps: list[str]) -> MemoryItem:
        content = " -> ".join(steps)
        for item in self._items:
            if item.key == name:
                item.content = content
                return item
        return self._add(content, key=name)

    def get(self, name: str) -> str | None:
        return next((i.content for i in self._items if i.key == name), None)


class OrganizationalStore(_Store):
    _type = MemoryType.ORGANIZATIONAL

    def share(self, content: str, tags: tuple[str, ...] = (),
              importance: float = 1.0) -> MemoryItem:
        return self._add(content, tags=tags, importance=importance)


@dataclass
class MultiLayerMemory:
    working: WorkingMemory = field(default_factory=WorkingMemory)
    episodic: EpisodicStore = field(default_factory=EpisodicStore)
    semantic: SemanticStore = field(default_factory=SemanticStore)
    procedural: ProceduralStore = field(default_factory=ProceduralStore)
    organizational: OrganizationalStore = field(default_factory=OrganizationalStore)

    def stores(self) -> list[_Store]:
        return [self.working, self.episodic, self.semantic,
                self.procedural, self.organizational]

    def retrieve(self, query: str, limit: int = 5) -> list[MemoryItem]:
        """Unified retrieval across all layers, ranked by importance then recency."""
        hits: list[MemoryItem] = []
        for store in self.stores():
            hits.extend(store.search(query, limit=limit))
        hits.sort(key=lambda i: (i.importance, i.created_at), reverse=True)
        return hits[:limit]

    def format_context(self, hits: list[MemoryItem]) -> str:
        if not hits:
            return ""
        lines = ["Relevant memory:"]
        for h in hits:
            lines.append(f"[{h.type.value}] {h.content}")
        return "\n".join(lines)

    def snapshot(self) -> dict[str, int]:
        return {s._type.value: len(s) for s in self.stores()}
