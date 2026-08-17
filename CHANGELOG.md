# Changelog

## v1.0.0 — Feature-complete

A full-stack, production-shaped agentic AI system. Built in public over five
weeks; every capability ships with tests and honest docs. **356 tests, green CI.**

### Retrieval
- **Hybrid RAG** — recursive chunking → dense embeddings + from-scratch BM25 →
  Reciprocal Rank Fusion → LLM reranker → citation-aware answers.
- **GraphRAG** — LLM entity/relation extraction → Neo4j → k-hop retrieval → RRF
  fusion with RAG → `graph_search` tool → `/ask?mode=vector|graph|fused`.

### Agents & tools
- LangGraph **Planner → Executor → Critic → Finalize** with a bounded retry loop.
- **Function-calling tool loop** across **12 tools** (web, python (sandboxed),
  sql (read-only), rag, graph, http (SSRF-guarded), files (path-guarded), …).
- Long-term memory: episodic (SQLite/Postgres) + semantic (Qdrant).

### Learning from feedback
- 👍/👎 collection → learned **feedback reranker** (LLM fallback) → **DPO**
  preference-pair export → measured on/off ablation. (DPO, not RLHF.)

### Fine-tuning
- SFT dataset builder → **LoRA training** (PEFT + TRL) + Colab notebook →
  loss-curve capture → adapter merge → **serve with API fallback** →
  base-vs-LoRA **before/after ablation** with auto-written analysis.

### Observability & security
- Prometheus `/metrics` + 3 provisioned **Grafana** dashboards + alert rules;
  optional **Langfuse** trace export; `/readyz` dependency health; structured
  JSON logs with request-id correlation.
- **JWT auth + RBAC**; per-request cost/latency/token accounting.

### Platform
- **Docker Compose** (7 services) and a **Kubernetes Helm chart** (dev/prod
  values, Ingress, API HPA, ConfigMap/Secret, non-root hardening,
  NetworkPolicies). CI **kind smoke-deploy** on every push; GHCR image publish on tags.

### Evaluation
- Automated harness: recall@k, LLM-judge correctness, citation accuracy, agent
  task-success, a discriminating retrieval **ablation**, GraphRAG fact-coverage,
  and reranker/fine-tune comparisons. Sample sizes stated, numbers not inflated.
