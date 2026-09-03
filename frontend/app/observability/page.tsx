"use client";

import { useCallback, useEffect, useState } from "react";
import "../observability.css";
import Icon from "../components/Icon";
import RuntimeMetrics from "../components/obs/RuntimeMetrics";
import LiveActivity from "../components/obs/LiveActivity";
import CostPanel from "../components/obs/CostPanel";
import ErrorPanel from "../components/obs/ErrorPanel";
import AnomalyPanel from "../components/obs/AnomalyPanel";
import InfrastructureStatus from "../components/obs/InfrastructureStatus";
import { loadRuntime, relSeconds, Runtime } from "../lib/obsApi";
import { api, RuntimeConfig, AnomalyStatus } from "../lib/api";

export default function ObservabilityPage() {
  const [rt, setRt] = useState<Runtime | null>(null);
  const [config, setConfig] = useState<RuntimeConfig | null>(null);
  const [readyz, setReadyz] = useState<Record<string, unknown> | null>(null);
  const [anomaly, setAnomaly] = useState<AnomalyStatus | null>(null);

  const refresh = useCallback(() => {
    loadRuntime().then(setRt).catch(() => {});
    api.config().then(setConfig).catch(() => {});
    api.readyz().then(setReadyz).catch(() => {});
    api.anomalyStatus().then(setAnomaly).catch(() => {});
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const s = rt?.summary ?? null;

  return (
    <div className="obs">
      <div className="wrap">
        <div className="head">
          <div>
            <h1 className="h1">Observability</h1>
            <p className="h-sub">Monitor agent executions, latency, cost, errors, and runtime health.</p>
          </div>
          <div className="head-actions">
            <span className="updated">Updated {rt ? relSeconds(Math.floor(rt.loadedAt / 1000)) : "…"}</span>
            <button className="btn" onClick={refresh}><Icon name="sync" size={13} /> Refresh</button>
          </div>
        </div>

        <RuntimeMetrics s={s} />

        <div className="sec-h">Live Activity</div>
        <LiveActivity events={rt?.activity ?? []} />

        <div className="grid2" style={{ marginTop: 16 }}>
          <div>
            <div className="sec-h" style={{ marginTop: 0 }}>LLM Cost & Tokens</div>
            <CostPanel s={s} />
          </div>
          <div>
            <div className="sec-h" style={{ marginTop: 0 }}>Recent Errors</div>
            <ErrorPanel errors={rt?.errors ?? []} />
          </div>
        </div>

        <div className="sec-h">Performance</div>
        <div className="card">
          <p className="empty-note" style={{ margin: 0 }}>
            Latency histograms (P50 / P95 / P99), per-tool and per-agent counters are exported to
            Prometheus at <code>/metrics</code> and visualised in Grafana — they aren’t served as JSON,
            so they’re not duplicated here. Cost, tokens and mission outcomes above are live aggregates
            from the mission runtime.
          </p>
        </div>

        <div className="grid2" style={{ marginTop: 16 }}>
          <div>
            <div className="sec-h" style={{ marginTop: 0 }}>Anomalies & Drift</div>
            <AnomalyPanel status={anomaly} />
          </div>
          <div>
            <div className="sec-h" style={{ marginTop: 0 }}>Infrastructure</div>
            <InfrastructureStatus config={config} readyz={readyz} />
          </div>
        </div>
      </div>
    </div>
  );
}
