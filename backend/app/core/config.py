"""Application configuration settings."""

import json

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "ClintelAI"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Security & Authentication
    SECRET_KEY: str = "insecure-dev-secret-key-change-me-in-production-minimum-32-chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 7 days

    # CORS
    CORS_ORIGINS: list[str] | str = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str) and v.startswith("["):
            return json.loads(v)
        return v

    # Database URLs
    DATABASE_URL: str = (
        "postgresql+asyncpg://clintelai:clintelai_password@localhost:5432/clintelai_db"
    )
    DATABASE_FALLBACK_URL: str = "sqlite+aiosqlite:///./clintelai_dev.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_FALLBACK_IN_MEMORY: bool = True

    # Vector DB
    VECTOR_DB_TYPE: str = "chroma"
    CHROMA_PERSIST_DIR: str = "./chroma_data"
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000

    # LLM & RAG
    LLM_PROVIDER: str = "mock"
    LLM_FALLBACK_ENABLED: bool = False
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    RAG_SIMILARITY_THRESHOLD: float = 0.45
    RAG_MAX_EVIDENCE_CHUNKS: int = 4

    # Maps
    MAPS_PROVIDER: str = "osm"
    MAPBOX_ACCESS_TOKEN: str = ""
    GOOGLE_MAPS_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )


settings = Settings()
