"""FastAPI entrypoint. Endpoints grow through the roadmap."""
from fastapi import FastAPI

from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title="Enterprise Agentic AI OS", version="0.1.0")


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
        "llm_key_configured": bool(settings.openai_api_key or settings.llm_base_url),
    }
