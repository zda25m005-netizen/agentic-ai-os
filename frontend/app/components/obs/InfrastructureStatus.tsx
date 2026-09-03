"use client";
import { RuntimeConfig } from "../../lib/api";

// Flatten a /readyz payload into {name, ok} rows (handles bool values or {ok}/status objects).
function readinessRows(readyz: Record<string, unknown> | null): { name: string; ok: boolean }[] {
  if (!readyz) return [];
  const src = (readyz.checks && typeof readyz.checks === "object" ? readyz.checks : readyz) as Record<string, unknown>;
  const rows: { name: string; ok: boolean }[] = [];
  for (const [k, v] of Object.entries(src)) {
    if (k === "status") continue;
    if (typeof v === "boolean") rows.push({ name: k, ok: v });
    else if (v && typeof v === "object") {
      const o = v as Record<string, unknown>;
      const ok = o.ok === true || o.status === "ok" || o.reachable === true || o.healthy === true;
      rows.push({ name: k, ok });
    } else if (typeof v === "string") rows.push({ name: k, ok: v === "ok" });
  }
  return rows;
}

export default function InfrastructureStatus({ config, readyz }: {
  config: RuntimeConfig | null; readyz: Record<string, unknown> | null;
}) {
  const services = readinessRows(readyz);
  return (
    <div className="card">
      <div className="stat-row">
        <span className={`d ${config?.llm_key_configured ? "ok" : "off"}`} />
        <span className="lbl">LLM</span>
        <span className="sub" style={{ marginLeft: 4 }}>{config?.active_model ?? config?.llm_model ?? ""}</span>
        <span className="r">{config?.llm_key_configured ? "Configured" : "Not configured"}</span>
      </div>
      {services.map((s) => (
        <div className="stat-row" key={s.name}>
          <span className={`d ${s.ok ? "ok" : "off"}`} />
          <span className="lbl" style={{ textTransform: "capitalize" }}>{s.name}</span>
          <span className="r">{s.ok ? "Reachable" : "Unreachable"}</span>
        </div>
      ))}
      <div className="stat-row"><span className="d warn" /><span className="lbl">Prometheus</span>
        <span className="sub" style={{ marginLeft: 4 }}>/metrics scraped</span>
        <a className="r" href="http://localhost:9090" target="_blank" rel="noreferrer">Open</a></div>
      <div className="stat-row"><span className="d warn" /><span className="lbl">Grafana</span>
        <span className="sub" style={{ marginLeft: 4 }}>docker compose</span>
        <a className="r" href="http://localhost:3002" target="_blank" rel="noreferrer">Open</a></div>
      <p className="empty-note" style={{ marginTop: 12 }}>
        Service readiness is live from <code>/readyz</code>. Prometheus/Grafana links open the local
        stack when it’s running via docker compose (reachability isn’t probed from the browser).
      </p>
    </div>
  );
}
