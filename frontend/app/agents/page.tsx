"use client";

// Agents page (Phase 4) — the agent-first experience.
// YOUR AGENTS (real, persisted, owner-scoped) + BUILT-IN AGENTS (templates) + create/run.
// Everything is backed by the real /agents + /characters API — no fabricated data.
// The internal planner/executor/critic loop is a runtime detail and lives under Observability.

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import AgentCharacter from "../components/AgentCharacter";
import { type AgentState, STATE_LABEL } from "../lib/characters";
import {
  type AgentDTO,
  type TemplateDTO,
  createAgent,
  deleteAgent,
  listAgents,
  listTemplates,
  pauseAgent,
  resumeAgent,
  runAgent,
} from "../lib/agentsApi";

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentDTO[] | null>(null);
  const [templates, setTemplates] = useState<TemplateDTO[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [a, t] = await Promise.all([listAgents(), listTemplates()]);
      setAgents(a);
      setTemplates(t);
      setError(null);
    } catch {
      setError("Can't reach the agent service. Start the API (uvicorn app.api.main:app --port 8000).");
      setAgents([]);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  async function withBusy(key: string, fn: () => Promise<unknown>) {
    setBusy(key);
    try { await fn(); await refresh(); } catch { /* surfaced via refresh */ } finally { setBusy(null); }
  }

  const createFromTemplate = (t: TemplateDTO) =>
    withBusy(`tpl-${t.id}`, () => createAgent({ template_id: t.id }));

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Agents</h1>
          <p className="page-sub">Your own team of AI workers — each with a job, tools, memory and a character.</p>
        </div>
        <Link href="/agents/new" className="agent-btn">+ Create agent</Link>
      </div>

      {error && <div className="ag-note">{error}</div>}

      {/* YOUR AGENTS */}
      <div className="sec-title" style={{ marginBottom: 12 }}>Your agents</div>
      {agents === null ? (
        <div className="ag-note">Loading your team…</div>
      ) : agents.length === 0 ? (
        <div className="ag-empty">
          <AgentCharacter character="nova" state="idle" size={72} />
          <div style={{ fontWeight: 600, marginTop: 8 }}>Your AI team starts here.</div>
          <div className="page-sub" style={{ marginTop: 2 }}>Create your first agent from a template below.</div>
        </div>
      ) : (
        <div className="team-grid">
          {agents.map((a) => (
            <div key={a.id} className="team-card">
              <AgentCharacter character={a.character_id} state={(a.status as AgentState) || "idle"} size={72} />
              <div className="team-name">{a.name}</div>
              <div className="team-purpose">{a.purpose || a.description || "—"}</div>
              <div className={`team-status s-${a.status}`}>{STATE_LABEL[a.status as AgentState] || a.status}</div>
              <div className="team-meta">
                {a.tools.length} tool{a.tools.length === 1 ? "" : "s"}
                {a.last_run_at ? " · ran " + new Date(a.last_run_at * 1000).toLocaleDateString() : " · never run"}
              </div>
              <div className="team-actions">
                <button className="agent-btn" disabled={busy === `run-${a.id}`} onClick={() => withBusy(`run-${a.id}`, () => runAgent(a.id))}>Run task</button>
                {a.status === "paused"
                  ? <button className="icon-btn" onClick={() => withBusy(`rs-${a.id}`, () => resumeAgent(a.id))}>Resume</button>
                  : <button className="icon-btn" onClick={() => withBusy(`ps-${a.id}`, () => pauseAgent(a.id))}>Pause</button>}
                <button className="icon-btn danger" onClick={() => withBusy(`del-${a.id}`, () => deleteAgent(a.id))}>Delete</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* BUILT-IN AGENTS / TEMPLATES */}
      <div className="sec-title" style={{ margin: "28px 0 12px" }}>Built-in agents</div>
      <div className="team-grid">
        {templates.map((t) => (
          <div key={t.id} className="team-card">
            <AgentCharacter character={t.character_id} state="idle" size={64} />
            <div className="team-name">{t.name}</div>
            <div className="team-purpose">{t.description}</div>
            <div className="team-meta">{t.tools.slice(0, 3).join(" · ")}</div>
            <div className="team-actions">
              <button className="agent-btn" disabled={busy === `tpl-${t.id}`} onClick={() => createFromTemplate(t)}>
                {busy === `tpl-${t.id}` ? "Creating…" : "Create agent"}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
