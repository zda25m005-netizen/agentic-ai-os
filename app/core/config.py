"""Application configuration, loaded from environment / .env.

Central, typed settings so the rest of the app never reads os.environ directly.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_env: str = Field(default="dev")
    log_level: str = Field(default="INFO")
    jwt_secret: str = Field(default="")

    # LLM
    openai_api_key: str = Field(default="")
    llm_base_url: str = Field(default="")
    llm_model: str = Field(default="gpt-4o-mini")

    # Embeddings
    embedding_model: str = Field(default="text-embedding-3-small")

    # Vector DB
    qdrant_url: str = Field(default="http://localhost:6333")

    # Graph DB (Neo4j)
    neo4j_uri: str = Field(default="bolt://localhost:7687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(default="neo4jpassword")

    # Postgres (async SQLAlchemy — note the +asyncpg driver)
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/agentic"
    )

    # Long-term memory backend: "sqlite" (default) or "postgres"
    memory_backend: str = Field(default="sqlite")

    # Langfuse tracing (optional; export runs when both keys are set)
    langfuse_public_key: str = Field(default="")
    langfuse_secret_key: str = Field(default="")
    langfuse_host: str = Field(default="https://cloud.langfuse.com")

    # Adzuna job-board API (optional; free key at developer.adzuna.com). When both
    # are set, the Job Search Agent returns real, country-scoped listings across
    # all domains/countries. Empty = provider stays off (Greenhouse/Lever only).
    adzuna_app_id: str = Field(default="")
    adzuna_app_key: str = Field(default="")

    # Jooble job-search API (optional; free key at jooble.org/api/about). When set,
    # adds a broad, country-aware aggregator source to the Job Search Agent.
    jooble_api_key: str = Field(default="")

    # Serve a locally fine-tuned model (falls back to the API model if missing)
    use_finetuned: bool = Field(default=False)
    finetuned_model_dir: str = Field(default="artifacts/lora-adapter-merged")

    # Background mission worker: drive active missions without a client request.
    worker_enabled: bool = Field(default=True)
    worker_poll_seconds: float = Field(default=2.0)

    # Distributed workers: Redis URL for the shared mission queue (empty = in-memory).
    redis_url: str = Field(default="")

    # Multi-agent execution (role prompts + critic/replan). Off by default so the
    # live demo stays fast (one LLM call/task); on = richer, self-critiquing runs.
    multi_agent_enabled: bool = Field(default=False)
    critic_threshold: float = Field(default=0.6)
    max_replans: int = Field(default=1)

    # Researcher tool-use: when on, researcher-role tasks call web_search and cite
    # the real URLs they find, so reports carry genuine sources (not 0). Off by
    # default so tests/CI never hit the network; enable for live/demo runs.
    research_enabled: bool = Field(default=False)
    research_max_results: int = Field(default=4)

    # Evidence-first report flow: build a structured Analysis Artifact and let the
    # LLM only synthesise prose over it (vs. the legacy LLM-authored report).
    report_evidence_first: bool = Field(default=True)
    # Fetch full page text for retrieved sources (deeper evidence than snippets).
    research_fetch_fulltext: bool = Field(default=True)
    # LLM-plan focused, acronym-expanded search queries before retrieving.
    research_query_planner: bool = Field(default=True)
    research_max_queries: int = Field(default=4)  # planned queries per research step
    research_max_sources: int = Field(default=14)  # merged sources kept per research step


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
