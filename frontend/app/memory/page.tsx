export default function Memory() {
  const layers = [
    ["Working", "Short-term scratchpad, capacity-bounded (evicts oldest)."],
    ["Episodic", "Append-only log of what happened, in time order."],
    ["Semantic", "Durable keyed facts (re-learning updates in place)."],
    ["Procedural", "Learned 'how-to' step sequences."],
    ["Organizational", "Knowledge shared across missions."],
  ];
  return (
    <div className="page">
      <div className="page-head"><div><h1 className="page-title">Memory</h1>
        <p className="page-sub">Five-layer memory with importance scoring, decay, consolidation and conflict resolution.</p></div></div>
      <div className="card"><h3>Layers</h3>
        <table className="mtable"><tbody>
          {layers.map(([r, d]) => (<tr key={r}><td style={{ width: 160 }}><b>{r}</b></td><td className="muted">{d}</td></tr>))}
        </tbody></table>
      </div>
      <div className="card"><h3>Dynamics</h3>
        <p className="muted" style={{ margin: 0 }}>Retrieval reinforces items; unused memories decay and prune; important working notes consolidate to long-term.</p></div>
    </div>
  );
}
