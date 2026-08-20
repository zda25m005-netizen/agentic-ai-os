# Control-Plane UI (v2 frontend)

The `frontend/` app is the **control plane** for the mission runtime: a dark,
Linear/Vercel-style dashboard to create missions, watch them execute over a task
graph, and inspect results. It is a thin client — all logic lives in the backend
(`app/`); the UI only fetches JSON and renders it.

## Tech stack

- **Next.js 14** (App Router) + **React 18** + **TypeScript**.
- **No UI framework** — plain CSS with CSS variables (`app/globals.css`). This is
  deliberate: zero heavy dependencies (no Tailwind/shadcn/React Flow) means the
  build is fast and can't break from a version conflict before a demo.
- The interactive task graph is hand-drawn **SVG** (no graph library).
- Talks to the FastAPI backend over REST; base URL is `NEXT_PUBLIC_API_BASE`
  (defaults to `http://localhost:8000`).

## Running it

Two processes, side by side:

```bash
# backend (repo root)
uvicorn app.api.main:app --reload          # http://localhost:8000

# frontend
cd frontend && npm run dev                  # http://localhost:3000 (or next free port)
```

The backend's CORS allows any `localhost:*` origin (regex in `app/api/main.py`),
so whatever port Next picks will work. For a no-Postgres local run, set
`DATABASE_URL=sqlite+aiosqlite:///./agentic.db` in `.env`; mission tables are
created at startup by the FastAPI `lifespan` hook.

## Directory map

```
frontend/app/
  layout.tsx              root layout — renders <Sidebar/> + <main> shell
  globals.css             all styles (shell, cards, badges, graph, v1 playground)
  page.tsx                "/"              Overview (dashboard)
  missions/page.tsx       "/missions"      list + create
  missions/[id]/page.tsx  "/missions/:id"  mission detail + task graph + controls
  playground/page.tsx     "/playground"    v1 single-shot Agent/RAG UI
  lib/api.ts              typed REST client + shared types
  components/
    Sidebar.tsx           left nav (active + "soon" items)
    StatusBadge.tsx       colored pill for any mission/task status
    TaskGraph.tsx         SVG DAG renderer (nodes + dependency edges)
```

## Pages

### Overview (`/`)
Dashboard. Fetches `GET /missions` every 4s and shows: total mission count,
counts by status (active / completed / failed / paused), and a "recent missions"
table with status badge + progress bar. Rows link to the mission detail page. If
the backend is down it shows a friendly "is the API running?" error instead of
crashing.

### Missions (`/missions`)
Two parts: a **create form** (goal text + priority) that calls
`POST /missions` and, on success, routes straight to the new mission's page; and
a **live list** of all missions (polled every 4s) with status + progress.
Creating a mission triggers the backend's Goal Interpreter + Mission Planner, so
it requires an LLM key; a failure surfaces as an inline error.

### Mission detail (`/missions/[id]`)
The core screen. Polls `GET /missions/:id` every **1.5s** so the view stays live
while a run is in flight. Contains:

- **Header** — objective, priority, settled/total, and a status badge.
- **Controls** — `Run to completion` (`POST /:id/run`), `Tick once`
  (`POST /:id/tick`), and `Pause`/`Resume` (`POST /:id/pause|resume`) shown only
  when the status allows them. Buttons disable while a terminal state is reached
  or an action is in flight. A live progress bar sits alongside.
- **Task graph** — the `TaskGraph` component (see below). Click a node to select
  it.
- **Task detail** — when a node/row is selected, shows its description, status,
  dependencies, and persisted `result` text.
- **Tasks table** — every task with id, description, `depends_on`, and status;
  clicking a row selects it in the graph.

### Playground (`/playground`)
The **v1** UI, preserved. Two modes: **Agent** (`POST /agent` — runs the
planner→executor→critic orchestrator on one goal and shows plan, execution
trace, and metrics: tokens / latency / estimated cost) and **Ask (RAG)**
(`POST /ask` — retrieval-augmented answer with citations). Single-shot, not
persistent — this is the contrast to Missions.

## Components

### `TaskGraph.tsx`
Renders the task DAG as SVG. Layout algorithm:

1. Compute each task's **column** = its dependency depth (longest path from a
   root; a root has depth 0). This groups tasks into left-to-right layers that
   respect dependencies.
2. Stack tasks that share a column **vertically** (row index per column).
3. Draw each dependency as a **bezier edge** from the parent's right edge to the
   child's left edge.
4. Color each node by status (fill + stroke maps mirror the badge palette).
   The selected node gets an accent stroke.

It's defensive: a self/again dependency can't loop the depth calc (a `seen` set
guards it), and dangling deps (pointing at a missing task) are ignored. A legend
maps colors to statuses. `onSelect(id)` reports clicks back to the page.

### `StatusBadge.tsx`
Maps every mission status (`created/active/paused/completed/failed`) and task
status (`pending/ready/running/done/failed/skipped`) to a colored pill class in
`globals.css`.

### `Sidebar.tsx`
Left nav. Live sections (**Overview, Missions, Playground**) are links with an
active-route highlight. **Agents, Memory, Evaluations, Observability** are marked
`soon` — see below.

## API client (`lib/api.ts`)

A small typed wrapper over `fetch` with `cache: "no-store"` (always live) and
error extraction (reads FastAPI's `detail` field). Exposes:

| Method | Endpoint |
| --- | --- |
| `api.listMissions(status?)` | `GET /missions` |
| `api.getMission(id)` | `GET /missions/:id` |
| `api.createMission(goal, priority)` | `POST /missions` |
| `api.tick(id)` | `POST /missions/:id/tick` |
| `api.run(id, maxTicks)` | `POST /missions/:id/run` |
| `api.pause(id)` / `api.resume(id)` | `POST /missions/:id/pause` \| `/resume` |

Types (`MissionOut`, `TaskOut`, `TickOut`, `MissionStatus`, `TaskStatus`) mirror
the Pydantic models in `app/api/missions.py`.

## The "soon" sections

`Agents`, `Memory`, `Evaluations`, and `Observability` are placeholders in the
nav — **the backends already exist in v1; only the visualization page is future
work** (a deliberate depth-over-breadth choice):

- **Agents** — the multi-agent orchestrator (`app/agents/`) runs today; see it in
  Playground. This tab will be the per-agent drill-down.
- **Memory** — `app/memory/` has episodic + semantic stores and a manager. This
  tab will be the memory explorer.
- **Evaluations** — `eval/` holds the reranker eval and fine-tuning ablation.
  This tab will surface those (real) numbers.
- **Observability** — `app/obs/` emits Prometheus metrics + Langfuse traces, with
  Grafana dashboards under `ops/grafana/`. This tab will be the in-app view.

## Design notes / conventions

- Every data page **polls** on an interval and cleans up its timer on unmount, so
  the whole control plane feels live without websockets (SSE is a later phase).
- Pages fail soft: a backend error renders an inline message, never a blank page.
- Client components (`"use client"`) are used wherever hooks or fetch are needed;
  `StatusBadge` is a pure presentational component shared across pages.
- Styling stays in `globals.css` with semantic class names (`.card`, `.stat`,
  `.mtable`, `.badge`, `.graph-*`) rather than inline utility classes.
