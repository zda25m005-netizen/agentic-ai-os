"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { API, api, MissionOut, TaskOut } from "../../lib/api";
import StatusBadge from "../../components/StatusBadge";
import TaskGraph from "../../components/TaskGraph";

const TERMINAL = ["completed", "failed"];

function fmtDur(s: number) {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

// Derive a lifecycle pipeline from real mission state (honest, not fabricated).
function pipeline(m: MissionOut) {
  const pct = m.total ? m.settled / m.total : 0;
  const failed = m.status === "failed";
  const done = m.status === "completed";
  const stage = (s: string, state: string) => ({ name: s, state });
  return [
    stage("Created", "done"),
    stage("Planning", m.total > 0 ? "done" : "active"),
    stage("Executing", done ? "done" : failed ? "failed" : m.total > 0 ? "active" : "pending"),
    stage("Reviewing", done ? "done" : pct >= 0.99 && !failed ? "active" : "pending"),
    stage("Finalize", done ? "done" : failed ? "failed" : "pending"),
  ];
}

export default function MissionDetail({ params }: { params: { id: string } }) {
  const id = Number(params.id);
  const [mission, setMission] = useState<MissionOut | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const prevStatuses = useRef<Record<number, string>>({});
  const [activity, setActivity] = useState<{ t: string; who: string; what: string }[]>([]);

  const load = useCallback(async () => {
    try {
      setMission(await api.getMission(id));
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "request failed");
    }
  }, [id]);

  useEffect(() => {
    load();
    let es: EventSource | null = null;
    let poll: ReturnType<typeof setInterval> | null = null;
    try {
      es = new EventSource(`${API}/missions/${id}/stream`);
      es.onmessage = (e) => {
        try { setMission(JSON.parse(e.data)); setError(""); } catch { /* ignore */ }
      };
      es.addEventListener("done", () => { es?.close(); load(); });
      es.onerror = () => { es?.close(); if (!poll) poll = setInterval(load, 1500); };
    } catch {
      poll = setInterval(load, 1500);
    }
    return () => { es?.close(); if (poll) clearInterval(poll); };
  }, [id, load]);

  // build a live activity feed from real task-status transitions
  useEffect(() => {
    if (!mission) return;
    const now = new Date().toLocaleTimeString([], { hour12: false });
    const events: { t: string; who: string; what: string }[] = [];
    for (const task of mission.tasks) {
      const was = prevStatuses.current[task.id];
      if (was && was !== task.status) {
        events.push({ t: now, who: `Task #${task.id}`, what: `${was} → ${task.status}` });
      }
      prevStatuses.current[task.id] = task.status;
    }
    if (events.length) setActivity((a) => [...events.reverse(), ...a].slice(0, 12));
  }, [mission]);

  const [now, setNow] = useState(Date.now() / 1000);
  const startedRef = useRef<number | null>(null);
  useEffect(() => {
    if (mission?.created_at && startedRef.current === null) startedRef.current = mission.created_at;
    const t = setInterval(() => setNow(Date.now() / 1000), 1000);
    return () => clearInterval(t);
  }, [mission?.created_at]);

  async function action(name: string, fn: () => Promise<unknown>) {
    if (busy) return;
    setBusy(name); setError("");
    try { await fn(); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : `${name} failed`); }
    finally { setBusy(""); }
  }

  const status = mission?.status;
  const isTerminal = status ? TERMINAL.includes(status) : false;
  const sel: TaskOut | undefined = mission?.tasks.find((t) => t.id === selected);
  const u = mission?.usage ?? {};
  const elapsed = startedRef.current ? Math.max(0, now - startedRef.current) : 0;
  const statusWord = status === "completed" ? "COMPLETED" : status === "failed" ? "FAILED"
    : status === "paused" ? "PAUSED" : "LIVE";
  const runningTask = mission?.tasks.find((t) => t.status === "running");
  const pct = mission && mission.total ? Math.round((mission.settled / mission.total) * 100) : 0;

  if (!mission) {
    return <div className="page">{error ? <div className="card error">{error}</div> : <div className="empty">Loading…</div>}</div>;
  }

  return (
    <div className="mc">
      {/* header */}
      <div className="mc-head">
        <div>
          <div className="crumb"><Link href="/missions">Missions</Link> / #{mission.id}</div>
          <h1 className="mc-title">{mission.objective}</h1>
          <div className="mc-meta">
            priority <b>{mission.priority}</b> · {mission.total} tasks · {pct}% complete
          </div>
        </div>
        <div className="mc-head-right">
          <span className={`live-pill ${statusWord === "LIVE" ? "on" : statusWord.toLowerCase()}`}><i /> {statusWord}</span>
          <span className="mc-timer mono">{fmtDur(elapsed)}</span>
          {status === "active" && <button className="btn danger" disabled={busy !== ""} onClick={() => action("pause", () => api.pause(mission.id))}>Stop</button>}
        </div>
      </div>

      {/* pipeline */}
      <div className="pipeline">
        {pipeline(mission).map((s, i, arr) => (
          <div key={s.name} className={`pl-stage pl-${s.state}`}>
            <div className="pl-dot"><i /></div>
            <div className="pl-body"><b>{s.name}</b><span>{s.state}</span></div>
            {i < arr.length - 1 && <div className={`pl-conn ${s.state === "done" ? "on" : ""}`} />}
          </div>
        ))}
      </div>

      {/* main grid */}
      <div className="mc-grid">
        <div className="card mc-graph">
          <h3>Task graph</h3>
          <TaskGraph tasks={mission.tasks} selected={selected} onSelect={setSelected} />
        </div>

        <div className="mc-side">
          <div className="card">
            <h3>Mission metrics</h3>
            <div className="mc-metrics">
              <div className="mc-metric"><span>Tokens</span><b>{(u.tokens ?? 0).toLocaleString()}</b></div>
              <div className="mc-metric"><span>Cost</span><b>${(u.usd ?? 0).toFixed(4)}</b></div>
              <div className="mc-metric"><span>LLM calls</span><b>{u.llm_calls ?? 0}</b></div>
              <div className="mc-metric"><span>Progress</span><b>{mission.settled}/{mission.total}</b></div>
            </div>
          </div>

          <div className="card">
            <h3>Current step</h3>
            {runningTask ? (
              <div>
                <div className="btn-row"><b>{runningTask.description}</b></div>
                <div className="progress" style={{ marginTop: 10 }}>
                  <div className="bar"><span className="bar-anim" style={{ width: "66%" }} /></div>
                  <small>running</small>
                </div>
              </div>
            ) : (
              <div className="muted">{isTerminal ? "No step running — mission " + status : "Idle — run to start"}</div>
            )}
            <div className="btn-row" style={{ marginTop: 14 }}>
              <button className="btn btn-primary" disabled={isTerminal || busy !== ""} onClick={() => action("run", () => api.run(mission.id))}>{busy === "run" ? "Running…" : "Run"}</button>
              <button className="btn" disabled={isTerminal || busy !== ""} onClick={() => action("tick", () => api.tick(mission.id))}>{busy === "tick" ? "Ticking…" : "Tick"}</button>
              {status === "paused" && <button className="btn" disabled={busy !== ""} onClick={() => action("resume", () => api.resume(mission.id))}>Resume</button>}
            </div>
          </div>

          <div className="card">
            <h3>Live activity</h3>
            {activity.length === 0 ? <div className="muted" style={{ fontSize: 13 }}>Waiting for task events…</div> : (
              <div className="act-list">
                {activity.map((a, i) => (
                  <div key={i} className="act-row">
                    <span className="mono act-t">{a.t}</span>
                    <span className="act-who">{a.who}</span>
                    <span className="act-what">{a.what}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {error && <div className="card error">{error}</div>}

      {sel && (
        <div className="card">
          <h3>Task #{sel.id}</h3>
          <p style={{ margin: "0 0 10px" }}>{sel.description}</p>
          <div className="btn-row" style={{ marginBottom: 10 }}>
            <StatusBadge status={sel.status} />
            <span className="muted">depends on: {sel.depends_on.length ? sel.depends_on.map((d) => `#${d}`).join(", ") : "—"}</span>
          </div>
          {sel.result && <div className="trace" style={{ whiteSpace: "pre-wrap" }}>{sel.result}</div>}
        </div>
      )}

      {/* bottom: tasks + quick actions */}
      <div className="mc-bottom">
        <div className="card">
          <h3>Tasks</h3>
          <table className="mtable">
            <thead><tr><th>#</th><th>Description</th><th>Depends</th><th>Status</th></tr></thead>
            <tbody>
              {mission.tasks.map((t) => (
                <tr key={t.id} className="row-link" onClick={() => setSelected(t.id)}>
                  <td className="muted">{t.id}</td>
                  <td>{t.description}</td>
                  <td className="muted">{t.depends_on.length ? t.depends_on.map((d) => `#${d}`).join(", ") : "—"}</td>
                  <td><StatusBadge status={t.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="card mc-actions">
          <h3>Quick actions</h3>
          <button className="btn" disabled={isTerminal || busy !== "" || status !== "active"} onClick={() => action("pause", () => api.pause(mission.id))}>❚❚ Pause mission</button>
          <button className="btn" disabled={busy !== ""} onClick={() => api.createMission(mission.objective, mission.priority).then(load)}>⧉ Clone mission</button>
          <Link className="btn" href="/missions">← All missions</Link>
        </div>
      </div>
    </div>
  );
}
