"use client";

export default function ToolMetrics({ m }: {
  m: { total: number; active: number; categories: number; safety: number };
}) {
  const items: [string, string, boolean?][] = [
    ["Total Tools", String(m.total)],
    ["Active", String(m.active)],
    ["Categories", String(m.categories)],
    ["Execution Telemetry", "Not connected", true],
  ];
  return (
    <div className="metrics">
      {items.map(([lbl, v, muted]) => (
        <div className="metric" key={lbl}>
          <div className="lbl">{lbl}</div>
          <div className={`val ${muted ? "muted" : ""}`}>{v}</div>
        </div>
      ))}
    </div>
  );
}
