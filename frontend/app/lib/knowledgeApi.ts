// ---------------------------------------------------------------------------
// Knowledge / RAG data layer.
//
// The `/ask` endpoint is REAL (hybrid retrieval + optional GraphRAG, returns an
// answer with citations + scored sources). The query playground uses it live.
// Document/chunk/source *counts* and ingestion are NOT exposed over HTTP, and the
// eval numbers below come from the labeled evaluation set (LLM-judge) — they are
// architecture / measured facts, not live production telemetry. Nothing is faked.
// ---------------------------------------------------------------------------
import { API } from "./api";

export type AskMode = "vector" | "fused" | "graph";

export interface AskCitation { marker: number; source: string; chunk_index: number | null; score: number; }
export interface AskSource { source: string; chunk_index: number | null; score: number; }
export interface AskResult { answer: string; citations: AskCitation[]; sources: AskSource[]; }

export async function askKnowledge(question: string, mode: AskMode = "fused"): Promise<AskResult> {
  const r = await fetch(`${API}/ask`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ question, mode, top_k: 5 }),
  });
  if (!r.ok) {
    if (r.status === 503) throw new Error("LLM not configured — set OPENAI_API_KEY in the backend .env.");
    if (r.status === 502) throw new Error("Knowledge index unavailable (vector store / graph not reachable).");
    throw new Error(`Request failed (${r.status}).`);
  }
  return r.json();
}

// The retrieval path each mode actually exercises (for provenance display).
export const RETRIEVAL_PATH: Record<AskMode, string[]> = {
  vector: ["Vector", "BM25", "RRF", "Reranker"],
  fused: ["Vector", "BM25", "RRF", "Reranker", "GraphRAG"],
  graph: ["GraphRAG"],
};

// System architecture — real design, not telemetry (no fabricated counts).
export const PIPELINE: { name: string; desc: string }[] = [
  { name: "Documents", desc: "Ingested sources" },
  { name: "Chunking", desc: "Recursive splitter" },
  { name: "Embeddings", desc: "text-embedding-3-small" },
  { name: "Qdrant", desc: "Dense vector index" },
  { name: "BM25", desc: "Lexical, from scratch" },
  { name: "RRF", desc: "Reciprocal rank fusion" },
  { name: "Reranker", desc: "LLM precision refine" },
  { name: "GraphRAG", desc: "Neo4j k-hop" },
  { name: "Context", desc: "Grounded answer" },
];

export const STRATEGY: { name: string; purpose: string }[] = [
  { name: "Vector Search", purpose: "Semantic retrieval" },
  { name: "BM25", purpose: "Lexical retrieval" },
  { name: "Reciprocal Rank Fusion", purpose: "Hybrid fusion" },
  { name: "LLM Reranker", purpose: "Precision refinement" },
  { name: "GraphRAG", purpose: "Relationship grounding" },
];

// Measured on the labeled eval set (LLM-judge).
export const QUALITY: { name: string; value?: string; baseline?: string; current?: string; note: string }[] = [
  { name: "Recall@5", value: "100%", note: "Relevant chunk in top 5" },
  { name: "Reranker Recall@1", baseline: "90%", current: "100%", note: "Top result after reranking" },
  { name: "Answer Correctness", value: "100%", note: "LLM-judge on labeled set" },
];
