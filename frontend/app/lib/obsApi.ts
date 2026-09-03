// ---------------------------------------------------------------------------
// Observability data layer — built from REAL backend data.
//
// `/missions` carries real per-mission usage (usd / tokens / llm_calls /
// tool_calls) and task statuses, so cost, tokens, success rate, recent activity
// and errors are genuine aggregates — not fabricated. Fine-grained telemetry
// (latency histograms, per-tool/per-agent counters) is exported to Prometheus at
// /metrics for Grafana, not as JSON, so those panels show an honest "exposed via
// Prometheus" state rather than invented numbers. `/config`, `/readyz` and
// `/anomaly/status` provide real runtime + infrastructure health.
// ---------------------------------------------------------------------------
import { api, MissionOut } from "./api";

export interface RuntimeSummary {
  missions: number; running: number; completed: number; failed: number;
  successRate: number | null;
  usd: number; tokens: number; llmCalls: number; toolCalls: number;
}
export interface ActivityEvent { missionId: number; title: string; status: string; progress: string; at: number | null; }
export interface ErrorEvent { missionId: number; title: string; detail: string; }
export interface Runtime {
  summary: RuntimeSummary; activity: ActivityEvent[]; errors: ErrorEvent[]; loadedAt: number;
}

export async function loadRuntime(): Promise<Runtime> {
  const missions = await api.listMissions();
  const sum = (f: (m: MissionOut) => number) => missions.reduce((a, m) => a + f(m), 0);
  const completed = missions.filter((m) => m.status === "completed").length;
  const failed = missions.filter((m) => m.status === "failed").length;
  const terminal = completed + failed;

  const summary: RuntimeSummary = {
    missions: missions.length,
    running: missions.filter((m) => m.status === "active").length,
    completed, failed,
    successRate: terminal ? completed / terminal : null,
    usd: sum((m) => m.usage?.usd ?? 0),
    tokens: sum((m) => m.usage?.tokens ?? 0),
    llmCalls: sum((m) => m.usage?.llm_calls ?? 0),
    toolCalls: sum((m) => m.usage?.tool_calls ?? 0),
  };

  const activity: ActivityEvent[] = [...missions]
    .sort((a, b) => (b.created_at ?? 0) - (a.created_at ?? 0))
    .slice(0, 8)
    .map((m) => ({ missionId: m.id, title: m.objective, status: m.status,
      progress: `${m.settled}/${m.total} tasks`, at: m.created_at ?? null }));

  const errors: ErrorEvent[] = [];
  for (const m of missions) {
    if (m.status === "failed") errors.push({ missionId: m.id, title: m.objective, detail: "Mission failed" });
    for (const t of m.tasks || []) {
      if (t.status === "failed") errors.push({ missionId: m.id, title: t.description, detail: "Task failed" });
    }
  }

  return { summary, activity, errors: errors.slice(0, 8), loadedAt: Date.now() };
}

export function relSeconds(epochSec: number | null): string {
  if (!epochSec) return "—";
  const d = Date.now() - epochSec * 1000;
  const m = Math.floor(d / 6e4), h = Math.floor(d / 36e5), day = Math.floor(d / 864e5);
  if (d < 6e4) return "just now";
  if (h < 1) return `${m}m ago`;
  if (day < 1) return `${h}h ago`;
  return `${day}d ago`;
}
export const money = (v: number) => `$${v.toFixed(2)}`;
export const compact = (v: number) => (v >= 1000 ? `${(v / 1000).toFixed(1)}K` : String(v));
