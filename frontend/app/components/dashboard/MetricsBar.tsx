"use client";
import Icon from "../Icon";
import { METRICS } from "../../lib/dashboardData";

export default function MetricsBar({ overrides }: { overrides?: Partial<Record<string, string>> }) {
  return (
    <div className="metrics">
      {METRICS.map((m) => (
        <div className="metric" key={m.label}>
          <div className="m-lbl"><Icon name={m.icon} size={14} sw={1.7} />{m.label}</div>
          <div className="m-val">{overrides?.[m.label] ?? m.value}</div>
          <div className="m-grow">{m.grow}</div>
        </div>
      ))}
    </div>
  );
}
