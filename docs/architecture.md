# Architecture

Diagrams render automatically on GitHub (Mermaid).

## System overview

```mermaid
flowchart TB
    UI["Client<br/>(Next.js chat + dashboard)"] -->|HTTP / SSE| API["FastAPI<br/>auth · rate limit · streaming"]

    API --> PL["Planner Agent<br/>decompose goal into steps"]

    PL --> RES["Research Agent"]
    PL --> COD["Coding Agent"]
    PL --> SQL["Data / SQL Agent"]
    PL --> BR["Browser Agent"]

    RES --> TL["Tool Layer"]
    COD --> TL
    SQL --> TL
    BR --> TL

    TL --> T1["Web search"]
    TL --> T2["Python exec"]
    TL --> T3["SQL"]
    TL --> T4["File ops"]

    RES --> RAG["RAG<br/>hybrid search + citations"]
    RES --> KG["Knowledge Graph<br/>Neo4j"]
    PL --> MEM["Memory<br/>vector + task history"]

    RAG --> VDB[("Qdrant")]
    MEM --> VDB
    MEM --> PG[("Postgres")]
    KG --> NEO[("Neo4j")]

    RES --> CR["Critic / Reviewer<br/>validate → retry or finish"]
    COD --> CR
    SQL --> CR
    CR -->|approved| API
    CR -.->|retry (max N)| PL

    API --> OBS["Observability<br/>Langfuse · OTel · Prometheus"]
```

## Request lifecycle (a single task)

```mermaid
sequenceDiagram
    participant U as User
    participant A as API (FastAPI)
    participant P as Planner
    participant W as Worker Agent
    participant T as Tools / RAG
    participant C as Critic

    U->>A: POST /task {goal}
    A->>P: plan(goal)
    P-->>A: ordered steps
    loop for each step
        A->>W: execute(step)
        W->>T: call tool / retrieve context
        T-->>W: results (+ citations)
        W-->>C: proposed result
        alt result passes
            C-->>A: approved
        else needs work
            C-->>P: retry with feedback
        end
    end
    A-->>U: final answer + citations + trace
```

## Evaluation loop (how we prove it works)

```mermaid
flowchart LR
    DS["Labeled datasets<br/>eval/datasets/*.json"] --> RUN["make eval"]
    RUN --> SC["Scorers"]
    SC --> M1["Retrieval recall@k"]
    SC --> M2["Answer correctness<br/>(LLM-judge)"]
    SC --> M3["Citation accuracy"]
    SC --> M4["Task success rate"]
    SC --> M5["Latency p50/p95 · cost/task"]
    M1 --> REP["Metrics table<br/>→ README + CI artifact"]
    M2 --> REP
    M3 --> REP
    M4 --> REP
    M5 --> REP
```

See [DESIGN.md](DESIGN.md) for component details and trade-offs.
