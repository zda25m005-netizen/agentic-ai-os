# Agentic AI OS v2 — Autonomous Long-Horizon Agent Runtime

**Positioning:** *"The Runtime for Autonomous AI Agents — plan, execute, remember,
recover, and evaluate long-running autonomous workflows."*

v1 gave us a bounded agent (Planner → Executor → Critic → Answer). v2 turns it
into a **mission runtime** that pursues objectives across sessions, schedules
agents under resource budgets, recovers from failure, remembers across missions,
and is driven from a **SaaS control plane**. Built on the v1 repo.

30 build days, daily commits (aim 6–10/day). Every feature ships with tests.
**Honesty rule from v1 stays:** state limits, never inflate numbers.

Two products:
```
                 AGENTIC AI OS
        ┌─────────────┴─────────────┐
   AI/Agent Runtime           Web Control Plane
   (missions, scheduler,      (dashboard, mission graph,
    memory, recovery,          activity stream, evidence,
    policies, eval)            eval, security, API)
```

---

## Phase A — Mission Runtime Core (Days 1–6)

The shift from "answer a task" to "maintain a mission until the objective is met."

### Day 1 — Mission domain model + persistence
- `app/missions/models.py`: `Mission` (objective, status, deadline, priority,
  created/updated), `Subgoal`/`Task` (mission_id, description, status, deps, result).
- State machine: `CREATED → ACTIVE → PAUSED → COMPLETED | FAILED`.
- Async SQLAlchemy store (reuse `app/db`) + repository CRUD.
- Tests: state transitions, persistence roundtrip.
- **Done when:** you can create a mission, persist it, and move it through states.

### Day 2 — Goal Interpreter + Mission Planner
- `goal_interpreter.py`: user goal → structured `Objective` (success criteria,
  constraints, deadline, notify-conditions). LLM-backed, injectable, tested with fakes.
- `mission_planner.py`: objective → ordered **subgoals** (a DAG, not a flat list).
- Tests: interpreter parses a monitoring goal; planner emits a valid DAG.

### Day 3 — Task graph (DAG) + dependency resolution
- `task_graph.py`: nodes + typed edges, topological order, "ready tasks" (deps met).
- Cycle detection; per-task status; persistence.
- Tests: ready-set computation, topo order, cycle rejection.

### Day 4 — Mission runtime loop (resumable)
- `runtime.py`: a **tick** — pick ready tasks, run them (via the v1 agent graph),
  update the graph, persist. Stop anytime, resume later (all state in the DB).
- Replan hook when a task fails or evidence contradicts.
- Tests: a mission advances across two separate `tick()` calls (resumability).

### Day 5 — Mission API
- `POST /missions`, `GET /missions`, `GET /missions/:id`,
  `POST /missions/:id/pause|resume`, `GET /missions/:id/tasks`,
  `GET /missions/:id/trajectory`.
- Pydantic schemas; tests with fakes.

### Day 6 — Background mission worker
- A loop/worker that `tick()`s active missions on a schedule (reuse scheduled-tasks
  pattern or a simple asyncio loop; Redis-backed queue lands in Phase D).
- Wire task execution to the v1 executor/tools. Integration test end-to-end (offline).
- **Milestone:** a mission runs, pauses, resumes, and completes across ticks.

---

## Phase B — Scheduler, Resources, Router, Recovery (Days 7–12)

The "OS" layer — real systems/ML engineering, not just LLM calls.

### Day 7 — Agent Scheduler
- `scheduler.py`: score-and-order ready tasks by **priority, deadline, cost,
  dependencies, expected value** (weighted function + topological constraint).
  Deterministic algorithm (not an LLM) → testable.
- Tests: given competing missions, the right one runs first.

### Day 8 — Resource Manager
- `resources.py`: per-task/mission **budgets** — tokens, USD cost, wall-time,
  tool-calls, API calls. Track consumption; enforce; emit "budget exceeded".
- Hooks: on threshold → downgrade model / terminate task.
- Tests: budget accounting + enforcement.

### Day 9 — Model Router
- `router.py`: task-type → model tier (cheap/code/reasoning/summarize), optimizing
  **quality subject to cost/latency/token limits**. Config of tiers in settings.
- Tests: routing picks the expected tier per task class + respects budget.

### Day 10 — Failure Recovery Engine
- `recovery.py`: decision policy on failure — **retry → alternative tool →
  cached result → replan → escalate to human → terminate**. Bounded.
- Wrap tool/step execution so any failure flows through it.
- Tests: simulate tool timeout → falls back → recovers (deterministic).

### Day 11 — Integrate scheduler + resources + router + recovery
- Thread all four through the mission runtime tick.
- Integration tests (offline): a budgeted, scheduled, recoverable tick.

### Day 12 — Multi-agent roles + Judge + replan loop
- Roles: **Researcher / Analyst / Executor** (specialized prompts + tool sets),
  coordinated by the scheduler; **Critic/Judge** gates mission success → replan or finish.
- Tests: role selection + the replan branch.
- **Milestone:** a mission with budgets, model routing, and failure recovery.

---

## Phase C — Memory System + Evaluation + Self-Improvement (Days 13–18)

### Day 13 — Memory interfaces: working + episodic
- `app/memory2/`: a `Memory` protocol; **working** (current mission scratch) +
  **episodic** (events: what happened) stores. Build on v1 episodic.
- Tests.

### Day 14 — Semantic + procedural + organizational memory
- **Semantic** (facts I know — vectors), **procedural** (how-to / successful
  strategies), **organizational** (what the whole system learned). Tests.

### Day 15 — Retrieval + importance scoring + consolidation
- Unified retrieval across memory types; **importance scoring**; **consolidation**
  (summarize episodics into semantic/organizational). Tests.

### Day 16 — Decay + conflict resolution + wire-in
- Time/importance **decay**; **conflict resolution** (contradictory memories →
  keep higher-confidence/newer). Wire memory into the mission runtime. Tests.

### Day 17 — AgentBench-style evaluation
- `eval/agentbench/`: a **task generator** across categories (easy/medium/hard/
  adversarial/long-horizon/tool-failure/memory-dependent/ambiguous). Start at
  hundreds of tasks (scale later — state the number).
- Metrics: task success, planning success, tool selection, **recovery rate**,
  memory retrieval, cost, latency, token efficiency, hallucination, safety,
  human-intervention rate. Runner + report. Tests on the harness.

### Day 18 — Self-improving policy engine
- `policies.py`: a **policy** = an ordered strategy (e.g. `search → summarize →
  answer`). On failure, analyze → propose a **candidate policy** → **A/B evaluate**
  on the bench → **promote if better**. Deterministic evaluation; the "learning"
  is search over strategies, not RL.
- Tests: a better candidate gets promoted; a worse one doesn't.
- **Milestone:** the runtime measurably improves a strategy on the bench.

---

## Phase D — Real-time Backend + Control-Plane Foundations (Days 19–24)

### Day 19 — Redis + distributed workers
- Redis for the mission/task queue + shared state; a worker pool that pulls tasks.
- `docker-compose` + Helm updated. Tests (fakeredis / in-memory).

### Day 20 — Real-time event stream (SSE/WebSocket)
- Emit agent activity events (task started, tool called, anomaly, replan) over
  **SSE** (simplest) or WebSocket. `GET /missions/:id/stream`.
- Tests: events published on a tick.

### Day 21 — Public API v1 + OpenAPI + playground
- Finalize `/api/v1/missions...` surface, versioned; OpenAPI schema; a simple
  request playground page. Tests.

### Day 22 — Control-plane scaffold (Next.js + shadcn/ui, dark premium)
- New `control-plane/` (or extend `frontend/`): Tailwind + shadcn/ui + layout,
  sidebar (Overview, Missions, Agents, Memory, Evidence, Evaluations, Security,
  Observability), dark/premium theme (Linear/Vercel/Datadog vibe).

### Day 23 — Dashboard + Active Missions (live)
- Overview cards + **Active Missions** list with progress bars, polling/SSE.

### Day 24 — Mission page: interactive task graph
- **React Flow** task graph; click a node → drawer with agent, model, tool calls,
  latency, tokens, cost, confidence, evidence.

---

## Phase E — Control-Plane Pages + Demo + Deploy (Days 25–30)

### Day 25 — Live activity stream + Agent detail
- Real-time **activity stream** page (SSE); **Agent detail** (model, current task,
  tools, resource usage, memories, confidence).

### Day 26 — Memory Explorer + Evidence Graph
- **Memory Explorer** (working/episodic/semantic/procedural, searchable);
  **Evidence Graph** (React Flow over GraphRAG: entity → source → evidence → confidence).

### Day 27 — Evaluation + Observability + Security Center
- **Eval dashboard** (Recharts: success/planning/recovery over versions);
  **Observability** (system health, LLM cost/tokens — reuse Prometheus);
  **Security Center** (prompt-injection blocked, SSRF, path-traversal, sandbox — surface v1 guards + a live event log).

### Day 28 — Public landing + Live Demo sandbox
- Hero + live mission visualization; **"Try Live Demo"** with preset missions
  (Financial Investigation, Research, Doc Intelligence, **Failure Recovery Demo**)
  running in a safe sandbox — no config for the recruiter.

### Day 29 — Architecture page + API playground + polish
- Beautiful architecture page; interactive API playground; restrained Framer
  Motion; information hierarchy pass.

### Day 30 — Integration, docs, deploy, release
- Full e2e smoke; README/positioning rewrite ("The Runtime for Autonomous AI
  Agents"); architecture + reference docs; compose + Helm updated; demo video;
  **tag v2.0.0** + release notes.

---

## Daily rhythm
1. `git pull`, re-read yesterday's last commit.
2. Build the day's core (backend feature or 1–2 UI pages), tests last, CI green.
3. 6–10 real commits (schema → logic → integration → tests → docs). No padding.
4. If a day overflows, split it — real small commits beat faked ones.

## If you fall behind (scope-cut order)
Cut depth here first, in this order: 10k→hundreds of bench tasks; policy engine to
a single documented A/B; organizational memory to a stub; WebSocket → SSE only;
fewer control-plane pages (keep Dashboard, Mission graph, Activity stream, Eval).
The **mission runtime + scheduler + recovery + control-plane dashboard** is the
irreducible core that proves the thesis.

## Positioning line for the README/landing
> **Agentic AI OS** — The Runtime for Autonomous AI Agents. A production-oriented
> runtime for planning, executing, remembering, recovering, and evaluating
> long-running autonomous workflows.
