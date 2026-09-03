"use client";
import Icon from "../Icon";
import { BENCHMARK, pct } from "../../lib/evalData";

export default function FailureAnalysis() {
  const rec = BENCHMARK.metrics.find((m) => m.id === "recovery")!;
  return (
    <div className="card">
      <div className="fail">
        <div className="ficon"><Icon name="alert" size={17} sw={1.7} /></div>
        <div>
          <b>Recovery weakness — double-fault tasks</b>
          <div className="fbig">{pct(rec.score)}</div>
          <p>{rec.note}</p>
        </div>
      </div>
    </div>
  );
}
