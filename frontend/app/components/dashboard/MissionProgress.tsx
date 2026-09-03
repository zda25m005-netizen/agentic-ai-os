"use client";
import Link from "next/link";
import Icon from "../Icon";
import { MissionOut } from "../../lib/api";

const DEMO = [
  { objective: "Find ML Jobs in Germany", pct: 75 },
  { objective: "Research: RAG vs Fine-tuning", pct: 60 },
  { objective: "PhD Opportunities in Switzerland", pct: 40 },
];

export default function MissionProgress({ missions }: { missions: MissionOut[] | null }) {
  const active = (missions || []).filter((m) => m.status === "active");
  const rows = active.length
    ? active.slice(0, 4).map((m) => ({
        objective: m.objective,
        pct: m.total ? Math.round((m.settled / m.total) * 100) : 0,
      }))
    : DEMO;

  return (
    <div className="panel">
      <div className="panel-head">
        <div className="panel-title">Mission Progress</div>
        <Link href="/missions" className="link">View all</Link>
      </div>
      <div className="panel-sub">Your active missions</div>
      {rows.map((r, i) => (
        <div className="mp" key={i}>
          <div className="mp-top"><b>{r.objective}</b><span className="pct">{r.pct}%</span></div>
          <div className="track"><div className="fill" style={{ width: `${r.pct}%` }} /></div>
        </div>
      ))}
      <Link href="/missions" className="foot-link">
        Go to Missions <Icon name="arrowRight" size={13} sw={2} />
      </Link>
    </div>
  );
}
