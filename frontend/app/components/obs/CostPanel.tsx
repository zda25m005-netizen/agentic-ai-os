"use client";
import { RuntimeSummary, money, compact } from "../../lib/obsApi";

export default function CostPanel({ s }: { s: RuntimeSummary | null }) {
  const avg = s && s.missions ? s.usd / s.missions : 0;
  return (
    <div className="card">
      <div className="kv">
        <span className="k">Total LLM spend</span><span className="v big">{s ? money(s.usd) : "…"}</span>
        <span className="k">Average / mission</span><span className="v">{s ? money(avg) : "…"}</span>
        <span className="k">LLM calls</span><span className="v">{s ? compact(s.llmCalls) : "…"}</span>
        <span className="k">Tool calls</span><span className="v">{s ? compact(s.toolCalls) : "…"}</span>
        <span className="k">Total tokens</span><span className="v">{s ? compact(s.tokens) : "…"}</span>
      </div>
    </div>
  );
}
