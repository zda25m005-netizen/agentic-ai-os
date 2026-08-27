// Typed client for the mission control-plane API.
// All calls go through the FastAPI backend (see app/api/missions.py).

export const API = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export type MissionStatus =
  | "created"
  | "active"
  | "paused"
  | "completed"
  | "failed";

export type TaskStatus =
  | "pending"
  | "ready"
  | "running"
  | "done"
  | "failed"
  | "skipped";

export type TaskOut = {
  id: number;
  description: string;
  status: TaskStatus;
  depends_on: number[];
  result: string | null;
};

export type Usage = {
  usd?: number;
  tokens?: number;
  tool_calls?: number;
  llm_calls?: number;
};

export type MissionOut = {
  id: number;
  objective: string;
  status: MissionStatus;
  priority: number;
  deadline: number | null;
  settled: number;
  total: number;
  tasks: TaskOut[];
  usage?: Usage;
  created_at?: number | null;
};

export type TickOut = {
  mission_id: number;
  status: MissionStatus;
  ran: number[];
  failed: number[];
};

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API}${path}`, {
    headers: { "content-type": "application/json" },
    cache: "no-store",
    ...init,
  });
  if (!r.ok) {
    let detail = `HTTP ${r.status}`;
    try {
      const body = await r.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* ignore non-JSON error bodies */
    }
    throw new Error(detail);
  }
  return r.json() as Promise<T>;
}

export const api = {
  listMissions: (status?: MissionStatus) =>
    req<MissionOut[]>(`/missions${status ? `?status=${status}` : ""}`),
  getMission: (id: number) => req<MissionOut>(`/missions/${id}`),
  createMission: (goal: string, priority = 0) =>
    req<MissionOut>(`/missions`, {
      method: "POST",
      body: JSON.stringify({ goal, priority }),
    }),
  tick: (id: number) =>
    req<TickOut>(`/missions/${id}/tick`, { method: "POST" }),
  run: (id: number, maxTicks = 100) =>
    req<MissionOut>(`/missions/${id}/run?max_ticks=${maxTicks}`, {
      method: "POST",
    }),
  pause: (id: number) =>
    req<MissionOut>(`/missions/${id}/pause`, { method: "POST" }),
  resume: (id: number) =>
    req<MissionOut>(`/missions/${id}/resume`, { method: "POST" }),
};

export const MISSION_STATUSES: MissionStatus[] = [
  "created",
  "active",
  "paused",
  "completed",
  "failed",
];
