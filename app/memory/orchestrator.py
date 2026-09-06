"""Canonical memory orchestration — the single entry point for memory operations.

Wraps the durable rich-record store (records/store) and reuses the in-memory
`multilayer`/`dynamics` engine for working-context scratchpad + decay. Exposes a
stable interface (remember / retrieve / update / forget / restore / reinforce /
build_context / resolve / stats) so agents depend on this, not on individual stores.

Policy: DETERMINISTIC by default (safe fallback). An LLM/RL policy can later plug in
behind `apply_memory_policy` without changing callers.

Guarantees encoded + tested here:
- No blind overwrite: a new value for an existing key only supersedes when its
  confidence is >= the stored one (an explicit correction); otherwise both are kept.
- History preserved: superseded/forgotten records are retained (soft status), so
  temporal reasoning can still see them.
- Retrieval is budgeted: `build_context` never returns more than the token budget.
- Advisory context: retrieved memory personalizes; it is returned as clearly-labelled
  context and never as a hard constraint (the current query stays authoritative).
"""

from __future__ import annotations

import math
import time

from app.memory import store
from app.memory.records import MemoryRecord


def _tokens(text: str) -> int:
    return max(1, len(text) // 4)  # ~4 chars/token approximation


# Process-wide orchestrator (installed by the app at startup, cleared on shutdown).
# When None, the agent falls back to the legacy MemoryManager path — preserving all
# existing behavior and tests, which never install one.
_default: MemoryOrchestrator | None = None


def get_orchestrator() -> MemoryOrchestrator | None:
    return _default


def set_orchestrator(orch: MemoryOrchestrator | None) -> None:
    global _default
    _default = orch


class MemoryOrchestrator:
    def __init__(self, owner: str = "me", decay_rate: float = 0.05):
        self.owner = owner
        self.decay_rate = decay_rate

    # --- write ---------------------------------------------------------------
    def remember(
        self,
        content: str,
        *,
        memory_type: str = "semantic",
        key: str | None = None,
        tags: list[str] | None = None,
        source: str = "agent",
        confidence: float = 0.7,
        importance: float = 1.0,
        mission_id: int | None = None,
        provenance: str | None = None,
        pinned: bool = False,
    ) -> dict:
        """Deterministic ADD / UPDATE(supersede) / NOOP(reinforce) resolution."""
        rec = MemoryRecord(
            memory_type=memory_type,
            content=content,
            key=key,
            tags=tags or [],
            source=source,
            confidence=confidence,
            importance=importance,
            mission_id=mission_id,
            provenance=provenance,
            owner=self.owner,
            pinned=pinned,
            valid_from=time.time(),
        )
        if key:
            existing = store.find_all_by_key(self.owner, memory_type, key)
            if existing:
                exact = next((e for e in existing if e.content.strip() == content.strip()), None)
                if exact:
                    exact.importance += 0.5
                    exact.access_count += 1
                    exact.status = "reinforced"
                    exact.updated_at = time.time()
                    store.put(exact)
                    return {
                        "operation": "NOOP",
                        "record": exact,
                        "rationale": "identical value reinforced",
                    }
                if confidence >= max(e.confidence for e in existing):
                    for e in existing:  # correction supersedes ALL prior values of this key
                        e.status = "superseded"
                        e.valid_until = time.time()
                        e.updated_at = time.time()
                        store.put(e)  # kept for history, never deleted
                    rec.supersedes_id = existing[0].id
                    store.put(rec)
                    return {
                        "operation": "UPDATE",
                        "record": rec,
                        "superseded": [e.id for e in existing],
                        "rationale": "higher/equal-confidence correction supersedes prior value(s)",
                    }
                # lower-confidence differing value: keep as an ADDITIVE note (don't
                # compete for the single-value key, don't overwrite the existing one)
                rec.key = None
                store.put(rec)
                return {
                    "operation": "ADD",
                    "record": rec,
                    "rationale": "additional lower-confidence value kept alongside existing",
                }
        store.put(rec)
        return {"operation": "ADD", "record": rec, "rationale": "new memory"}

    # --- read ----------------------------------------------------------------
    def _score(self, r: MemoryRecord, query: str, now: float) -> float:
        q = query.lower().strip()
        hay = f"{r.content} {r.key or ''} {' '.join(r.tags)}".lower()
        match = (
            1.0
            if (q and q in hay)
            else (0.5 if q and any(w in hay for w in q.split() if len(w) > 3) else 0.0)
        )
        hours = max(0.0, (now - (r.last_accessed_at or r.created_at)) / 3600.0)
        recency = math.exp(-self.decay_rate * hours)
        pin = 0.5 if r.pinned else 0.0
        return r.importance * recency + match + 0.2 * r.confidence + pin

    def retrieve(
        self,
        query: str,
        *,
        limit: int = 8,
        token_budget: int | None = None,
        layer: str | None = None,
    ) -> tuple[list[MemoryRecord], int]:
        now = time.time()
        candidates = [r for r in store.query(self.owner, layer=layer) if r.is_current(now)]
        ranked = sorted(candidates, key=lambda r: self._score(r, query, now), reverse=True)
        out: list[MemoryRecord] = []
        used = 0
        for r in ranked:
            if len(out) >= limit:
                break
            t = _tokens(r.content)
            if token_budget is not None and used + t > token_budget:
                continue  # budget guard — retrieval can never overflow the budget
            out.append(r)
            used += t
        for r in out:  # reinforce accessed
            r.access_count += 1
            r.last_accessed_at = now
            store.put(r)
        return out, used

    def build_context(self, query: str, *, token_budget: int = 600) -> dict:
        """Advisory context only — personalizes, never a hard constraint."""
        recs, tokens = self.retrieve(query, token_budget=token_budget)
        if not recs:
            return {"context": "", "records": [], "tokens": 0}
        lines = ["Relevant remembered context (advisory — the current request takes precedence):"]
        lines += [f"- [{r.memory_type}] {r.content}" for r in recs]
        return {"context": "\n".join(lines), "records": recs, "tokens": tokens}

    # --- lifecycle -----------------------------------------------------------
    def update(self, mem_id: str, **fields) -> MemoryRecord | None:
        r = store.get(mem_id, self.owner)
        if not r:
            return None
        for k, v in fields.items():
            if hasattr(r, k) and v is not None:
                setattr(r, k, v)
        r.status = "updated"
        r.updated_at = time.time()
        return store.put(r)

    def forget(self, mem_id: str, *, hard: bool = False) -> bool:
        if hard:
            return store.delete_hard(mem_id, self.owner)  # user-requested erasure
        r = store.get(mem_id, self.owner)
        if not r:
            return False
        r.status = "archived"
        r.updated_at = time.time()
        store.put(r)
        return True

    def restore(self, mem_id: str) -> MemoryRecord | None:
        r = store.get(mem_id, self.owner)
        if not r:
            return None
        r.status = "active"
        r.updated_at = time.time()
        return store.put(r)

    def reinforce(self, mem_id: str, boost: float = 0.5) -> MemoryRecord | None:
        r = store.get(mem_id, self.owner)
        if not r:
            return None
        r.importance += boost
        r.access_count += 1
        r.last_accessed_at = time.time()
        r.status = "reinforced"
        return store.put(r)

    def supersede(self, old_id: str, content: str, **meta) -> MemoryRecord | None:
        """Explicitly supersede a record by id (used by the lifecycle resolver).

        The old record is retained as history; a new active record links back to it.
        """
        old = store.get(old_id, self.owner)
        if not old:
            return None
        old.status = "superseded"
        old.valid_until = time.time()
        old.updated_at = time.time()
        store.put(old)
        rec = MemoryRecord(
            memory_type=old.memory_type,
            content=content,
            key=old.key,
            source=meta.get("source", "agent"),
            confidence=meta.get("confidence", 0.8),
            importance=meta.get("importance", 1.0),
            owner=self.owner,
            supersedes_id=old.id,
            provenance=meta.get("provenance"),
            valid_from=time.time(),
        )
        return store.put(rec)

    # --- introspection -------------------------------------------------------
    def stats(self) -> dict:
        allr = store.query(self.owner, include_archived=True)
        current = [r for r in allr if r.is_current()]
        layers = {
            lyr: sum(1 for r in current if r.memory_type == lyr)
            for lyr in ("working", "episodic", "semantic", "procedural", "organizational")
        }
        statuses: dict[str, int] = {}
        for r in allr:
            statuses[r.status] = statuses.get(r.status, 0) + 1
        return {
            "total": len(allr),
            "current": len(current),
            "layers": layers,
            "statuses": statuses,
            "superseded": statuses.get("superseded", 0),
        }
