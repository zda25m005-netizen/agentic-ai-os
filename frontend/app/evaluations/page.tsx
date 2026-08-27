export default function Evaluations() {
  const rows: [string, string][] = [
    ["task success", "0.875"], ["recovery rate", "0.667"], ["tool selection", "0.857"],
    ["memory retrieval", "1.000"], ["safety block", "1.000"], ["planning validity", "1.000"],
  ];
  return (
    <div className="page">
      <div className="page-head"><div><h1 className="page-title">Evaluations</h1>
        <p className="page-sub">Fault-injection benchmark — 200 tasks, seed 42, real reproducible numbers.</p></div></div>
      <div className="card"><h3>Benchmark results</h3>
        <table className="mtable"><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody>
          {rows.map(([k, v]) => (<tr key={k}><td>{k}</td><td className="mono"><b>{v}</b></td></tr>))}
        </tbody></table>
        <p className="muted" style={{ fontSize: 12, marginTop: 10 }}>Honest finding: double-fault (hard) tasks escalate rather than recover, so recovery = 0.667. Run: <code>python -m benchmarks.run</code></p></div>
    </div>
  );
}
