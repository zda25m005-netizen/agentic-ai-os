"use client";

export default function MemoryMetrics({ m }: {
  m: { total: number; working: number; longTerm: number; retrievedToday: number };
}) {
  const items: [string, number][] = [
    ["Total Memories", m.total],
    ["Working", m.working],
    ["Long-term", m.longTerm],
    ["Retrieved Today", m.retrievedToday],
  ];
  return (
    <div className="metrics">
      {items.map(([lbl, v]) => (
        <div className="metric" key={lbl}>
          <div className="lbl">{lbl}</div>
          <div className="val">{v.toLocaleString()}</div>
        </div>
      ))}
    </div>
  );
}
