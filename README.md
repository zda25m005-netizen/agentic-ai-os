# Enterprise Agentic AI OS

> A production-grade, multi-agent AI platform that reasons, plans, and executes complex tasks over enterprise data — with retrieval, tool use, long-term memory, and a real evaluation harness.

**Status:** 🚧 In active development (Day 1). Building in public — one commit a day.

---

## Why this project

Most "AI agent" portfolios wire tutorials together and can't prove anything works. This one is built around **measurement**: every capability ships with an automated evaluation and real numbers (task success rate, latency, cost per task, citation accuracy).

## Planned architecture (high level)

```
User → API (FastAPI) → Planner Agent
                          │
        ┌─────────────────┼─────────────────┐
     Research          Coding            Data/SQL
      Agent             Agent             Agent
        └─────────────────┼─────────────────┘
                     Tool Layer (web, python, sql, files)
                          │
              RAG (hybrid search + citations)  ·  Memory (vector + history)  ·  Knowledge Graph
                          │
                     Critic / Reviewer  → retry or finish
```

Full design in [`docs/DESIGN.md`](docs/DESIGN.md).

## Tech stack

| Layer | Choice |
|---|---|
| LLM | Qwen / Llama (fine-tuned via LoRA) + hosted API |
| Agents | LangGraph |
| Backend | FastAPI |
| Vector DB | Qdrant |
| Knowledge Graph | Neo4j |
| Database | PostgreSQL |
| Observability | Langfuse + OpenTelemetry + Prometheus/Grafana |
| Frontend | Next.js + TypeScript |

## Evaluation (results will appear here)

| Metric | Baseline | Current |
|---|---|---|
| Retrieval recall@5 | — | — |
| Answer correctness | — | — |
| Citation accuracy | — | — |
| Multi-step task success | — | — |
| p95 latency | — | — |
| Cost / task | — | — |

## Quickstart

```bash
git clone <your-repo-url>
cd agentic-ai-os
cp .env.example .env        # add your API keys
make install
make run                    # starts FastAPI on :8000
```

## Roadmap

See [`docs/DESIGN.md`](docs/DESIGN.md). Built over ~4 months, daily commits.

## License

MIT — see [LICENSE](LICENSE).
