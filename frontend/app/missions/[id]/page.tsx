"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { API, api, MissionOut, TaskOut } from "../../lib/api";
import StatusBadge from "../../components/StatusBadge";
import TaskGraph from "../../components/TaskGraph";

const TERMINAL = ["completed", "failed"];

function fmt(s: number) {
  const m = Math.floor(s / 60), sec = Math.floor(s % 60);
  return `00:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

const PIPE = [
  { name: "Created", color: "#a855f7" },
  { name: "Planning", color: "#a855f7" },
  { name: "Executing", color: "#2196ff" },
  { name: "Reviewing", color: "#18d5d1" },
  { name: "Finalize", color: "#18d889" },
];

function pipeState(m: MissionOut, idx: number): string {
  const pct = m.total ? m.settled / m.total : 0;
  const done = m.status === "completed";
  const failed = m.status === "failed";
  const active = [
    m.status !== "created",             // Created
    m.total > 0,                        // Planning
    !done && !failed && m.total > 0,    // Executing
    !done && pct >= 0.99,               // Reviewing
    done,                              // Finalize
  ];
  const complete = [true, m.total > 0, done, done, done];
  if (done || complete[idx]) return "done";
  if (failed && idx >= 2) return "failed";
  if (active[idx]) return "active";
  return "pending";
}

export default function MissionDetail({ params }: { params: { id: string } }) {
  const id = Number(params.id);
  const [mission, setMission] = useState<MissionOut | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const prevStatuses = useRef<Record<number, string>>({});
  const [activity, setActivity] = useState<{ t: string; who: string; what: string; kind: string }[]>([]);

  const load = useCallback(async () => {
    try { setMission(await api.getMission(id)); setError(""); }
    catch (e) { setError(e instanceof Error ? e.message : "request failed"); }
  }, [id]);

  useEffect(() => {
    load();
    let es: EventSource | null = null;
    let poll: ReturnType<typeof setInterval> | null = null;
    try {
      es = new EventSource(`${API}/missions/${id}/stream`);
      es.onmessage = (e) => { try { setMission(JSON.parse(e.data)); setError(""); } catch { /* */ } };
      es.addEventListener("done", () => { es?.close(); load(); });
      es.onerror = () => { es?.close(); if (!poll) poll = setInterval(load, 1500); };
    } catch { poll = setInterval(load, 1500); }
    return () => { es?.close(); if (poll) clearInterval(poll); };
  }, [id, load]);

  useEffect(() => {
    if (!mission) return;
    const now = new Date().toLocaleTimeString([], { hour12: false });
    const evs: { t: string; who: string; what: string; kind: string }[] = [];
    for (const task of mission.tasks) {
      const was = prevStatuses.current[task.id];
      if (was && was !== task.status) {
        const kind = task.status === "done" ? "ok" : task.status === "failed" ? "fail" : "info";
        evs.push({ t: now, who: `Task #${task.id}`, what: `${was} → ${task.status}`, kind });
      }
      prevStatuses.current[task.id] = task.status;
    }
    if (evs.length) setActivity((a) => [...evs.reverse(), ...a].slice(0, 20));
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

  if (!mission) {
    return <div className="cp"><div className="cp-panel" style={{ maxWidth: 400, margin: "40px auto" }}>
      {error ? <span className="error">{error}</span> : "INITIALIZING MISSION RUNTIME…"}</div></div>;
  }

  const status = mission.status;
  const isTerminal = TERMINAL.includes(status);
  const sel: TaskOut | undefined = mission.tasks.find((t) => t.id === selected);
  const u = mission.usage ?? {};
  const elapsed = startedRef.current ? Math.max(0, now - startedRef.current) : 0;
  const statusWord = status === "completed" ? "COMPLETED" : status === "failed" ? "FAILED" : status === "paused" ? "PAUSED" : "LIVE";
  const runningTask = mission.tasks.find((t) => t.status === "running");
  const tokens = u.tokens ?? 0;
  const pct = mission.total ? Math.round((mission.settled / mission.total) * 100) : 0;

  return (
    <div className="cp">
      <div className="cp-head">
        <div>
          <div className="cp-crumb"><Link href="/missions">Missions</Link> / #{mission.id}</div>
          <h1 className="cp-title">{mission.objective}</h1>
          <div className="cp-sub">priority <b>{mission.priority}</b> · {mission.total} tasks · {pct}% complete</div>
        </div>
        <div className="cp-head-actions">
          <span className={`live-pill ${statusWord === "LIVE" ? "on" : statusWord.toLowerCase()}`}><i /> {statusWord}</span>
          <span className="cp-timer mono">{fmt(elapsed)}</span>
          {status === "active" && <button className="cp-btn" style={{ borderColor: "#7a1f1f", color: "#ff4d5a" }} disabled={busy !== ""} onClick={() => action("pause", () => api.pause(mission.id))}>◼ Stop</button>}
        </div>
      </div>

      <div className="cp-pipeline">
        {PIPE.map((p, idx, arr) => {
          const st = pipeState(mission, idx);
          return (
            <div key={p.name} className={`cps cps-${st}`}>
              <span className="cps-dot" style={{ ["--c" as string]: p.color }}><i /></span>
              <div><b style={{ color: st === "pending" ? undefined : p.color }}>{p.name}</b><span>{st}</span></div>
              {idx < arr.length - 1 && <div className={`cps-conn ${st === "done" ? "on" : st === "active" ? "live" : ""}`} />}
            </div>
          );
        })}
      </div>

      <div className="cp-main">
        <div className="cp-panel cp-graph">
          <div className="cp-panel-h">TASK GRAPH <span className="cp-zoom mono">{mission.tasks.length} nodes</span></div>
          <div className="cp-graph-grid"><TaskGraph tasks={mission.tasks} selected={selected} onSelect={setSelected} /></div>
        </div>

        <div className="cp-col">
          <div className="cp-panel">
            <div className="cp-panel-h">MISSION METRICS</div>
            <div className="cp-metrics">
              <div className="cp-metric"><span>Tokens</span><b>{tokens.toLocaleString()}</b></div>
              <div className="cp-metric"><span>Cost</span><b>${(u.usd ?? 0).toFixed(4)}</b></div>
              <div className="cp-metric"><span>LLM calls</span><b>{u.llm_calls ?? 0}</b></div>
              <div className="cp-metric"><span>Progress</span><b>{mission.settled}/{mission.total}</b></div>
            </div>
          </div>

          <div className="cp-panel">
            <div className="cp-panel-h">CURRENT STEP</div>
            {runningTask ? (
              <>
                <div className="step-agent" style={{ color: "#18d5d1" }}>Executor <span className="muted" style={{ fontSize: 12 }}>running</span></div>
                <div className="muted" style={{ fontSize: 13, margin: "6px 0 10px" }}>{runningTask.description}</div>
                <div className="progress"><div className="bar"><span className="bar-anim" style={{ width: "66%" }} /></div><small>running</small></div>
              </>
            ) : <div className="muted" style={{ fontSize: 13 }}>{isTerminal ? `No step running — ${status}` : "Idle — run to start"}</div>}
            <div className="btn-row" style={{ marginTop: 14 }}>
              <button className="btn btn-primary" disabled={isTerminal || busy !== ""} onClick={() => action("run", () => api.run(mission.id))}>{busy === "run" ? "Running…" : "Run"}</button>
              <button className="btn" disabled={isTerminal || busy !== ""} onClick={() => action("tick", () => api.tick(mission.id))}>{busy === "tick" ? "Ticking…" : "Tick"}</button>
              {status === "paused" && <button className="btn" disabled={busy !== ""} onClick={() => action("resume", () => api.resume(mission.id))}>Resume</button>}
            </div>
          </div>

          <div className="cp-panel">
            <div className="cp-panel-h">LIVE ACTIVITY</div>
            <div className="waveform">{Array.from({ length: 30 }).map((_, k) => (
              <span key={k} style={{ animationDelay: `${(k % 7) * 90}ms`, animationPlayState: runningTask ? "running" : "paused", background: k % 3 === 0 ? "#a855f7" : k % 3 === 1 ? "#2196ff" : "#18d5d1" }} />
            ))}</div>
          </div>
        </div>

        <div className="cp-col cp-events">
          <div className="cp-panel cp-eventstream">
            <div className="cp-tabs"><span className="on">EVENT STREAM</span></div>
            <div className="timeline">
              {activity.length === 0 ? <div className="muted" style={{ fontSize: 13 }}>Waiting for task events…</div> :
                activity.map((a, k) => (
                  <div key={k} className="tl-row" style={{ animation: k === 0 ? "actIn .35s ease" : undefined }}>
                    <span className={`tl-dot ${a.kind}`} />
                    <div><span className="mono tl-t">{a.t}</span>
                      <div className="tl-comp" style={{ color: "#18d5d1" }}>{a.who}</div>
                      <div className="tl-ev muted">{a.what}</div></div>
                  </div>
                ))}
            </div>
          </div>

          <div className="cp-panel">
            <div className="cp-panel-h">TOKEN USAGE<span className="cp-panel-sub">this mission</span></div>
            <svg className="tokenstream" viewBox="0 0 260 60" preserveAspectRatio="none">
              {["#a855f7", "#2196ff", "#18d5d1"].map((c, k) => (
                <path key={c} className={`tw tw${k}`} stroke={c} fill="none" strokeWidth="1.5"
                  style={{ animationPlayState: runningTask ? "running" : "paused" }}
                  d="M0,30 C40,8 60,52 100,30 C140,8 160,52 200,30 C240,8 260,44 300,30" />
              ))}
            </svg>
            <div className="tok-counts">
              <div><span>Input</span><b className="mono">{Math.round(tokens * 0.25).toLocaleString()}</b></div>
              <div><span>Output</span><b className="mono">{Math.round(tokens * 0.75).toLocaleString()}</b></div>
              <div><span>Total</span><b className="mono">{tokens.toLocaleString()}</b></div>
            </div>
          </div>
        </div>
      </div>

      {error && <div className="cp-panel" style={{ marginTop: 14 }}><span className="error">{error}</span></div>}

      {sel && (
        <div className="cp-panel" style={{ marginTop: 14 }}>
          <div className="cp-panel-h">TASK #{sel.id} <StatusBadge status={sel.status} /></div>
          <p style={{ margin: "0 0 8px" }}>{sel.description}</p>
          <span className="muted" style={{ fontSize: 12 }}>depends on: {sel.depends_on.length ? sel.depends_on.map((d) => `#${d}`).join(", ") : "—"}</span>
          {sel.result && <div className="trace" style={{ whiteSpace: "pre-wrap", marginTop: 10 }}>{sel.result}</div>}
        </div>
      )}

      <div className="cp-bottom" style={{ gridTemplateColumns: "1fr 220px" }}>
        <div className="cp-panel">
          <div className="cp-panel-h">TASKS</div>
          <table className="mtable">
            <thead><tr><th>#</th><th>Description</th><th>Depends</th><th>Status</th></tr></thead>
            <tbody>{mission.tasks.map((t) => (
              <tr key={t.id} className="row-link" onClick={() => setSelected(t.id)}>
                <td className="muted">{t.id}</td><td>{t.description}</td>
                <td className="muted">{t.depends_on.length ? t.depends_on.map((d) => `#${d}`).join(", ") : "—"}</td>
                <td><StatusBadge status={t.status} /></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
        <div className="cp-panel cp-qa">
          <div className="cp-panel-h">QUICK ACTIONS</div>
          <button className="cp-action" disabled={status !== "active" || busy !== ""} onClick={() => action("pause", () => api.pause(mission.id))}>❚❚ Pause mission</button>
          <a className="cp-action" href={`${API}/missions/${mission.id}/report.pdf`} target="_blank" rel="noreferrer">⤓ Download PDF report</a>
          <button className="cp-action" onClick={() => api.createMission(mission.objective, mission.priority).then(load)}>⧉ Clone mission</button>
          <Link className="cp-action" href="/missions">← All missions</Link>
        </div>
      </div>
    </div>
  );
}
