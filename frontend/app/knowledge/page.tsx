export default function Knowledge() {
  return (
    <div className="page">
      <div className="page-head"><div><h1 className="page-title">Knowledge · RAG</h1>
        <p className="page-sub">Hybrid retrieval + GraphRAG grounding answers with citations.</p></div></div>
      <div className="card"><h3>Pipeline</h3>
        <p className="muted" style={{ margin: 0 }}>Document → chunk → embed → vector DB (Qdrant) + from-scratch BM25 → Reciprocal Rank Fusion → LLM reranker → GraphRAG (Neo4j k-hop) → context.</p></div>
      <div className="card"><h3>Measured</h3>
        <div className="mc-metrics">
          <div className="mc-metric"><span>recall@5</span><b>100%</b></div>
          <div className="mc-metric"><span>reranker recall@1</span><b>90→100%</b></div>
          <div className="mc-metric"><span>answer correctness</span><b>100%</b></div>
        </div>
        <p className="muted" style={{ fontSize: 12, marginTop: 10 }}>On the labeled eval set (LLM-judge). See docs/ for details.</p></div>
    </div>
  );
}
