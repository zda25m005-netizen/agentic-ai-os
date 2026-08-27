export default function Experiments() {
  const rows: [string, string, string, string][] = [
    ["gradient_boosting", "0.986", "0.903", "0.014"],
    ["logreg", "0.982", "0.878", "0.044"],
    ["gaussian", "0.945", "0.844", "n/a"],
    ["isolation_forest", "0.947", "0.729", "n/a"],
    ["autoencoder", "0.917", "0.769", "n/a"],
  ];
  return (
    <div className="page">
      <div className="page-head"><div><h1 className="page-title">ML Experiments</h1>
        <p className="page-sub">Anomaly-detection model comparison, tracked in MLflow (seed 42, held-out test).</p></div></div>
      <div className="card"><h3>Model comparison</h3>
        <table className="mtable"><thead><tr><th>Model</th><th>ROC-AUC</th><th>PR-AUC</th><th>Brier</th></tr></thead><tbody>
          {rows.map((r) => (<tr key={r[0]}><td>{r[0]}{r[0] === "gradient_boosting" && " ★"}</td><td className="mono">{r[1]}</td><td className="mono">{r[2]}</td><td className="mono">{r[3]}</td></tr>))}
        </tbody></table>
        <p className="muted" style={{ fontSize: 12, marginTop: 10 }}>Winner promoted to a versioned registry. Run: <code>python -m ml.anomaly.evaluate</code></p></div>
    </div>
  );
}
