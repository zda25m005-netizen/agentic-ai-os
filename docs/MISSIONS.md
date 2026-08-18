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
`SKIPPED`. The task graph + ready-set computation lands next (Day 3), then the
resumable runtime tick (Day 4).

## What's coming (per ROADMAP_V2.md)
Goal Interpreter + Mission Planner (Day 2) → task DAG (Day 3) → resumable runtime
tick (Day 4) → Mission API (Day 5) → background worker (Day 6). Then the OS layer:
scheduler, resource budgets, model router, and failure recovery.
