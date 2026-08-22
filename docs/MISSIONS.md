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

## Resumable runtime tick (Day 4)

`runtime.py` drives a mission over its DAG; `executor.py` is the pluggable unit
of work.

- **`TaskExecutor`** (`executor.py`) — `async (Task) -> str`. The runtime never
  knows *how* a task runs, only that it returns a result or raises. Tests inject
  a fake; `chat_executor()` is a stopgap single-LLM-call executor, and the full
  tool-using agent plugs in here later without touching the runtime.
- **`MissionRuntime.tick(mission_id)`** — advances the mission by **one DAG
  layer**: reload state, recover any crash-stranded `RUNNING` tasks, run the
  current ready-set (each task `RUNNING` → `DONE`/`FAILED`, persisted
  individually), then re-settle the mission. Returns a `TickResult` (status +
  which tasks ran/failed).
- **`MissionRuntime.run(mission_id)`** — tick until terminal, paused, or no
  progress is possible (`max_ticks` guards against a spin loop).

**Resumability** falls out of persistence: every tick reloads from the repo and
holds no in-memory progress, so a mission can stop after any tick and a *fresh*
runtime resumes from the persisted state. A task left `RUNNING` by a dead worker
is reset to `PENDING` and retried (`_recover`) — single-worker for now; proper
leasing arrives with the scheduler. A failed task strands its dependents, which
`is_blocked` detects, so the mission moves to `FAILED` instead of ticking forever.

## Mission API (Day 5)

`app/api/missions.py` — an `APIRouter` mounted under `/missions`, a thin HTTP
layer over the package. It owns no logic: the repository owns persistence and the
state machine, the runtime owns execution. Dependencies (`get_mission_repo`,
`get_chat_fn`, `get_executor`) are injected so the whole surface runs offline in
tests.

| Method & path | Does |
| --- | --- |
| `POST /missions` | goal → persisted mission with a wired task DAG (201) |
| `GET /missions` | list missions, optional `?status=` filter |
| `GET /missions/{id}` | mission + tasks + progress |
| `GET /missions/{id}/tasks` | just the tasks |
| `POST /missions/{id}/tick` | advance one DAG layer, report what ran/failed |
| `POST /missions/{id}/run` | drive to a terminal/paused state (`?max_ticks=`) |
| `POST /missions/{id}/pause` · `/resume` | guarded status change |

Errors map to status codes: unknown mission → **404**, an illegal state
transition (e.g. pausing a `CREATED` mission) → **409**, a planning/LLM failure
during create → **502**. Mission tables are created at startup via a FastAPI
`lifespan` hook (best-effort, so a cold database never blocks boot).

## Background worker (Day 6)

`app/missions/worker.py` — a `MissionWorker` drives missions forward **without a
client holding a request**, so a mission created via `POST /missions` progresses
on its own. It's the same `MissionRuntime.tick` the API uses; the worker just
calls it on a schedule.

- `poll_once()` — lists non-terminal, non-paused missions (`created`/`active`,
  highest priority first) and ticks each once.
- `run(stop)` — loops `poll_once` every `worker_poll_seconds`, waking early when
  the stop event is set (`asyncio.wait`, so shutdown is prompt and there's no
  version-specific timeout handling). A failing poll is logged and swallowed — a
  transient error never kills the worker.
- `drain(max_rounds)` — ticks until no mission can make progress; used by tests
  and one-shot runs. A round that advances nothing stops the loop (no spin).

It runs as a background `asyncio` task started in the FastAPI **lifespan**, gated
by `worker_enabled` (default on; off in tests, which drive the runtime directly).
On shutdown the task is signalled and cancelled cleanly. Paused and terminal
missions are left untouched; a failed task fails its mission rather than looping.

## Agent scheduler (Day 7)

`app/missions/scheduler.py` — under contention the worker may have many drivable
missions; the scheduler decides which runs first. It's a deterministic scoring
function (pure algorithm, no LLM), so the same input always yields the same
order. `score_mission` sums four weighted terms:

- **priority** — the caller's explicit priority (dominant).
- **deadline urgency** — 0 with no deadline, rising toward 1 as it approaches,
  pinned to 2.0 once **overdue** so an overdue mission can't be starved.
- **age** — a small per-hour boost so a low-priority mission eventually runs
  instead of starving forever.
- **value** — an optional expected-value hint from `mission.meta["value"]`.

`order_missions` sorts by score (ties broken by ascending id, for determinism);
`pick_next` returns the top one. The worker's `_due()` now returns drivable
missions in this scheduled order, so the most important mission is ticked first.
Weights live in a frozen `SchedulerWeights` dataclass and are easy to tune.

## Resource manager (Day 8)

`app/missions/resources.py` — a mission must not burn unbounded money or time.
Each mission can carry a `Budget` (USD, tokens, wall-clock seconds, tool calls,
LLM calls; any dimension `None` = unbounded). `ResourceManager` accumulates
`Usage` via `record(...)` and reports one decision from `evaluate()`:

- **OK** — under the soft threshold, proceed.
- **DOWNGRADE** — crossed the soft threshold (default 80%): keep going but
  cheaper (the model router drops a tier on Day 9).
- **TERMINATE** — a budget is exhausted; stop the mission.

The decision is the **max utilization across all set dimensions**, so the
tightest budget governs. Time is measured from a start clock (`elapsed`), so it's
injectable and deterministic in tests. `budget_from_meta` reads a budget spec off
`mission.meta["budget"]`, so budgets travel with the mission. Enforcing this in
the tick and persisting usage is Day 11.

## Model router (Day 9)

`app/missions/model_router.py` — not every step deserves the strongest (and
priciest) model. The router maps a task's **role** to a preferred model **tier**,
then returns the **highest-quality model that still fits the cost and latency
constraints**:

- `executor` → tier 1 (fast/cheap); `researcher` → tier 2; `analyst` / `planner`
  / `critic` → tier 3 (frontier). Unknown roles use the default tier.
- `route(...)` picks the best model at or below the target tier that satisfies
  `max_usd_per_1k` / `max_latency_ms`; if nothing fits, it **degrades gracefully**
  to the cheapest model rather than failing.
- `route_for(task_type, status)` folds in the resource manager's decision:
  `DOWNGRADE` drops one tier — this is where the budget policy from Day 8 gets
  teeth (tight budget → cheaper model automatically).

The catalog (`fast` / `balanced` / `frontier`) carries **illustrative,
configurable** quality/cost/latency figures meant to be replaced with real
per-deployment numbers — not vendor benchmarks. Selection is deterministic.

## Failure recovery (Day 10)

`app/missions/recovery.py` — when a step fails, retrying forever is wrong and
giving up instantly is wrong. The engine climbs a **bounded ladder**: retry →
alternate tool → cached → replan → escalate → terminate, advancing one rung per
failure. The error *type* sets the starting rung — a `timeout` starts with a
plain retry, a `tool_error` skips straight to the alternate tool, an
`invalid_plan` jumps to replan.

- `RecoveryEngine.decide(ctx)` is the **pure policy** — deterministic, always
  bounded (it reaches `terminate` after `max_attempts`, so it can't loop).
- `execute_with_recovery(primary, engine, handlers)` is the **async runner**:
  `RETRY` re-runs the primary op, other rungs dispatch to fallback handlers, a
  rung with no handler is skipped, and it raises `RecoveryExhausted` if it reaches
  escalate/terminate. It returns the value plus the full **decision trail**, so
  the UI/telemetry can show exactly how a mission recovered.

Tested end to end: a simulated tool timeout recovers on retry, a broken tool
falls back to an alternate, and a doubly-broken tool climbs to the cached result.

## OS subsystems integrated into the tick (Day 11 — Phase B milestone)

`runtime.py` now runs every mission through all four OS subsystems:

- **Scheduler** — already chooses *which mission* ticks first (worker, Day 7); the
  tick then runs that mission's ready-set in topological order.
- **Resources** — each tick builds a `ResourceManager` from the mission's budget
  (`meta["budget"]`) and its **carried-over usage** (`meta["usage"]`), timed from
  `created_at`. Usage accrues as tasks run; when a budget is exhausted the mission
  is set `FAILED` with `meta["termination_reason"] = "budget exhausted"`. Usage is
  persisted every tick, so budgets survive restarts.
- **Router** — each task is routed to a model tier by its **role**
  (`meta["roles"][task_id]`); the chosen model is recorded in `meta["models"]`.
  When the budget policy returns `DOWNGRADE`, the router automatically drops a
  tier (frontier → balanced), and the cheaper model's rate feeds the cost
  estimate — so a tightening budget really does cost less per task.
- **Recovery** — every task runs through `execute_with_recovery`, so a transient
  failure (e.g. a timeout) retries up the ladder before the task is marked
  `FAILED`.

Tested end to end: a transient task failure recovers via retry, an exhausted
`max_llm_calls` budget terminates the mission mid-layer, per-role routing sends an
analyst task to the frontier model, and a near-spent budget downgrades it to the
cheaper one.

**Milestone reached:** a budgeted, scheduled, model-routed, self-healing mission.

## Multi-agent roles + critic/replan (Day 12 — Phase B capstone)

`app/missions/agents.py` — each task carries a **role** (`meta["roles"]`), and
`MultiAgentExecutor` runs it with the matching system prompt: a **Researcher**
gathers facts, an **Analyst** reasons over tradeoffs, an **Executor** just does
the thing. After generating, a **Critic** (`Critic.review`) judges the output and
returns a `Verdict(accepted, score, feedback)`; if it's rejected (or below the
score threshold), the task is regenerated with the critic's feedback — a
**bounded replan loop** (`max_replans`). A malformed judge response never blocks
progress (it defaults to accept).

It's a `TaskExecutor`, so it plugs into the same tick that budgets, routes, and
recovers — the multi-agent step is self-critiquing but otherwise transparent to
the runtime. `build_executor(repo)` selects it when `multi_agent_enabled` is set
(off by default so the live demo stays fast at one LLM call per task); the worker
and the mission endpoints both go through the factory.

**Phase B milestone reached:** a budgeted, scheduled, model-routed, recoverable,
**multi-agent** mission.

## What's coming (per ROADMAP_V2.md)
Phase C — the ML anomaly-detection lifecycle (Days 13–17): dataset generation,
feature engineering, training + experiment tracking, evaluation + registry, and
serving + monitoring. Then the fault-injection benchmark (Day 20) that produces
the real demo numbers.
