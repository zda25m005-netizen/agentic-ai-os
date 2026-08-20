"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, MissionOut, MissionStatus } from "./lib/api";
import StatusBadge from "./components/StatusBadge";

const STAT_ORDER: MissionStatus[] = ["active", "completed", "failed", "paused"];

export default function Overview() {
  const [missions, setMissions] = useState<MissionOut[] | null>(null);
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
    const t = setInterval(load, 4000); // keep the overview live
    return () => clearInterval(t);
  }, []);

  const counts = (missions || []).reduce<Record<string, number>>((acc, m) => {
    acc[m.status] = (acc[m.status] || 0) + 1;
    return acc;
  }, {});
  const total = missions?.length ?? 0;
  const recent = (missions || []).slice(0, 8);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Overview</h1>
          <p className="page-sub">Long-horizon autonomous missions — live state.</p>
        </div>
        <Link href="/missions" className="btn btn-primary">New mission</Link>
      </div>

      <div className="stat-grid">
        <div className="stat">
          <b>{total}</b>
          <span>Total missions</span>
        </div>
        {STAT_ORDER.map((s) => (
          <div className="stat" key={s}>
            <b>{counts[s] || 0}</b>
            <span>{s}</span>
          </div>
        ))}
      </div>

      {error && (
        <div className="card error">
          {error} — is the API running on the backend? Start it with <code>make run</code>.
        </div>
      )}

      <div className="card">
        <h3>Recent missions</h3>
        {recent.length === 0 && !error && (
          <div className="empty">No missions yet. Create one from the Missions page.</div>
        )}
        {recent.length > 0 && (
          <table className="mtable">
            <thead>
              <tr>
                <th>#</th>
                <th>Objective</th>
                <th>Status</th>
                <th>Progress</th>
              </tr>
            </thead>
            <tbody>
              {recent.map((m) => (
                <tr key={m.id} className="row-link">
                  <td className="muted">{m.id}</td>
                  <td>
                    <Link href={`/missions/${m.id}`}>{m.objective}</Link>
                  </td>
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
