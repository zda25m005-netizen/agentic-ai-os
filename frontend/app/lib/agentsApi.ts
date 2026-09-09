// Agent registry API client (Phase 3). Talks to the real /agents + /characters backend.
// No fabricated data — every call hits a persisted, owner-scoped endpoint.

import type { AgentState } from "./characters";

const BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export interface AgentDTO {
  id: string;
  owner: string;
  name: string;
  description: string;
  purpose: string;
  instructions: string;
  character_id: string;
  tools: string[];
  memory_config: Record<string, unknown>;
  knowledge_sources: string[];
  model: Record<string, unknown>;
  schedule: Record<string, unknown>;
  trigger_config: Record<string, unknown>;
  approval_policy: Record<string, unknown>;
  personality: string;
  template_id: string | null;
  status: AgentState | string;
  created_at: number;
  updated_at: number;
  last_run_at: number | null;
}

export interface TemplateDTO {
  id: string;
  name: string;
  description: string;
  purpose: string;
  character_id: string;
  personality: string;
  tools: string[];
  route: string;
  memory_config?: Record<string, unknown>;
  approval_policy?: Record<string, unknown>;
}

export interface CharacterDTO {
  id: string;
  name: string;
  accent: string;
  personality: string;
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`${init?.method || "GET"} ${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}

export const listAgents = () => req<{ agents: AgentDTO[] }>("/agents").then((r) => r.agents);
export const getAgent = (id: string) => req<AgentDTO>(`/agents/${id}`);
export const createAgent = (body: Partial<AgentDTO> & { template_id?: string }) =>
  req<AgentDTO>("/agents", { method: "POST", body: JSON.stringify(body) });
export const updateAgent = (id: string, body: Partial<AgentDTO>) =>
  req<AgentDTO>(`/agents/${id}`, { method: "PUT", body: JSON.stringify(body) });
export const deleteAgent = (id: string) =>
  req<{ deleted: boolean }>(`/agents/${id}`, { method: "DELETE" });
export const runAgent = (id: string, task?: string) =>
  req<{ mission_id: number; status: string; objective: string }>(`/agents/${id}/run`, {
    method: "POST",
    body: JSON.stringify({ task: task ?? null }),
  });
export const pauseAgent = (id: string) => req<AgentDTO>(`/agents/${id}/pause`, { method: "POST" });
export const resumeAgent = (id: string) => req<AgentDTO>(`/agents/${id}/resume`, { method: "POST" });
export const agentTasks = (id: string) => req<{ tasks: any[] }>(`/agents/${id}/tasks`).then((r) => r.tasks);
export const agentActivity = (id: string) => req<{ activity: any[] }>(`/agents/${id}/activity`).then((r) => r.activity);
export const agentMemory = (id: string) => req<{ count: number; layers: Record<string, number> }>(`/agents/${id}/memory`);
export const listTemplates = () => req<{ templates: TemplateDTO[] }>("/agents/templates").then((r) => r.templates);
export const listCharacters = () => req<{ characters: CharacterDTO[] }>("/characters").then((r) => r.characters);

export interface AgentSpec {
  name: string;
  description: string;
  purpose: string;
  instructions: string;
  tools: string[];
  memory_config: Record<string, unknown>;
  schedule: Record<string, unknown>;
  approval_policy: Record<string, unknown>;
  personality: string;
  suggested_character_id: string;
  template_id: string;
  generated_by: string;
}

export const generateSpec = (description: string) =>
  req<{ spec: AgentSpec }>("/agents/spec", {
    method: "POST",
    body: JSON.stringify({ description }),
  }).then((r) => r.spec);
