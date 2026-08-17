# Agentic AI OS v2 — Autonomous Long-Horizon Agent Runtime

**Positioning:** *"The Runtime for Autonomous AI Agents — plan, execute, remember,
recover, and evaluate long-running autonomous workflows."*

Built on the v1 repo. 30 build days, daily commits (6–10/day). Every feature ships
with tests and CI green.

## Design principles (read this before Day 1)

1. **Depth over breadth.** We build **8 deep capabilities**, not 50 shallow
   features. No "100+ features / 20 tools" README padding — that impresses no one.
2. **Real numbers only.** Every metric on the demo/landing (success, recovery
   rate, safety, avg cost, avg latency) is produced by the **benchmark run**
   (Day 20 + Day 30), never invented. If a number is bad, we show it and explain.
3. **The ML component is a real ML project**, not decoration. The anomaly detector
   gets the full lifecycle: **dataset generation → feature engineering → training →
   evaluation → experiment tracking → serving → monitoring**.
4. **Tests every day.** If it's not tested, it doesn't count as done.

## The 8 capabilities (what we make exceptional)

```
1. Long-horizon autonomous missions      (Phase A)
2. Intelligent scheduling + resources     (Phase B)
3. Fault recovery + dynamic replanning    (Phase B)
4. ML anomaly detection (full lifecycle)  (Phase C)
5. Persistent multi-layer memory          (Phase D)
6. Evaluation + fault-injection benchmark (Phase D)  → real numbers
7. Self-improving agent policies          (Phase D)
8. Production-grade control plane          (Phase E–F)
   (+ evidence-based GraphRAG & security carried from v1, deepened)
```

---

## Phase A — Mission Runtime Core (Days 1–6)

*The shift from "answer a task" to "maintain a mission until the objective is met."*

- **Day 1** — Mission + Task domain model, state machine
  (`CREATED→ACTIVE→PAUSED→COMPLETED|FAILED`), async store, tests.
- **Day 2** — Goal Interpreter (goal → structured objective + success criteria +
  notify-conditions) + Mission Planner (objective → subgoal DAG).
- **Day 3** — Task graph (DAG), dependency resolution, ready-set, cycle detection.
- **Day 4** — Mission runtime **tick** — resumable across sessions (stop today,
  continue tomorrow); replan hook. Test: advances across two `tick()`s.
- **Day 5** — Mission API (create / get / pause / resume / tasks / trajectory).
- **Day 6** — Background mission worker; wire task execution to the v1 agent graph.
  **Milestone:** a mission runs, pauses, resumes, completes.

## Phase B — Scheduler, Resources, Router, Recovery (Days 7–12)

*The "OS" layer — real systems engineering, algorithms not LLM calls.*

- **Day 7** — Agent Scheduler (priority · deadline · cost · deps · expected value;
  deterministic scoring). Test: right mission runs first.
- **Day 8** — Resource Manager (token / USD / time / tool-call / API budgets;
  enforce; on-threshold downgrade or terminate).
- **Day 9** — Model Router (task-type → model tier, maximize quality s.t.
  cost/latency/token limits).
- **Day 10** — Failure Recovery Engine (retry → alt tool → cached → replan →
  escalate → terminate; bounded). Test: simulated tool timeout recovers.
- **Day 11** — Integrate scheduler + resources + router + recovery into the tick.
- **Day 12** — Multi-agent roles (Researcher / Analyst / Executor) + Critic/Judge
  + replan loop. **Milestone:** budgeted, scheduled, recoverable multi-agent mission.

## Phase C — ML Anomaly Detection: FULL LIFECYCLE (Days 13–17)

*A real ML project inside the OS — this is the "substantial ML" the reviewer wants.*

- **Day 13 — Dataset generation.** Synthetic financial-transaction generator with
  **injected, labeled anomalies** (amount spikes, velocity, duplicate, off-hours,
  geo-mismatch). Deterministic seed; train/val/test splits; a dataset card.
  `ml/anomaly/data.py`. Tests: label balance, splits, reproducibility.
- **Day 14 — Feature engineering.** Temporal + rolling-window stats, ratios,
  entity aggregates, encodings — a reusable **feature pipeline** (fit on train
  only, no leakage). Tests: pipeline determinism, no train/test leakage.
- **Day 15 — Model training + experiment tracking.** Train + compare **≥3 models**
  (IsolationForest, GradientBoosting/XGBoost, a small autoencoder), logged to
  **MLflow** (params, metrics, artifacts). `ml/anomaly/train.py`. CI-safe smoke.
- **Day 16 — Evaluation + model registry.** **PR-AUC, precision/recall, F1** on
  held-out, threshold selection, calibration; pick the winner; save a **versioned
  model artifact**. Honest results table. Tests on the scorers.
- **Day 17 — Serving + monitoring + integration.** Versioned **scorer** + endpoint;
  **monitoring** — input **drift** (PSI/KS), score-distribution, live
  precision/recall → Prometheus/Grafana panels. Wire into the mission as the
  "anomaly detected → evidence" step. **Milestone:** a real, served, monitored ML
  model driving agent decisions.

## Phase D — Memory, Benchmark, Self-Improvement (Days 18–21)

- **Day 18 — Multi-layer memory.** working / episodic / semantic / procedural /
  organizational stores (build on v1). Tests.
- **Day 19 — Memory dynamics.** unified retrieval + **importance scoring** +
  **consolidation** + **decay** + **conflict resolution**; wire into the runtime.
- **Day 20 — Fault-injection benchmark (the numbers).** Task generator across
  categories (easy/medium/hard/adversarial/long-horizon/**tool-failure**/
  memory-dependent/ambiguous) + metrics (task success, planning, tool selection,
  **recovery rate**, memory retrieval, cost, latency, hallucination, **safety**,
  human-intervention). Runner → **results.json** that feeds the dashboards.
  Start at a stated size (hundreds), scale later. This is where the demo numbers
  come from — real, reproducible.
- **Day 21 — Self-improving policy engine.** policy = ordered strategy; on failure
  → analyze → candidate policy → **A/B on the bench → promote if better**.
  Test: a better candidate is promoted, a worse one isn't.

## Phase E — Real-time + Control-Plane Foundation (Days 22–26)

*Dark, premium, Linear/Vercel/Datadog aesthetic. shadcn/ui + React Flow + Recharts.*

- **Day 22** — Redis + distributed workers (queue + shared state); compose/Helm.
- **Day 23** — Real-time **SSE** activity stream (`/missions/:id/stream`) + API v1
  (versioned) + OpenAPI.
- **Day 24** — Control-plane scaffold: layout, dark theme, sidebar (Overview,
  Missions, Agents, Memory, Evidence, Evaluations, Security, Observability).
- **Day 25** — Dashboard overview + **Active Missions** (live) + **Mission page
  with an interactive task graph** (React Flow, click-node → detail drawer).
- **Day 26** — Live **activity stream** page (SSE) + **Agent detail**
  (model, task, tools, resource usage, memories, confidence).

## Phase F — Pages, Demo, Deploy (Days 27–30)

- **Day 27** — **Memory Explorer** + **Evidence Graph** (React Flow over GraphRAG)
  + **Eval / Observability / Security** dashboards (Recharts; real benchmark +
  Prometheus data; surface v1 security guards + a live block-event log).
- **Day 28** — **Public landing** (hero + live mission viz) + **"Try Live Demo"**
  sandbox with preset missions incl. the **Failure-Recovery demo** — no config
  for the recruiter, runs safely.
- **Day 29** — Architecture page + interactive **API playground** + restrained
  Framer Motion polish + information hierarchy pass.
- **Day 30** — Full e2e smoke; **run the benchmark for real** and wire the numbers
  into landing/eval pages; README/positioning rewrite; docs; compose + Helm;
  demo video; **tag v2.0.0** + release notes.

---

## The live demo flow (what a recruiter sees)
Mission created → Planner builds task graph → Scheduler allocates resources →
Agents execute → Tools queried → Memory retrieved → **ML model flags anomaly** →
Evidence graph built → contradiction found → agent replans → tool fails →
**recovery strategy** → policy/approval check → action → verification → mission
complete → trajectory evaluated → memory consolidated. Numbers shown are the
**benchmark's real output**.

## Daily rhythm
`git pull` → build the day's core → tests last → CI green → 6–10 real commits
(schema → logic → integration → tests → docs). No padding. If a day overflows,
split it — real small commits beat faked ones.

## Honest scope note
The ML lifecycle now gets a proper 5 days (Days 13–17), so memory is compressed to
2 days (Days 18–19). If you want memory equally deep, we extend ~2–3 days past 30
— your call as we approach Phase D. The **irreducible core** (mission runtime +
scheduler + recovery + the ML lifecycle + the benchmark + the control-plane
dashboard) is what proves the thesis; everything else is depth we add if time allows.

## Scope-cut order (if behind)
benchmark task count (thousands → hundreds) → policy engine to one documented A/B →
organizational memory to a stub → WebSocket to SSE-only → fewer control-plane pages
(keep Dashboard, Mission graph, Activity stream, Eval, the ML monitoring panels).
