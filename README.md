# Enterprise Agentic AI OS

![CI](https://github.com/zda25m005-netizen/agentic-ai-os/actions/workflows/ci.yml/badge.svg)

> A production-grade, multi-agent AI platform that reasons, plans, and executes complex tasks over enterprise data — with hybrid retrieval, tool use, long-term memory, and a real evaluation harness.

**Status:** 🚧 In active development. Building in public — one commit a day.

---

## Why this project

Most "AI agent" portfolios wire tutorials together and can't prove anything works. This one is built around **measurement**: every capability ships with an automated evaluation and real numbers.

## Evaluation

Run end-to-end with `make eval` — ingests a labeled corpus, answers every question with the real hybrid-retrieval + citation pipeline, and scores against gold labels.

| Metric | Score |
|---|---|
| Retrieval recall@5 | **100%** |
| Answer correctness (LLM-judge) | **100%** |
| Answer match (exact substring) | **93%** |
| Citation accuracy | **100%** |

*Measured on a 15-question labeled set (`eval/datasets/`) with `gpt-4o-mini` + `text-embedding-3-small`. Reproduce with `make eval`. The eval set is being expanded.*

### Agent evaluation

The multi-agent graph, scored on multi-step goals (`eval/datasets/agent_tasks.json`). Reproduce with `python -m eval.agent_eval`.

| Metric | Score |
|---|---|
| Task success rate | **100%** |
| Step completion rate | **100%** |
| Avg steps / task | 3.2 |

*Measured on 5 multi-step tasks with `gpt-4o-mini`.*

### Retrieval ablation — why hybrid + reranker

Controlled comparison on a purpose-built 10-document benchmark with deliberately hard queries: exact identifiers (SKU codes, cipher names) that favor keyword search, and paraphrased queries that favor dense vectors. Reproduce with `make ablation`.

| Retrieval strategy | Recall@1 | Recall@3 |
|---|---|---|
| Vector only (dense) | 100% | 100% |
| BM25 only (sparse) | 80% | 90% |
| Hybrid (RRF) | 90% | 100% |
| Hybrid + reranker | 100% | 100% |

**Analysis.** On this small, clean corpus a strong embedding model already saturates dense retrieval, so vector-only is a hard baseline. Fusing BM25 via RRF slightly dilutes the dense signal at rank 1 (90%); adding an LLM reranker recovers it to 100%. BM25 alone is weakest, confirming keyword matching is insufficient for paraphrased queries. The default configuration is hybrid + reranker; the advantage of hybrid/BM25 grows on larger, noisier, or identifier-heavy corpora and with weaker embedding models.

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for full diagrams, [`docs/DESIGN.md`](docs/DESIGN.md) for design & trade-offs.

## RAG pipeline

Ingest: `load (PDF/DOCX/PPTX/XLSX) -> recursive chunk (overlap) -> embed -> store (Qdrant)`
Retrieve: `dense (vector) + sparse (BM25) -> RRF fusion -> grounded answer -> inline [n] citations`

## Tech stack

| Layer | Choice |
|---|---|
| LLM | OpenAI-compatible (GPT-4o-mini) · Qwen/Llama LoRA planned |
| Backend | FastAPI |
| Vector DB | Qdrant |
| Retrieval | Hybrid: dense + BM25 (from scratch) fused with RRF |
| Agents / KG / Frontend | LangGraph · Neo4j · Next.js (planned) |

## API

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness probe |
| GET | `/config` | Non-secret runtime config |
| POST | `/chat` | Single-turn chat with the LLM |
| POST | `/ask` | RAG: grounded, citation-aware answer over ingested docs |
| POST | `/agent` | Multi-agent: plan -> execute -> critique -> answer |

## Quickstart

```bash
git clone https://github.com/zda25m005-netizen/agentic-ai-os.git
cd agentic-ai-os
cp .env.example .env        # add your OPENAI_API_KEY
make install
make run                    # FastAPI on :8000
make test                   # run tests
make eval                   # run the evaluation harness
```

## Roadmap

Built over ~4 months, daily commits. Done: ingestion, hybrid RAG, citations, eval harness. Next: multi-agent orchestration, tools, memory, fine-tuning, observability, frontend. See [`docs/DESIGN.md`](docs/DESIGN.md).

## License

MIT — see [LICENSE](LICENSE).
