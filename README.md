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
