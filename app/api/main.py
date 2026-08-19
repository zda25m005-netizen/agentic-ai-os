"""FastAPI entrypoint. Endpoints grow through the roadmap."""
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

import app.missions.models  # noqa: F401  (register mission tables on Base)
from app.agents.graph import run_agent
from app.api.missions import router as missions_router
from app.core import auth, llm
from app.core.config import get_settings
from app.db import session as db
from app.feedback import store as feedback_store
from app.finetune import serving
from app.graph import fusion
from app.graph.retrieval import get_graph_context, graph_chunk_hits
from app.obs import health, langfuse_export, logging_setup, tracing
from app.obs import metrics as obs_metrics
from app.rag import citations, retriever, vectorstore

settings = get_settings()
logging_setup.configure_logging(settings.log_level)
_access_log = logging.getLogger("agentic.access")

@asynccontextmanager
async def _lifespan(_app: FastAPI):
    """Best-effort create of mission tables at boot (no-op if the DB is down)."""
    try:
        await db.init_models(db.get_engine())
    except Exception as exc:  # never block startup on a cold database
        logging.getLogger("agentic").warning("mission table init skipped: %s", exc)
    yield


app = FastAPI(title="Enterprise Agentic AI OS", version="0.1.0", lifespan=_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(missions_router)


@app.middleware("http")
async def _observability_middleware(request: Request, call_next):
    """Assign a request id, record Prometheus metrics, and JSON-log the request."""
    request_id = uuid.uuid4().hex[:12]
    logging_setup.set_request_id(request_id)
    t0 = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - t0) * 1000.0
    obs_metrics.observe_request(
        request.url.path, request.method, response.status_code, duration_ms / 1000.0
    )
    response.headers["X-Request-ID"] = request_id
    _access_log.info(
        "request",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": round(duration_ms, 2),
        },
    )
    return response


@app.get("/metrics")
def metrics_endpoint() -> Response:
    """Prometheus scrape endpoint."""
    payload, content_type = obs_metrics.render()
    return Response(content=payload, media_type=content_type)


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
    mode: str = "vector"  # vector | graph | fused (GraphRAG)


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


class FeedbackRequest(BaseModel):
    query: str
    answer: str
    rating: str  # "up" | "down"
    run_id: str | None = None
    better_answer: str | None = None


class FeedbackResponse(BaseModel):
    id: int
    status: str = "recorded"


class TokenRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


_bearer = HTTPBearer(auto_error=True)


def current_user(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),  # noqa: B008
) -> dict:
    """Decode the bearer token; raise 401 if missing/invalid/expired."""
    try:
        return auth.decode_token(creds.credentials)
    except auth.AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def require_role(role: str):
    """Dependency factory: require the caller to have a specific role."""

    def checker(user: dict = Depends(current_user)) -> dict:  # noqa: B008
        if user.get("role") != role:
            raise HTTPException(status_code=403, detail=f"requires {role} role")
        return user

    return checker


_require_admin = require_role("admin")


@app.post("/token", response_model=TokenResponse)
def token(req: TokenRequest) -> TokenResponse:
    """Exchange username/password for a signed JWT."""
    role = auth.verify_credentials(req.username, req.password)
    if role is None:
        raise HTTPException(status_code=401, detail="invalid credentials")
    return TokenResponse(
        access_token=auth.create_access_token(req.username, role=role), role=role
    )


@app.get("/me")
def me(user: dict = Depends(current_user)) -> dict:  # noqa: B008
    """Return the authenticated user (requires a valid token)."""
    return {"username": user.get("sub"), "role": user.get("role")}


@app.get("/admin/stats")
async def admin_stats(user: dict = Depends(_require_admin)) -> dict:  # noqa: B008
    """Admin-only stats: feedback counts (RBAC)."""
    return {
        "ok": True,
        "viewer": user.get("sub"),
        "feedback": await feedback_store.summary(),
    }


@app.get("/health")
def health_endpoint() -> dict:
    """Liveness probe (the process is up)."""
    return {"status": "ok", "version": app.version}


@app.get("/readyz")
async def readyz() -> dict:
    """Readiness probe: are backing services (qdrant/neo4j/postgres) reachable?"""
    return await health.check_all()


@app.get("/config")
def config() -> dict:
    """Non-secret runtime config (useful for debugging deployments)."""
    return {
        "app_env": settings.app_env,
        "llm_model": settings.llm_model,
        "embedding_model": settings.embedding_model,
        "qdrant_url": settings.qdrant_url,
        "llm_key_configured": llm.is_configured(),
        "active_model": serving.model_display_name(serving.model_label()),
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
        reply, label = await serving.answer(messages)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"LLM call failed: {exc}") from exc

    return ChatResponse(reply=reply, model=serving.model_display_name(label))


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest) -> AskResponse:
    """Answer a question grounded in retrieved documents, with citations."""
    if not llm.is_configured():
        raise HTTPException(
            status_code=503,
            detail="LLM not configured. Set OPENAI_API_KEY or LLM_BASE_URL in .env",
        )

    # Graph-only mode: answer purely from knowledge-graph facts.
    if req.mode == "graph":
        try:
            gctx = await get_graph_context(req.question)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(502, f"Knowledge graph unavailable: {exc}") from exc
        if not gctx.triples:
            return AskResponse(
                answer="I don't know — no related facts found in the knowledge graph.",
                citations=[],
                sources=[],
            )
        try:
            answer = await llm.chat(
                fusion.build_graphrag_messages(req.question, [], gctx.text)
            )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(502, f"LLM call failed: {exc}") from exc
        return AskResponse(answer=answer, citations=[], sources=[])

    client = vectorstore.get_client()
    hits = await retriever.retrieve(
        req.question, client, collection=req.collection, limit=req.top_k
    )

    # Fused (GraphRAG) mode: RRF-merge graph chunk hits with the vector hits and
    # prepend graph facts. Degrades to plain vector answer if the graph is down.
    graph_text = ""
    if req.mode == "fused":
        try:
            graph_text = (await get_graph_context(req.question)).text
            ghits = await graph_chunk_hits(req.question, limit=req.top_k * 2)
            hits = fusion.fuse_hits(hits, ghits, limit=req.top_k)
        except Exception:  # noqa: BLE001
            graph_text = ""

    if not hits:
        return AskResponse(
            answer="I don't know — no relevant documents found.",
            citations=[],
            sources=[],
        )

    messages = (
        fusion.build_graphrag_messages(req.question, hits, graph_text)
        if req.mode == "fused"
        else citations.build_messages(req.question, hits)
    )
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


@app.post("/feedback", response_model=FeedbackResponse)
async def feedback(req: FeedbackRequest) -> FeedbackResponse:
    """Record a thumbs up/down (and optional better answer) on an answer."""
    if req.rating not in feedback_store.VALID_RATINGS:
        raise HTTPException(
            status_code=422,
            detail=f"rating must be one of {feedback_store.VALID_RATINGS}",
        )
    try:
        fid = await feedback_store.record(
            req.query, req.answer, req.rating,
            run_id=req.run_id, better_answer=req.better_answer,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"could not save feedback: {exc}") from exc
    return FeedbackResponse(id=fid)


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
        # Best-effort: export the full trace to Langfuse (no-op unless configured).
        try:
            langfuse_export.export_trace(trace, name="agent-run", metadata={"goal": req.goal})
        except Exception:  # noqa: BLE001 - observability must never break the request
            pass
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
