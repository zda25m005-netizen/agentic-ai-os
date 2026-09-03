"use client";
import { RuntimeSummary, money, compact } from "../../lib/obsApi";

export default function RuntimeMetrics({ s }: { s: RuntimeSummary | null }) {
  const items: { lbl: string; val: string }[] = s
    ? [
        { lbl: "Missions", val: String(s.missions) },
        { lbl: "Success Rate", val: s.successRate == null ? "—" : `${Math.round(s.successRate * 100)}%` },
        { lbl: "Running", val: String(s.running) },
        { lbl: "LLM Cost", val: money(s.usd) },
        { lbl: "Tokens", val: compact(s.tokens) },
      ]
    : [
        { lbl: "Missions", val: "…" }, { lbl: "Success Rate", val: "…" },
        { lbl: "Running", val: "…" }, { lbl: "LLM Cost", val: "…" }, { lbl: "Tokens", val: "…" },
      ];
  return (
    <div className="metrics">
      {items.map((m) => (
        <div className="metric" key={m.lbl}>
          <div className="lbl">{m.lbl}</div>
          <div className="val">{m.val}</div>
        </div>
      ))}
    </div>
  );
}
