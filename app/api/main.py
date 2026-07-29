"""FastAPI entrypoint. Endpoints grow through the roadmap."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.agents.graph import run_agent
from app.core import llm
from app.core.config import get_settings
from app.obs import tracing
from app.rag import citations, retriever, vectorstore

settings = get_settings()

app = FastAPI(title="Enterprise Agentic AI OS", version="0.1.0")


class ChatRequest(BaseModel):
    message: str
    system: str | None = None


class ChatResponse(BaseModel):
    reply: str
    model: str


class Source(BaseModel):
    source: str
    chunk_index: int | None = None
    score: float


class CitationOut(BaseModel):
    marker: int
    source: str
    chunk_index: int | None = None
    score: float


class AskRequest(BaseModel):
    question: str
    collection: str = retriever.DEFAULT_COLLECTION
    top_k: int = 5


class AskResponse(BaseModel):
    answer: str
    citations: list[CitationOut]
    sources: list[Source]


class Metrics(BaseModel):
    spans: int
    total_ms: float
    prompt_tokens: int
    completion_tokens: int
    est_cost_usd: float


class AgentRequest(BaseModel):
    goal: str


class AgentStepOut(BaseModel):
    id: int
    description: str
    agent: str
    status: str


class AgentResponse(BaseModel):
    answer: str
    steps: list[AgentStepOut]
    trace: list[str]
    metrics: Metrics


@app.get("/health")
def health() -> dict:
    """Liveness probe."""
    return {"status": "ok", "version": app.version}


@app.get("/config")
def config() -> dict:
    """Non-secret runtime config (useful for debugging deployments)."""
    return {
        "app_env": settings.app_env,
        "llm_model": settings.llm_model,
        "embedding_model": settings.embedding_model,
        "qdrant_url": settings.qdrant_url,
        "llm_key_configured": llm.is_configured(),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """Single-turn chat with the configured LLM."""
    if not llm.is_configured():
        raise HTTPException(
            status_code=503,
            detail="LLM not configured. Set OPENAI_API_KEY or LLM_BASE_URL in .env",
        )
    messages = []
    if req.system:
        messages.append({"role": "system", "content": req.system})
    messages.append({"role": "user", "content": req.message})

    try:
        reply = await llm.chat(messages)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"LLM call failed: {exc}") from exc

    return ChatResponse(reply=reply, model=settings.llm_model)


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest) -> AskResponse:
    """Answer a question grounded in retrieved documents, with citations."""
    if not llm.is_configured():
        raise HTTPException(
            status_code=503,
            detail="LLM not configured. Set OPENAI_API_KEY or LLM_BASE_URL in .env",
        )

    client = vectorstore.get_client()
    hits = await retriever.retrieve(
        req.question, client, collection=req.collection, limit=req.top_k
    )
    if not hits:
        return AskResponse(
            answer="I don't know — no relevant documents found.",
            citations=[],
            sources=[],
        )

    messages = citations.build_messages(req.question, hits)
    try:
        answer = await llm.chat(messages)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"LLM call failed: {exc}") from exc

    cited = citations.parse_citations(answer, hits)
    citation_out = [
        CitationOut(
            marker=c.marker,
            source=c.source,
            chunk_index=c.chunk_index,
            score=c.score,
        )
        for c in cited
    ]
    sources = [
        Source(
            source=h.payload.get("source", "unknown"),
            chunk_index=h.payload.get("chunk_index"),
            score=h.score,
        )
        for h in hits
    ]
    return AskResponse(answer=answer, citations=citation_out, sources=sources)


@app.post("/agent", response_model=AgentResponse)
async def agent(req: AgentRequest) -> AgentResponse:
    """Run the multi-agent graph on a goal; report latency, tokens, and cost."""
    if not llm.is_configured():
        raise HTTPException(
            status_code=503,
            detail="LLM not configured. Set OPENAI_API_KEY or LLM_BASE_URL in .env",
        )

    trace = tracing.start_trace()
    try:
        state = await tracing.traced("agent.run", run_agent(req.goal))
        summary = trace.summary()
    finally:
        tracing.clear_trace()

    steps = [
        AgentStepOut(
            id=s.get("id", i),
            description=s.get("description", ""),
            agent=s.get("agent", "research"),
            status=s.get("status", "pending"),
        )
        for i, s in enumerate(state.get("plan", []))
    ]
    trace_lines = [f"{m['node']}: {m['content']}" for m in state.get("scratchpad", [])]
    metrics = Metrics(
        spans=summary["spans"],
        total_ms=summary["total_ms"],
        prompt_tokens=summary["prompt_tokens"],
        completion_tokens=summary["completion_tokens"],
        est_cost_usd=summary["est_cost_usd"],
    )
    return AgentResponse(
        answer=state.get("answer", ""), steps=steps, trace=trace_lines, metrics=metrics
    )
