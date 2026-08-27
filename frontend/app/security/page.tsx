const CHECKS = [
  "JWT auth + RBAC (admin/user roles)", "SSRF protection on the HTTP tool",
  "Path-traversal protection on file ops", "Read-only SQL tool",
  "AST-based Python sandbox (no exec/eval)", "Per-tool permission guards",
];
export default function Security() {
  return (
    <div className="page">
      <div className="page-head"><div><h1 className="page-title">Security</h1>
        <p className="page-sub">Guardrails around autonomous execution.</p></div></div>
      <div className="card"><h3>Active controls</h3>
        <div className="act-list">
          {CHECKS.map((c) => (<div key={c} className="act-row"><span style={{ color: "#22c55e" }}>✓</span><span>{c}</span></div>))}
        </div></div>
    </div>
  );
}
