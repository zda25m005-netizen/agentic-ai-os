# Memory (v1 + multi-layer v2)

## v1 — episodic + semantic recall

`app/memory/` gave the agent two backends: **episodic** (a durable SQLite log of
past runs, keyword-searchable) and **semantic** (runs embedded into Qdrant, so a
new goal recalls similar past work by meaning). `MemoryManager` unifies them:
`remember(goal, answer)` writes both, `recall(query)` returns semantically
similar runs formatted for a planner prompt.

## Day 18 — multi-layer memory

`app/memory/multilayer.py` adds a cognitively-inspired **five-layer** memory the
mission runtime can use — all in-memory and dependency-free (CI-safe):

| Layer | Role | Key API |
| --- | --- | --- |
| **working** | short-term scratchpad, capacity-bounded (evicts oldest) | `note`, `recent`, `clear` |
| **episodic** | append-only log of what happened, in time order | `record`, `recent` |
| **semantic** | durable facts, keyed (learning a key updates it) | `learn`, `get` |
| **procedural** | learned "how to" procedures (named step sequences) | `learn`, `get` |
| **organizational** | knowledge shared across missions/agents | `share`, `search` |

Every item is a `MemoryItem` (content, optional key, tags, importance,
created_at). `MultiLayerMemory.retrieve(query)` searches **all** layers and ranks
by **importance then recency**; `format_context` renders hits for a prompt and
`snapshot` reports per-layer counts.

Design choices: working memory is bounded so it can't grow without limit;
semantic and procedural are **keyed**, so re-learning a key updates in place
instead of duplicating; organizational is separate so shared knowledge isn't
tangled with a single mission's episodic trace.

### Tested

Working-memory capacity eviction, episodic time order, semantic keyed
update-not-duplicate, procedural step storage, organizational sharing, unified
retrieval spanning all layers ranked by importance, and content/key/tag matching.

## Day 19 — memory dynamics

`app/memory/dynamics.py` — `MemoryDynamics` layers real behavior over the static
stores (all deterministic given an injected `now`):

- **Reinforcement** — `retrieve()` boosts the importance of whatever it returns
  and records the access, so frequently-used memories stay strong.
- **Decay** — `decay(now)` shrinks importance exponentially by time since last
  access and **prunes** items below a threshold. Procedural memory is exempt —
  learned skills persist.
- **Consolidation** — `consolidate(now)` promotes high-importance working-memory
  notes into the episodic log and clears them from the transient scratchpad.
- **Conflict resolution** — `assert_fact(key, value, importance)` stores a
  semantic fact, and on a contradiction keeps the **higher-importance** value
  (ties go to the newer assertion), returning `new / reinforced / overridden /
  kept_existing`.

**Wired into the runtime:** `MissionRuntime` takes an optional `memory`; when set,
each tick records an episodic trace of which tasks ran/failed (failures scored
more salient), so a mission accumulates memory as it executes.

### Tested

Reinforcement on retrieve, exponential decay, prune-but-keep-procedures,
consolidation of important working notes, the full conflict-resolution policy,
and a runtime run recording episodic memory.
