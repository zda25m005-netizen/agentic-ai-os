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

### What's coming (Day 19)

Memory dynamics: unified retrieval with **importance scoring**, **consolidation**
(working → long-term), **decay**, and **conflict resolution**, wired into the
runtime tick so missions accumulate and reuse memory.
