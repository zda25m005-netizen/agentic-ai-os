"use client";
import Icon from "../Icon";
import { Consolidation, LAYERS, relativeTime } from "../../lib/memoryApi";

const name = (id: string) => LAYERS.find((l) => l.id === id)?.name ?? id;

export default function RecentConsolidations({ items }: { items: Consolidation[] }) {
  return (
    <div className="panel">
      <div className="panel-title">Recent Consolidations</div>
      {items.length === 0 && <div className="empty"><span>No recent consolidations.</span></div>}
      {items.map((c, i) => (
        <div className="cons" key={i}>
          <div className="cons-flow">
            <span className="from">{name(c.from)}</span>
            <Icon name="arrowRight" size={12} sw={2} />
            <span className="to">{name(c.to)}</span>
          </div>
          <div className="cons-b">
            <div className="cons-note">{c.note}</div>
            <div className="cons-time">{relativeTime(c.at)}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
