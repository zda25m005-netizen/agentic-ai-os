# DESIGN.md — Enterprise Agentic AI OS (v0)

> Living design doc. Updated as the system grows. v0 = Day 2.

## 1. Problem statement

Enterprises have knowledge scattered across documents, databases, and tools. Answering a real question ("summarize Q3 risk from these 40 PDFs and draft an email to the team") requires **reasoning + retrieval + tool use + multiple steps**, not a single LLM call.

This project builds an **agentic operating system**: a planner coordinates specialist agents that retrieve knowledge (RAG + knowledge graph), call tools (web, Python, SQL, files), remember past work, and are reviewed by a critic before returning an answer — all measured by an automated evaluation harness.

**Non-goal:** being a chatbot. The differentiator is *verifiable* multi-step task execution.

## 2. Success criteria (how we know it works)

The whole project is designed around these numbers. They live in the README and are produced by `make eval`.

| Metric | What it measures | Target (v1) |
|---|---|---|
| Retrieval recall@5 | Did we fetch the right chunks? | > 0.85 |
| Answer correctness (LLM-judge) | Is the answer right? | > 0.80 |
| Citation accuracy | Do citations point to real supporting text? | > 0.90 |
| Multi-step task success rate | Did the agent complete the full task? | > 0.70 |
| p95 latency | Responsiveness | < 15s |
| Cost / task | Token efficiency | tracked, trending down |
| Hallucination rate | Unsupported claims | < 0.10 |

## 3. Architecture

### 3.1 Request flow
```
Client (Next.js) ──HTTP/SSE──▶ FastAPI
                                  │
                                  ▼
                          ┌───────────────┐
                          │ Planner Agent │  decompose task → ordered steps
                          └───────┬───────┘
                                  ▼
        ┌────────────┬────────────┼────────────┬────────────┐
        ▼            ▼            ▼            ▼            ▼
   Research      Coding        Data/SQL     Browser     (extensible)
    Agent         Agent         Agent        Agent
        └────────────┴──────┬─────┴────────────┴────────────┘
                            ▼
                     Tool Layer  (web search · python exec · sql · file ops)
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
      RAG               Memory            Knowledge Graph
 (hybrid + cite)   (vector + history)      (Neo4j)
                            │
                            ▼
                   ┌─────────────────┐
                   │ Critic/Reviewer │  validate → retry (max N) or finish
                   └─────────────────┘
```

### 3.2 Agent responsibilities
- **Planner** — turns a goal into an ordered, typed plan; decides which agent/tool handles each step.
- **Research** — retrieval-heavy Q&A over RAG + knowledge graph; always cites.
- **Coding** — writes/executes Python in a sandbox; returns results, not just code.
- **Data/SQL** — translates questions to SQL, runs against Postgres, interprets results.
- **Browser** — live web search/navigation when the answer isn't in the corpus.
- **Critic/Reviewer** — checks each result against the step's intent; triggers a bounded retry loop or approves.

### 3.3 State (LangGraph)
A shared typed state object flows through the graph:
```
State = {
  goal: str,
  plan: list[Step],
  cursor: int,
  scratchpad: list[Message],
  tool_results: list[ToolResult],
  memory_hits: list[MemoryItem],
  verdict: Literal["retry", "done"] | None,
  cost: {tokens, usd},
}
```

## 4. Key components

### 4.1 RAG
- Ingestion: PDF/DOCX/PPTX/XLSX → clean text → recursive chunking (with overlap).
- Retrieval: **hybrid** = dense (embeddings in Qdrant) + sparse (BM25), fused with Reciprocal Rank Fusion, then cross-encoder reranking.
- Answers are **citation-aware**: every claim maps to a source chunk; citation accuracy is measured.

### 4.2 Memory
- **Episodic:** every run (goal, steps, result) persisted in Postgres — full task history.
- **Semantic:** summaries embedded in Qdrant so the agent recalls relevant past work.
- **Preferences:** user settings injected into prompts.

### 4.3 Knowledge graph
- LLM extracts entities/relations from ingested docs → Neo4j.
- A Cypher query tool lets agents answer relationship questions RAG handles poorly ("which projects is Person X connected to?").

### 4.4 Fine-tuning
- LoRA/QLoRA on Qwen or Llama for one focused task (candidate: reliable tool-call formatting).
- Measured **before/after** on a held-out set — reported in README.

### 4.5 Evaluation harness (the backbone)
- Labeled datasets in `eval/datasets/`.
- Scorers: retrieval recall, LLM-judge correctness, citation accuracy, task success, latency, cost, hallucination.
- `make eval` prints a table and (later) CI uploads it as an artifact.

## 5. Tech choices & trade-offs

| Decision | Choice | Why (one line) | Rejected alt |
|---|---|---|---|
| Agent framework | LangGraph | Explicit, debuggable state machine; good for critic/retry loops | CrewAI (less control), raw loops (more boilerplate) |
| Vector DB | Qdrant | Fast, open-source, easy local Docker, hybrid-friendly | Pinecone (paid/hosted), Milvus (heavier ops) |
| Backend | FastAPI | Async, streaming, typed, industry standard | Flask (no async-first) |
| Fine-tune | LoRA/QLoRA | Fits one GPU, cheap, reversible adapters | Full fine-tune (cost/compute) |
| Graph DB | Neo4j | Mature Cypher, great for relation queries | Building on Postgres (weaker graph ergonomics) |

*(Each row gets a fuller paragraph in the README's "Design decisions" section as it's built.)*

## 6. Scope discipline

- **Built deeply:** multi-agent orchestration, RAG, tools, memory, eval harness, API.
- **Built if time allows:** fine-tuning, knowledge graph, browser agent, frontend.
- **Designed but not fully built:** full Kubernetes/Helm/auto-scaling, Kafka, RL feedback — documented as a scale-out design, run locally via docker-compose.

Rationale: depth + proof beats a broad, shallow feature checklist for senior reviewers.

## 7. Milestones (see full daily plan)
- **M1** RAG + eval harness (proof it works)
- **M2** Multi-agent + tools + memory
- **M3** Fine-tuning + knowledge graph + observability
- **M4** Security + frontend + deploy + packaging

## 8. Open questions / risks
- Sandbox security for Python tool execution (isolate hard).
- LLM-judge reliability — spot-check against human labels.
- Cost control on multi-step runs — enforce token budgets + caching.
- Fine-tune task selection — must show a *clear* measurable win.

## 9. GraphRAG (knowledge graph) — in progress

**Why.** Dense + BM25 retrieval finds *similar text*, but can't answer
relational questions ("which projects share a dependency?", "who reports to
whom, two hops up?"). A knowledge graph makes entities and their relationships
first-class, so those queries become graph traversals instead of guesswork.

**Store.** Neo4j (community), reached over the Bolt protocol. A thin
`app/graph/client.py` wrapper mirrors the Qdrant wrapper: a cached, pooled
driver (the driver owns its own connection pool), a `graph_session` context
manager that always closes, and a `run_query` helper that returns plain dicts.
Config lives in `Settings` (`neo4j_uri/user/password`); tests monkeypatch the
driver so no live DB is needed in CI.

**Model.** Nodes: `Entity {name, type}` and `Chunk {id}`. Edges: typed
`RELATION` triples between entities, plus `MENTIONED_IN` linking an entity back
to its source chunk (so graph answers stay citable).

**Extraction (built).** Two LLM passes over a chunk — entities first, then
subject–predicate–object relations *between those entities* (`app/graph/
extract.py`). Names are normalized and deduped (`normalize.py`), relations whose
endpoints aren't known entities are dropped, and malformed LLM output parses to
an empty list rather than crashing. `chat_fn` is injectable, so the whole path
is unit-tested with a fake LLM. Next: MERGE these into Neo4j (idempotent ingest).

**Retrieval (built).** Match query entities → pull their k-hop neighborhood →
serialize the subgraph to text. In parallel, chunks are ranked by how many
query-entities they mention, and that ranking is RRF-fused with the vector/BM25
hits (keyed by source). The fused prompt puts graph facts above passages.
Exposed as a `graph_search` tool and an `/ask?mode=vector|graph|fused` switch.

**Evaluation & routing (built).** `make graph-eval` scores answers by
fact-coverage over a graph-QA set (`eval/datasets/graph_qa.json`). A cheap
relational-goal heuristic (`app/graph/routing.py`) detects relationship/
multi-hop phrasing and injects a hint so the planner steers the executor toward
`graph_search`. Coverage numbers depend on a live graph + LLM; the harness and
routing are unit-tested offline with fakes.

| GraphRAG piece | Status | Proof |
|---|---|---|
| Entity/relation extraction | built | `test_graph_extract.py` |
| Idempotent ingest (MERGE + chunk links) | built | `test_graph_ingest.py` |
| k-hop retrieval + serialization | built | `test_graph_retrieval.py` |
| RRF fusion (RAG + graph) | built | `test_graph_fusion.py` |
| `graph_search` tool + `/ask` modes | built | `test_graph_fusion.py` |
| Eval harness + relational routing | built | `test_graph_routing_eval.py` |

## 10. Feedback loop (learning from users) — in progress

The "learn from feedback" component is scoped as **DPO + a feedback-driven
reranker**, not RLHF — a tractable, defensible design.

**Collection (built).** Every answer card has 👍 / 👎 buttons; a 👎 can include
a suggested better answer. `POST /feedback` persists a row (`app/feedback/`):
`{run_id?, query, answer, rating, better_answer?, ts}` via async SQLAlchemy, so
it works on SQLite (dev) or Postgres (prod). The endpoint validates the rating
and is unit-tested with a faked store; the store is tested on in-memory SQLite.

**Use (building this week).**
- *Reranker signal:* 👍/👎 on answers whose passages are known become
  (query, passage, label) pairs to train a lightweight learned reranker that
  augments the current LLM reranker (cold-start falls back to the LLM).
- *DPO pairs:* a 👎 with a `better_answer` gives a (chosen, rejected) pair;
  a 👍 answer can be the chosen against a weaker candidate. Exported as JSONL
  for offline preference tuning (Week 4).

Everything is measured: reranker-on vs -off enters the ablation table, so the
loop has to *demonstrate* a win, not just exist.

---
*v3 — feedback collection built (Week 2, Day 9). Next: feedback reranker + DPO export.*
