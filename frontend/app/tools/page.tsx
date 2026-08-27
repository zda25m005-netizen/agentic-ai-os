const TOOLS = [
  ["calculator", "AST-safe arithmetic"], ["web_search", "external search"],
  ["rag_search", "hybrid RAG retrieval"], ["graph_search", "GraphRAG k-hop"],
  ["sql_tool", "read-only SQL"], ["python_exec", "sandboxed Python"],
  ["wikipedia", "encyclopedia lookup"], ["http_tool", "guarded HTTP (SSRF-safe)"],
  ["file_ops", "path-traversal-safe files"], ["data_analysis", "CSV/tabular analysis"],
  ["subagent", "recursive delegation"], ["anomaly_scan", "ML anomaly evidence"],
];
export default function Tools() {
  return (
    <div className="page">
      <div className="page-head"><div><h1 className="page-title">Tools</h1>
        <p className="page-sub">{TOOLS.length} safety-guarded tools in the registry.</p></div></div>
      <div className="stat-grid">
        {TOOLS.map(([n, d]) => (<div className="stat" key={n}><b style={{ fontSize: 15 }}>{n}</b><span>{d}</span></div>))}
      </div>
    </div>
  );
}
