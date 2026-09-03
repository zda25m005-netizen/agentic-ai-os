"use client";
import { AGENTS } from "../../lib/agentsData";

export default function AgentMetrics({ missions }: { missions: number | null }) {
  const active = AGENTS.filter((a) => a.status === "active").length;
  const items: { lbl: string; val: string; small?: boolean }[] = [
    { lbl: "Agents", val: String(AGENTS.length) },
    { lbl: "Active", val: String(active) },
    { lbl: "Missions in runtime", val: missions == null ? "—" : String(missions) },
    { lbl: "Runtime telemetry", val: "See Observability", small: true },
  ];
  return (
    <div className="metrics">
      {items.map((m) => (
        <div className="metric" key={m.lbl}>
          <div className="lbl">{m.lbl}</div>
          <div className={`val ${m.small ? "small" : ""}`}>{m.val}</div>
        </div>
      ))}
    </div>
  );
}
