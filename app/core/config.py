"""Application configuration, loaded from environment / .env.

Central, typed settings so the rest of the app never reads os.environ directly.
"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

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


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
