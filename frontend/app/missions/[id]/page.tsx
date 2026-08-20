"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, MissionOut, TaskOut } from "../../lib/api";
import StatusBadge from "../../components/StatusBadge";
import TaskGraph from "../../components/TaskGraph";

const TERMINAL = ["completed", "failed"];

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
    load();
    const t = setInterval(load, 1500); // live refresh while a run is in flight
    return () => clearInterval(t);
  }, [load]);

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

  const status = mission?.status;
  const isTerminal = status ? TERMINAL.includes(status) : false;
  const sel: TaskOut | undefined = mission?.tasks.find((t) => t.id === selected);

  return (
    <div className="page">
      <div className="crumb">
        <Link href="/missions">Missions</Link> / #{id}
      </div>

      {error && !mission && <div className="card error">{error}</div>}

      {mission && (
        <>
          <div className="page-head">
            <div>
              <h1 className="page-title">{mission.objective}</h1>
              <p className="page-sub">
                Mission #{mission.id} · priority {mission.priority} ·{" "}
                {mission.settled}/{mission.total} tasks settled
              </p>
            </div>
            <StatusBadge status={mission.status} />
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
