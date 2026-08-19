# Mission Runtime (v2)

The v2 core: long-horizon, **resumable** objectives. Where v1 answered a bounded
task, v2 maintains a **Mission** until its objective is achieved — across
sessions, budgets, and failures.

## Domain model

- **Mission** — an objective + status + priority + deadline + metadata
  (e.g. notify-conditions). Persisted, so it can stop today and continue tomorrow.
- **Task** — a unit of work in a mission, with `depends_on` edges (a DAG),
  a status, and a result.

## Mission state machine

```
CREATED ──▶ ACTIVE ──▶ COMPLETED
   │          │  ▲
   │          ▼  │
   │        PAUSED
   ▼          │
 FAILED ◀─────┘        (COMPLETED / FAILED are terminal)
```

Only legal transitions are allowed, enforced in exactly one place
(`MissionRepository.set_status` → `state.transition`). A terminal mission can't
be revived; a paused mission can't jump to completed. This is the safety rail for
autonomy.

## Persistence

`app/missions/` — `state.py` (enums + transitions), `models.py` (ORM +
`Mission`/`Task` dataclasses), `repository.py` (async CRUD, all transitions
guarded). Async SQLAlchemy; tests run on in-memory SQLite.

## Task status

`PENDING` (deps unmet) → `READY` (deps met) → `RUNNING` → `DONE` | `FAILED` |
`SKIPPED`.

## From goal to mission (Day 2)

A raw goal becomes a persisted mission with a wired task DAG in three steps:

1. **Goal Interpreter** (`goal_interpreter.py`) — goal → `Objective`
   (summary, success criteria, constraints, **notify conditions**, deadline,
   **horizon**: one_shot / monitoring / investigation). Defensive JSON parse with
   a one-shot fallback.
2. **Mission Planner** (`mission_planner.py`) — objective → an acyclic list of
   `SubgoalSpec` (description, `depends_on` indices, role: researcher / analyst /
   executor). Sanitization keeps only backward deps, so the graph is always
   acyclic; a bad response falls back to research → analyze → report.
3. **Builder** (`builder.py`) — `build_mission(repo, goal)` interprets, plans,
   creates the mission, and materializes each subgoal as a Task, translating
   subgoal **indices into real task ids** so persisted `depends_on` edges point at
   actual tasks.

Example: *"monitor Company X for 30 days, notify me only on strong evidence"* →
Objective(horizon=monitoring, deadline=30, notify=["strong evidence"]) → tasks
[baseline] → [detect anomalies] → [report].

## Task DAG engine (Day 3)

Two pure modules — no DB, no I/O — give the runtime one source of truth for
"what can run now" and "are we stuck":

- **`toposort.py`** — `topological_order(tasks)` (Kahn's algorithm, ascending-id
  tie-break so it's deterministic) and `has_cycle(tasks)`. A cycle is a **runtime
  guard**: the planner only emits backward deps, but a persisted edit could
  introduce one, so the runtime refuses to execute a cyclic graph instead of
  looping forever. Dangling deps (pointing at a missing task) are ignored.
- **`task_graph.py`** — the execution view:
  - `ready_tasks(tasks)` — PENDING/READY tasks whose **every** dependency is
    `DONE` (or `SKIPPED`), in id order. A `FAILED` or missing dep leaves the
    dependent unready, so work never runs on incomplete inputs.
  - `is_complete(tasks)` — all tasks settled (`DONE`/`SKIPPED`).
  - `is_blocked(tasks)` — not complete, nothing `RUNNING`, and nothing ready:
    the mission is stuck (usually a failed dep stranding its dependents). The
    runtime uses this to **fail** a mission rather than tick forever.
  - `progress(tasks)` → `(settled, total)` for the UI and telemetry.

The tick loop (Day 4) is then trivial: while not complete and not blocked, run
the ready-set, persist statuses, repeat.

## What's coming (per ROADMAP_V2.md)
Resumable runtime tick (Day 4) → Mission API (Day 5) → background worker
(Day 6). Then the OS layer: scheduler, resource budgets, model router, and
failure recovery.
