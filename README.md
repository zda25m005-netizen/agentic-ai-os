# Enterprise Agentic AI OS

![CI](https://github.com/zda25m005-netizen/agentic-ai-os/actions/workflows/ci.yml/badge.svg)

> A retrieval-augmented, multi-agent AI system with a **rigorous, reproducible evaluation harness** — built and measured, not just assembled.

Two working systems, both benchmarked: a hybrid-RAG engine that answers questions over documents with citations, and a LangGraph multi-agent orchestrator that plans, calls real tools, and self-critiques. Every capability ships with an automated eval and real numbers.

**Status:** actively developed, built in public — one commit a day, ~190 tests, green CI.

---

## What's built and proven

- **Hybrid RAG** — PDF/DOCX/PPTX/XLSX ingestion → recursive chunking → dense + BM25 retrieval fused with RRF → LLM reranker → grounded, **citation-aware** answers. *Measured: 100% retrieval recall@5, 100% answer correctness.*
- **Multi-agent orchestrator** — Planner → Executor → Critic graph (LangGraph) with a bounded retry loop and a **function-calling tool-use loop** across 11 tools. *Measured: 100% task success on multi-step goals.*
- **Evaluation harness** — labeled datasets, automated scorers (recall, LLM-judge correctness, citation accuracy), and a **retrieval ablation** comparing strategies. One command: `make eval`, `make ablation`.

## Demo

The agent plans a goal, calls a tool, self-critiques, and reports its own latency and cost — and hybrid RAG returns a grounded answer with citations.

| Multi-agent + tools (`/agent`) | Hybrid RAG + citations (`/ask`) |
|---|---|
| ![Agent demo](docs/images/agent-demo.png) | ![RAG demo](docs/images/rag-demo.png) |

## Evaluation

Everything below is reproducible from the repo.

### RAG quality (`make eval`)

| Metric | Score |
|---|---|
| Retrieval recall@5 | **100%** |
| Answer correctness (LLM-judge) | **100%** |
| Answer match (exact substring) | 93% |
| Citation accuracy | **100%** |

*15-question labeled set (`eval/datasets/`), `gpt-4o-mini` + `text-embedding-3-small`.*

### Agent task success (`python -m eval.agent_eval`)

| Metric | Score |
|---|---|
| Task success rate | **100%** |
| Step completion rate | **100%** |
| Avg steps / task | 3.2 |

*5 multi-step goals.*

### Retrieval ablation (`make ablation`)

A controlled comparison on a purpose-built 10-doc benchmark with hard queries — exact identifiers (SKU codes) that favor keyword search, and paraphrases that favor dense vectors.

| Retrieval strategy | Recall@1 | Recall@3 |
|---|---|---|
| Vector only (dense) | 100% | 100% |
| BM25 only (sparse) | 80% | 90% |
| Hybrid (RRF) | 90% | 100% |
| **Hybrid + reranker** | **100%** | **100%** |

**Analysis.** On this small, clean corpus a strong embedding model saturates dense retrieval, so vector-only is a hard baseline. Fusing BM25 via RRF dilutes the dense signal at rank 1 (90%); an LLM reranker recovers it to 100%. BM25 alone is weakest, confirming keyword matching is insufficient for paraphrases. The advantage of hybrid/BM25 grows on larger, noisier, or identifier-heavy corpora and with weaker embedding models — this benchmark honestly shows where each method wins.

## Architecture

```mermaid
flowchart TB
    UI["Client / API (FastAPI)"] --> PL["Planner"]
    PL --> EX["Executor (tool-use loop)"]
    EX --> TOOLS["11 tools: web · python · sql · rag · files · ..."]
    EX --> CR["Critic (bounded retries)"]
    CR -->|approve| FIN["Finalize"]
    CR -.->|retry| EX
    EX --> RAG["Hybrid RAG + reranker"]
    RAG --> VDB[("Qdrant")]
```

Full diagrams in [docs/architecture.md](docs/architecture.md) · design & trade-offs in [docs/DESIGN.md](docs/DESIGN.md).

## Tools (12, all tested)

`calculator` · `web_search` · `python_exec` (sandboxed) · `sql_query` (read-only) · `rag_search` · `graph_search` (knowledge graph) · `current_datetime` · `http_get` (SSRF-guarded) · `wikipedia` · `file_read/write/list` (path-traversal guarded) · `analyze_csv` (pandas) · `delegate` (recursive sub-agent).

Adding a tool is ~40 lines: an async function + a `@tool` decorator with a JSON schema. The registry exposes them as OpenAI function-calling specs; the agent picks and invokes them autonomously.

## API

| Method | Path | Description |
|---|---|---|
| GET | `/health` · `/config` | Liveness / runtime config |
| POST | `/chat` | Single-turn chat |
| POST | `/ask` | Hybrid RAG with inline citations |
| POST | `/agent` | Multi-agent: plan → tool use → critique → answer |
| POST | `/feedback` | Record 👍/👎 (+ optional better answer) on an answer |
| GET | `/metrics` | Prometheus scrape endpoint |

## Metrics (Prometheus)

`GET /metrics` exposes process-wide counters/histograms for scraping:

| Metric | Type | Labels | Meaning |
|---|---|---|---|
| `agentic_requests_total` | counter | endpoint, method, status | HTTP requests |
| `agentic_request_latency_seconds` | histogram | endpoint | request latency |
| `agentic_llm_tokens_total` | counter | type (prompt/completion) | LLM tokens used |
| `agentic_llm_cost_usd_total` | counter | — | estimated LLM spend |
| `agentic_agent_node_runs_total` | counter | node | planner/executor/critic/finalize runs |
| `agentic_tool_calls_total` | counter | tool | tool invocations |

A request-timing middleware records the HTTP series; token/cost are emitted from
the LLM client; node/tool counters from the agent graph and tool registry.

Compose ships a full monitoring stack: **Prometheus** scrapes `/metrics`, and
**Grafana** comes pre-provisioned with Prometheus as its default datasource.

```bash
docker compose up -d prometheus grafana
# Prometheus  → http://localhost:9090   (targets: api:8000/metrics)
# Grafana     → http://localhost:3001   (admin / admin)
```

## Tech stack

**Built:** FastAPI · Qdrant · hybrid retrieval (dense + BM25 + RRF + LLM reranker) · Neo4j GraphRAG (entity/relation extraction, k-hop retrieval, RRF fusion, `graph_search` tool, `/ask?mode=graph|fused`) · LangGraph agents · function-calling tool loop · pytest/CI · Docker Compose.

GraphRAG has its own eval harness (`make graph-eval`, fact-coverage over a graph-QA set) and a relational-goal router that steers the planner to `graph_search`. Design in [docs/DESIGN.md](docs/DESIGN.md) §9.

**Designed / roadmap (not yet built):** LoRA fine-tuning + DPO preference tuning · a feedback-driven reranker · Postgres-backed long-term memory · Prometheus/Grafana + Langfuse observability · Kubernetes/Helm deploy. These are scoped in [docs/DESIGN.md](docs/DESIGN.md) as design, not claimed as complete.

## Run the whole stack (Docker)

```bash
cp .env.example .env    # add OPENAI_API_KEY
docker compose up --build
# API on :8000, UI on :3000, Qdrant on :6333, Neo4j on :7474/:7687
```

## Database (Postgres)

Episodic long-term memory runs on either backend, chosen by `MEMORY_BACKEND`:
`sqlite` (default, zero-setup) or `postgres` (async SQLAlchemy 2.0 + asyncpg).
The Postgres store implements the same interface, so nothing else changes.
Config is a single `DATABASE_URL` (note the `+asyncpg` driver). Compose brings up
a `postgres` service automatically; tests run against in-memory SQLite (aiosqlite),
so no live database is needed in CI.

```bash
docker compose up -d postgres
# DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/agentic
# MEMORY_BACKEND=postgres
```

## Build the knowledge graph

With Neo4j running and an LLM configured, extract entities/relations from the
corpus and MERGE them into the graph (idempotent — safe to re-run):

```bash
docker compose up -d neo4j
python -m app.graph.cli --corpus eval/datasets/corpus.json
# Browse the graph at http://localhost:7474 (neo4j / neo4jpassword)
```

## Quickstart

```bash
git clone https://github.com/zda25m005-netizen/agentic-ai-os.git
cd agentic-ai-os
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env          # add OPENAI_API_KEY
make test                     # ~190 tests
make eval                     # RAG metrics
make ablation                 # retrieval comparison
make run                      # FastAPI on :8000
```

## Design notes & honesty

- Metrics are on small labeled sets (15 Q&A, 10-doc ablation, 5 agent tasks); they demonstrate the harness and current quality, and are being expanded — sample sizes are stated, not hidden.
- The "learn from feedback" component is scoped as **DPO + a feedback reranker** (a tractable, defensible alternative to full RLHF), not reinforcement learning.
- Kubernetes, Kafka, and knowledge-graph pieces are documented designs, deliberately not half-implemented.

## License

MIT — see [LICENSE](LICENSE).
