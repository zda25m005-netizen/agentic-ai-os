"use client";
import { BENCHMARK, EvalMetric, pct, status, STATUS_LABEL } from "../../lib/evalData";

export default function BenchmarkTable({ onOpen }: { onOpen: (m: EvalMetric) => void }) {
  return (
    <div className="card" style={{ padding: "6px 6px 2px" }}>
      <table>
        <thead>
          <tr><th>Metric</th><th>Score</th><th>Target</th><th>Status</th><th>Interpretation</th></tr>
        </thead>
        <tbody>
          {BENCHMARK.metrics.map((m) => {
            const s = status(m);
            return (
              <tr className="row" key={m.id} onClick={() => onOpen(m)}>
                <td>{m.name}</td>
                <td className="score">{pct(m.score)}</td>
                <td className="target">≥ {pct(m.target)}</td>
                <td><span className={`stpill st ${s}`}><span className="d" />{STATUS_LABEL[s]}</span></td>
                <td className="interp">{m.interpretation}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
