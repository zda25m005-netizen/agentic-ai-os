"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, MissionOut } from "../lib/api";
import StatusBadge from "../components/StatusBadge";

export default function MissionsPage() {
  const router = useRouter();
  const [missions, setMissions] = useState<MissionOut[] | null>(null);
  const [goal, setGoal] = useState("");
  const [priority, setPriority] = useState(0);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    try {
      setMissions(await api.listMissions());
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "request failed");
    }
  }

  useEffect(() => {
    load();
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, []);

  async function create() {
    if (!goal.trim() || creating) return;
    setCreating(true);
    setError("");
    try {
      const m = await api.createMission(goal.trim(), priority);
      router.push(`/missions/${m.id}`); // jump straight to the new mission
    } catch (e) {
      setError(e instanceof Error ? e.message : "could not create mission");
      setCreating(false);
    }
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Missions</h1>
          <p className="page-sub">Give the runtime a goal; it plans a task DAG and executes it.</p>
        </div>
      </div>

      <div className="card">
        <h3>New mission</h3>
        <div className="form-row">
          <input
            className="input grow"
            placeholder="e.g. Monitor Company X's filings for 30 days and flag material changes"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && create()}
          />
          <input
            className="input"
            type="number"
            title="priority"
            style={{ width: 100 }}
            value={priority}
            onChange={(e) => setPriority(Number(e.target.value) || 0)}
          />
          <button className="btn btn-primary" onClick={create} disabled={creating}>
            {creating ? "Planning…" : "Create"}
          </button>
        </div>
        {error && <p className="error" style={{ marginTop: 12 }}>{error}</p>}
      </div>

      <div className="card">
        <h3>All missions</h3>
        {(missions?.length ?? 0) === 0 ? (
          <div className="empty">No missions yet.</div>
        ) : (
          <table className="mtable">
            <thead>
              <tr>
                <th>#</th>
                <th>Objective</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Progress</th>
              </tr>
            </thead>
            <tbody>
              {missions!.map((m) => (
                <tr key={m.id} className="row-link" onClick={() => router.push(`/missions/${m.id}`)}>
                  <td className="muted">{m.id}</td>
                  <td><Link href={`/missions/${m.id}`}>{m.objective}</Link></td>
                  <td className="muted">{m.priority}</td>
                  <td><StatusBadge status={m.status} /></td>
                  <td>
                    <div className="progress">
                      <div className="bar">
                        <span style={{ width: `${m.total ? (m.settled / m.total) * 100 : 0}%` }} />
                      </div>
                      <small>{m.settled}/{m.total}</small>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
