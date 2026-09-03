"use client";
import { AnomalyStatus } from "../../lib/api";

export default function AnomalyPanel({ status }: { status: AnomalyStatus | null }) {
  if (status && status.model_available) {
    return (
      <div className="card">
        <div className="stat-row"><span className="d ok" /><span className="lbl">Anomaly model</span>
          <span className="r">{status.model ?? "available"}{status.version ? ` · v${status.version}` : ""}</span></div>
        <div className="stat-row"><span className="d ok" /><span className="lbl">Threshold</span>
          <span className="r">{status.threshold ?? "—"}</span></div>
        <div className="stat-row"><span className="d off" /><span className="lbl">Live score</span>
          <span className="r">on-demand</span></div>
        <p className="empty-note" style={{ marginTop: 12 }}>
          Scoring runs on demand via <code>POST /anomaly/score</code>; drift PSI is computed per batch.
          No continuous stream — histograms are exported to Prometheus.
        </p>
      </div>
    );
  }
  return (
    <div className="card">
      <div className="stat-row"><span className="d off" /><span className="lbl">Anomaly model</span>
        <span className="r">not loaded</span></div>
      <p className="empty-note" style={{ marginTop: 12 }}>
        No anomaly model in the registry. Train/register one with <code>ml.anomaly.evaluate</code>.
      </p>
    </div>
  );
}
