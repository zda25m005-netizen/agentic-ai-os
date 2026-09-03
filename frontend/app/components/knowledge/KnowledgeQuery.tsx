"use client";
import { useState } from "react";
import Icon from "../Icon";
import { askKnowledge, AskMode, AskResult, RETRIEVAL_PATH } from "../../lib/knowledgeApi";

const fileName = (s: string) => s.split("/").pop() || s;

export default function KnowledgeQuery() {
  const [q, setQ] = useState("");
  const [mode, setMode] = useState<AskMode>("fused");
  const [loading, setLoading] = useState(false);
  const [res, setRes] = useState<AskResult | null>(null);
  const [err, setErr] = useState("");
  const [ranMode, setRanMode] = useState<AskMode>("fused");

  const run = async () => {
    if (!q.trim() || loading) return;
    setLoading(true); setErr(""); setRes(null);
    try {
      setRanMode(mode);
      setRes(await askKnowledge(q.trim(), mode));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Request failed.");
    } finally {
      setLoading(false);
    }
  };

  const rows = res
    ? (res.citations.length
        ? res.citations.map((c) => ({ marker: c.marker, source: c.source, chunk: c.chunk_index, score: c.score }))
        : res.sources.map((s, i) => ({ marker: i + 1, source: s.source, chunk: s.chunk_index, score: s.score })))
    : [];

  return (
    <div className="card">
      <div className="qbar">
        <input placeholder="Ask something about your knowledge..." value={q}
          onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && run()} />
        <select value={mode} onChange={(e) => setMode(e.target.value as AskMode)} aria-label="Retrieval mode">
          <option value="fused">Hybrid + GraphRAG</option>
          <option value="vector">Vector + Rerank</option>
          <option value="graph">Graph only</option>
        </select>
        <button onClick={run} disabled={loading || !q.trim()}>{loading ? "Searching…" : "Search"}</button>
      </div>

      {err && <div className="qerr">{err}</div>}

      {!res && !err && !loading && (
        <div className="qhint">Runs the live retrieval pipeline and returns a grounded answer with cited sources. Retrieval provenance only — no model reasoning is shown.</div>
      )}

      {res && (
        <div className="qresult">
          <div className="qpath">
            <span className="pl">Retrieval path</span>
            {RETRIEVAL_PATH[ranMode].map((n, i) => (
              <span key={n} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <span className="node">{n}</span>
                {i < RETRIEVAL_PATH[ranMode].length - 1 && <Icon name="arrowRight" size={12} sw={2} />}
              </span>
            ))}
          </div>
          <div className="ans-lbl">Answer</div>
          <div className="ans">{res.answer}</div>
          {rows.length > 0 && (
            <div className="sources">
              <div className="ans-lbl">Sources · {rows.length}</div>
              {rows.map((r, i) => (
                <div className="source" key={i}>
                  <span className="mk">{r.marker}</span>
                  <span className="sfile">{fileName(r.source)}</span>
                  {r.chunk != null && <span className="schunk">chunk {r.chunk}</span>}
                  <span className="sscore">{r.score.toFixed(3)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
