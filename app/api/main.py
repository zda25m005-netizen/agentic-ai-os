"""FastAPI entrypoint. Day 1 skeleton — endpoints grow through the roadmap."""
from fastapi import FastAPI

app = FastAPI(title="Enterprise Agentic AI OS", version="0.1.0")


@app.get("/health")
def health() -> dict:
    """Liveness probe."""
    return {"status": "ok", "version": app.version}
