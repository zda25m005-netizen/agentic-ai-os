# Agentic Memory Engine

Upgrade of the memory subsystem toward a hierarchical + agentic memory engine.
Delivered **incrementally**; this document marks what is real today vs. planned.
No paper benchmarks are reproduced or claimed.

## Status

| Area | Status |
|---|---|
| Canonical `MemoryOrchestrator` (single entry point) | **Implemented** |
| Rich memory object model + lifecycle (provenance, temporal validity, status) | **Implemented** |
| Durable, owner-isolated record store (SQLite) | **Implemented** |
| Deterministic resolver: ADD / UPDATE(supersede) / NOOP(reinforce) + additive keep-both | **Implemented** |
| Retrieval ranking + token-budget guard + advisory context | **Implemented** |
| `/memory` HTTP API + Memory UI on real records (no more sample data) | **Implemented** |
| Eval harness (local LongMemEval-style fixtures) + metrics + ablation runner | **Implemented** |
| `MEMORY_POLICY_MODE` config (`deterministic` default) | **Implemented** |
| Mem0-style lifecycle (extract candidates → retrieve-similar → resolve) wired into `finalize_node` | **Implemented** (config D) |
| MemGPT-style context controller (budget/prioritize/evict) wired into `planner_node` | **Implemented** (config D) |
| Optional LLM candidate extraction (`MEMORY_POLICY_MODE=llm`, deterministic fallback) | **Implemented** |
| Graph memory (owner-scoped entity/relationship, reuse `app/graph` Neo4j client) | **Implemented** (config E) |
| LLM / RL (GRPO) memory policy + training + RL env | **Planned / Experimental** (config F) |

## Architecture (implemented core)

```mermaid
flowchart TD
    A[Agent / API] --> O[MemoryOrchestrator]
    O -->|remember| R[Resolver: ADD/UPDATE/NOOP/additive]
    O -->|retrieve| K[Rank + token-budget guard]
    O -->|build_context| C[Advisory context — current request wins]
    R --> S[(Durable store: rich MemoryRecord, owner-isolated)]
    K --> S
    S --- H[Superseded/archived kept for temporal reasoning]
    subgraph existing[Preserved existing modules]
      MM[multilayer 5-layer scratchpad] --- DY[dynamics decay/consolidation]
      EP[episodic SQLite/Postgres] --- SE[semantic Qdrant]
    end
    O -.wraps.-> existing
```

## Agent wiring (config D)

The Mem0 lifecycle and MemGPT context controller are wired into the **real LangGraph
execution path**, not exposed as standalone classes:

```mermaid
flowchart LR
    P[planner_node] -->|ContextController.build| O[(MemoryOrchestrator)]
    O -->|budgeted advisory context| P
    P --> E[executor] --> CR[critic] --> F[finalize_node]
    F -->|episodic run log| O
    F -->|extract_candidates → resolve_and_ingest| O
```

- **`planner_node`** — when an orchestrator is installed, a `ContextController`
  (`app/memory/context.py`) retrieves + budgets memory into an advisory block injected
  into the plan prompt. The goal is never overridden; over-long items are clipped (evicted).
- **`finalize_node`** — logs the run episodically, then runs the Mem0 lifecycle
  (`app/memory/lifecycle.py`): extract candidate facts from goal+answer, retrieve similar
  memories, and resolve to ADD / UPDATE(supersede) / NOOP(reinforce).
- **Safe fallback.** When no orchestrator is installed (`MEMORY_POLICY_MODE=off`, and every
  existing test), both nodes fall back to the legacy `MemoryManager` path — so all prior
  behavior and tests are preserved.

## Graph memory (config E)

An optional entity/relationship layer (`app/memory/graph_memory.py`, Mem0g-style) that
reuses the existing `app/graph` stack — the same LLM extraction (`extract_graph`) and the
same Neo4j client (`run_query` / `verify_connectivity`). Durable facts are projected into
an **owner-scoped** namespace (`:MemEntity` / `:MEM_RELATION`, distinct from the document
RAG graph's `:Entity` / `:RELATION`), and recall traverses only the current owner's subgraph.

- **`finalize_node`** — after the Mem0 lifecycle, also calls `GraphMemory.ingest_text(...)`
  to MERGE the run's entities/relations (idempotent, owner-scoped).
- **`planner_node`** — calls `GraphMemory.related(goal)` and appends the returned triples as
  a second, clearly-labelled *advisory* block alongside the MemGPT context.
- **Optional + graceful.** Gated by `MEMORY_GRAPH_ENABLED` (default **off**) and only active
  when a live Neo4j answers `verify_connectivity`. Otherwise every call is a safe no-op —
  ingest returns zeros, recall returns empty — so the agent, the `/memory/graph` endpoint,
  and the whole test suite run unchanged without a graph database. Unit-tested end-to-end
  with a fake driver (`tests/test_graph_memory.py`); no live Neo4j required in CI.
- **Owner isolation.** Every MATCH/MERGE filters on `$owner`; one owner's graph is never
  traversed for another (tested).

## Guarantees (encoded + tested)

- **Current request is authoritative.** `build_context` returns memory clearly labelled
  *advisory — the current request takes precedence*; retrieval never emits hard constraints.
- **No blind overwrite.** A differing value only supersedes an existing keyed fact when its
  confidence ≥ the stored one (an explicit correction). Lower-confidence differing values are
  kept as additive notes.
- **History preserved.** Superseded/forgotten records move to `superseded`/`archived` and stay
  queryable — never hard-deleted (except explicit user erasure via `forget(hard=True)`).
- **Retrieval cannot overflow the budget.** `retrieve(token_budget=…)` enforces the cap.
- **Owner isolation.** Every record carries an `owner`; the store filters by it — no cross-user leakage.

## Configuration

- `MEMORY_BACKEND` — `sqlite` (default) | `postgres` (existing episodic backend).
- `MEMORY_POLICY_MODE` — `deterministic` (default, always works) | `llm` | `rl` (experimental, gated).
- `MEMORY_GRAPH_ENABLED` — `false` (default) | `true`. When true and a live Neo4j answers,
  graph memory (config E) ingests + recalls owner-scoped triples; otherwise it is a no-op.
- Neo4j (`NEO4J_*`) and Qdrant (`QDRANT_URL`) remain optional; graph memory reuses the existing Neo4j client.

## Evaluation

`python -c "from app.memory.eval.ablation import run; import json; print(json.dumps(run(), default=str, indent=2))"`

Runs the local fixtures for **A (no memory)**, **C (orchestrator)**, and **D (orchestrator +
Mem0 lifecycle + MemGPT context controller)**. B requires a live Qdrant and E requires a live
Neo4j, so both are skipped offline (E's module + wiring exist and are unit-tested with a fake
driver); F is unbuilt. No numbers are reported for configs that were not actually run. Metrics:
precision, recall, stale-leak, irrelevant-leak, retrieved tokens.

On the local fixtures, config D improves precision over C (0.708 → 0.875) and reduces
irrelevant-leak (3 → 1) at recall 1.0 with zero stale leaks. These are small hand-written
fixtures, **not** the published LongMemEval benchmark — no paper numbers are claimed.

## Files

- `app/memory/records.py`, `app/memory/store.py`, `app/memory/orchestrator.py`
- `app/memory/lifecycle.py` (Mem0), `app/memory/context.py` (MemGPT),
  `app/memory/graph_memory.py` (graph memory) — wired into `app/agents/planner.py`
  and `app/agents/graph.py`
- `app/api/memory.py` (router incl. `/memory/graph`), registered in `app/api/main.py`
  (orchestrator installed in lifespan)
- `app/memory/eval/{dataset,metrics,harness,ablation}.py`
- `frontend/app/lib/memoryApi.ts` (now calls `/memory`)
- `tests/test_memory_orchestrator.py`, `tests/test_memory_eval.py`,
  `tests/test_memory_lifecycle.py`, `tests/test_memory_context.py`,
  `tests/test_memory_agent_wiring.py`, `tests/test_graph_memory.py`
