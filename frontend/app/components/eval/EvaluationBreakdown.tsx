"use client";
import { BENCHMARK, pct } from "../../lib/evalData";

export default function EvaluationBreakdown() {
  return (
    <div className="card">
      <div className="bars">
        {BENCHMARK.metrics.map((m) => (
          <div className="brow" key={m.id}>
            <span className="bn">{m.name}</span>
            <span className={`btrack ${m.score >= 1 ? "full" : ""}`}>
              <span style={{ width: `${Math.round(m.score * 100)}%` }} />
            </span>
            <span className="bval">{pct(m.score)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
