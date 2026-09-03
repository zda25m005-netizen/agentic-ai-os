"use client";
import { BENCHMARK, EvalMetric, pct, status, STATUS_LABEL } from "../../lib/evalData";

const find = (id: string) => BENCHMARK.metrics.find((m) => m.id === id)!;

export default function BenchmarkSummary() {
  const cards: { lbl: string; val: string; m?: EvalMetric }[] = [
    { lbl: "Tasks", val: String(BENCHMARK.tasks) },
    ...["task_success", "recovery", "safety_block", "planning_validity"].map((id) => {
      const m = find(id); return { lbl: m.name, val: pct(m.score), m };
    }),
  ];
  return (
    <div className="summary">
      {cards.map((c) => (
        <div className="sumcard" key={c.lbl}>
          <div className="lbl">{c.lbl}</div>
          <div className="val">{c.val}</div>
          {c.m && <div className={`st ${status(c.m)}`}><span className="d" />{STATUS_LABEL[status(c.m)]}</div>}
        </div>
      ))}
    </div>
  );
}
