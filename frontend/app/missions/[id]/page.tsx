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

export default function MissionDetail({ params }: { params: { id: string } }) {
  const id = Number(params.id);
  const [mission, setMission] = useState<MissionOut | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setMission(await api.getMission(id));
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "request failed");
    }
  }, [id]);

  useEffect(() => {
    load(); // initial snapshot
    let es: EventSource | null = null;
    let poll: ReturnType<typeof setInterval> | null = null;
    try {
      // live push via SSE; fall back to polling if the stream errors
      es = new EventSource(`${API}/missions/${id}/stream`);
      es.onmessage = (e) => {
        try {
          setMission(JSON.parse(e.data));
          setError("");
        } catch {
          /* ignore malformed frame */
        }
      };
      es.addEventListener("done", () => {
        es?.close();
        load();
      });
      es.onerror = () => {
        es?.close();
        if (!poll) poll = setInterval(load, 1500);
      };
    } catch {
      poll = setInterval(load, 1500);
    }
    return () => {
      es?.close();
      if (poll) clearInterval(poll);
    };
  }, [id, load]);

  async function action(name: string, fn: () => Promise<unknown>) {
    if (busy) return;
    setBusy(name);
    setError("");
    try {
      await fn();
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : `${name} failed`);
    } finally {
      setBusy("");
    }
  }

  // live elapsed timer (from created_at, ticking while running)
  const [now, setNow] = useState(Date.now() / 1000);
  const startedRef = useRef<number | null>(null);
  useEffect(() => {
    if (mission?.created_at && startedRef.current === null) startedRef.current = mission.created_at;
    const t = setInterval(() => setNow(Date.now() / 1000), 1000);
    return () => clearInterval(t);
  }, [mission?.created_at]);

  const status = mission?.status;
  const isTerminal = status ? TERMINAL.includes(status) : false;
  const isRunning = status === "active" || status === "created";
  const sel: TaskOut | undefined = mission?.tasks.find((t) => t.id === selected);
  const u = mission?.usage ?? {};
  const elapsed = startedRef.current ? Math.max(0, now - startedRef.current) : 0;
  const statusWord = status === "completed" ? "COMPLETED" : status === "failed" ? "FAILED"
    : status === "paused" ? "PAUSED" : "LIVE";
  const running = mission?.tasks.filter((t) => t.status === "running").length ?? 0;

  return (
    <div className="page">
      <div className="crumb">
        <Link href="/missions">Missions</Link> / #{id}
      </div>

      {error && !mission && <div className="card error">{error}</div>}

      {mission && (
        <>
          <div className="mc-head">
            <div>
              <h1 className="page-title">{mission.objective}</h1>
              <p className="page-sub">
                Mission #{mission.id} · priority {mission.priority} · {mission.total} tasks
                {running > 0 && <> · {running} running</>}
              </p>
            </div>
            <div className="mc-head-right">
              <span className={`live-pill ${statusWord === "LIVE" ? "on" : statusWord.toLowerCase()}`}>
                <i /> {statusWord}
              </span>
              <span className="mc-timer mono">{fmtDur(elapsed)}</span>
            </div>
          </div>

          <div className="mc-metrics">
            <div className="mc-metric"><span>Progress</span><b>{mission.settled}/{mission.total}</b></div>
            <div className="mc-metric"><span>Tokens</span><b>{(u.tokens ?? 0).toLocaleString()}</b></div>
            <div className="mc-metric"><span>Cost</span><b>${(u.usd ?? 0).toFixed(4)}</b></div>
            <div className="mc-metric"><span>LLM calls</span><b>{u.llm_calls ?? 0}</b></div>
            <div className="mc-metric"><span>Status</span><b><StatusBadge status={mission.status} /></b></div>
          </div>

          <div className="card">
            <div className="btn-row">
              <button
                className="btn btn-primary"
                disabled={isTerminal || busy !== ""}
                onClick={() => action("run", () => api.run(mission.id))}
              >
                {busy === "run" ? "Running…" : "Run to completion"}
              </button>
              <button
                className="btn"
                disabled={isTerminal || busy !== ""}
                onClick={() => action("tick", () => api.tick(mission.id))}
              >
                {busy === "tick" ? "Ticking…" : "Tick once"}
              </button>
              {status === "active" && (
                <button className="btn" disabled={busy !== ""} onClick={() => action("pause", () => api.pause(mission.id))}>
                  Pause
                </button>
              )}
              {status === "paused" && (
                <button className="btn" disabled={busy !== ""} onClick={() => action("resume", () => api.resume(mission.id))}>
                  Resume
                </button>
              )}
              <div className="progress" style={{ marginLeft: "auto", minWidth: 160 }}>
                <div className="bar">
                  <span style={{ width: `${mission.total ? (mission.settled / mission.total) * 100 : 0}%` }} />
                </div>
                <small>{mission.settled}/{mission.total}</small>
              </div>
            </div>
            {error && <p className="error" style={{ marginTop: 12 }}>{error}</p>}
          </div>

          <div className="card">
            <h3>Task graph</h3>
            <TaskGraph tasks={mission.tasks} selected={selected} onSelect={setSelected} />
          </div>

          {sel && (
            <div className="card">
              <h3>Task #{sel.id}</h3>
              <p style={{ margin: "0 0 10px" }}>{sel.description}</p>
              <div className="btn-row" style={{ marginBottom: 10 }}>
                <StatusBadge status={sel.status} />
                <span className="muted">
                  depends on: {sel.depends_on.length ? sel.depends_on.map((d) => `#${d}`).join(", ") : "—"}
                </span>
              </div>
              {sel.result && (
                <div className="trace" style={{ whiteSpace: "pre-wrap" }}>{sel.result}</div>
              )}
            </div>
          )}

          <div className="card">
            <h3>Tasks</h3>
            <table className="mtable">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Description</th>
                  <th>Depends on</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {mission.tasks.map((t) => (
                  <tr key={t.id} className="row-link" onClick={() => setSelected(t.id)}>
                    <td className="muted">{t.id}</td>
                    <td>{t.description}</td>
                    <td className="muted">
                      {t.depends_on.length ? t.depends_on.map((d) => `#${d}`).join(", ") : "—"}
                    </td>
                    <td><StatusBadge status={t.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
