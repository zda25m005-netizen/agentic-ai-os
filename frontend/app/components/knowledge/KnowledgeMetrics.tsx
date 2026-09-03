"use client";

// Measured on the labeled eval set (LLM-judge) — real, not live telemetry.
const ITEMS: { lbl: string; val: string; small?: boolean }[] = [
  { lbl: "Recall@5", val: "100%" },
  { lbl: "Reranker Recall@1", val: "100%" },
  { lbl: "Answer Correctness", val: "100%" },
  { lbl: "Eval Set", val: "Labeled · LLM-judge", small: true },
];

export default function KnowledgeMetrics() {
  return (
    <div className="metrics">
      {ITEMS.map((m) => (
        <div className="metric" key={m.lbl}>
          <div className="lbl">{m.lbl}</div>
          <div className={`val ${m.small ? "small" : ""}`}>{m.val}</div>
        </div>
      ))}
    </div>
  );
}
