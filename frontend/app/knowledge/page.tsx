"use client";

import "../knowledge.css";
import KnowledgeMetrics from "../components/knowledge/KnowledgeMetrics";
import RetrievalPipeline from "../components/knowledge/RetrievalPipeline";
import RetrievalStrategy from "../components/knowledge/RetrievalStrategy";
import RetrievalQuality from "../components/knowledge/RetrievalQuality";
import KnowledgeQuery from "../components/knowledge/KnowledgeQuery";

export default function KnowledgePage() {
  return (
    <div className="kn">
      <div className="wrap">
        <div className="head">
          <div>
            <h1 className="h1">Knowledge · RAG</h1>
            <p className="h-sub">Manage indexed knowledge, retrieval quality, and grounding.</p>
          </div>
        </div>

        <KnowledgeMetrics />

        <div className="sec-h">Retrieval Pipeline</div>
        <div className="card"><RetrievalPipeline /></div>

        <div className="sec-h">Retrieval Strategy</div>
        <RetrievalStrategy />

        <div className="sec-h">Retrieval Quality</div>
        <RetrievalQuality />

        <div className="sec-h">Knowledge Query</div>
        <KnowledgeQuery />

        <div className="grid2" style={{ marginTop: 16 }}>
          <div className="card">
            <div className="sec-h" style={{ margin: "0 0 12px" }}>Knowledge Graph</div>
            <div className="kv">
              <span className="k">Backend</span><span className="v">Neo4j (GraphRAG)</span>
              <span className="k">Traversal</span><span className="v">k-hop entity / relation</span>
              <span className="k">Fusion</span><span className="v">Graph facts + vector via RRF</span>
              <span className="k">Entities</span><span className="v">— not exposed via API</span>
              <span className="k">Relationships</span><span className="v">— not exposed via API</span>
            </div>
            <p className="note">Live graph statistics aren’t served over HTTP yet. Detailed traversal
              and per-query facts appear in the query results and in Observability.</p>
          </div>

          <div className="card">
            <div className="sec-h" style={{ margin: "0 0 12px" }}>Knowledge Sources</div>
            <p className="note" style={{ marginTop: 0 }}>
              A source/ingestion API isn’t exposed yet, so indexed documents can’t be listed or
              managed here. Ingestion currently runs via the pipeline CLI; when a sources endpoint
              lands, this panel will list documents with type, chunk count, last-indexed time and
              re-index / remove actions.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
