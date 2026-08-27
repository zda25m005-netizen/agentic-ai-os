export default function Observability() {
  return (
    <div className="page">
      <div className="page-head"><div><h1 className="page-title">Observability</h1>
        <p className="page-sub">Prometheus metrics + Grafana dashboards + Langfuse tracing.</p></div></div>
      <div className="card"><h3>Signals</h3>
        <p className="muted" style={{ margin: 0 }}>Per-request latency histogram, LLM token/cost counters, per-tool and per-agent-node counters, anomaly score histogram + drift PSI gauge — scraped at <code>/metrics</code>.</p></div>
      <div className="card"><h3>Dashboards</h3>
        <p className="muted" style={{ margin: 0 }}>Grafana runs at <code>localhost:3002</code> (docker compose). Prometheus at <code>localhost:9090</code>.</p></div>
    </div>
  );
}
