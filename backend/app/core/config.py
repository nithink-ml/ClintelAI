"""Application configuration settings."""

import json

from pydantic import field_validator, model_validator
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

    # Database Connection Pool Parameters
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # API Rate Limiting & Abuse Protection
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT_PER_MINUTE: int = 60
    RATE_LIMIT_AUTH_PER_MINUTE: int = 15
    RATE_LIMIT_RAG_PER_MINUTE: int = 30

    # Demo Data Ingestion Controls
    SEED_DEMO_DATA: bool = True

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    @model_validator(mode="after")
    def validate_production_environment(self) -> "Settings":
        """Enforces strict production security constraints and forbids insecure defaults."""
        if self.ENVIRONMENT.lower() == "production":
            if self.DEBUG:
                raise ValueError("DEBUG must be False in production environments.")

            insecure_keys = {
                "insecure-dev-secret-key-change-me-in-production-minimum-32-chars",
                "secret",
                "changeme",
                "password",
            }
            if self.SECRET_KEY in insecure_keys or len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "SECRET_KEY is insecure or too short for production. "
                    "Must be an unpredictable, cryptographically random secret of at least 32 characters."
                )

            if self.LLM_FALLBACK_ENABLED:
                raise ValueError(
                    "LLM_FALLBACK_ENABLED must be False in production to prevent silent mock substitutions."
                )

            if isinstance(self.CORS_ORIGINS, list) and ("*" in self.CORS_ORIGINS):
                raise ValueError(
                    "Wildcard CORS origin ('*') is strictly forbidden in production when allow_credentials=True."
                )

        return self


settings = Settings()
