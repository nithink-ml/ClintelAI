"""Database session and engine initialization."""

import sys
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool

from app.core.config import settings
from app.core.logging import logger

Base = declarative_base()

# Primary Engine (PostgreSQL PostGIS in prod/docker, or SQLite in local dev)
primary_url = settings.DATABASE_URL
is_testing = "pytest" in sys.modules or any("pytest" in arg for arg in sys.argv)
engine_kwargs: dict = {
    "echo": False,
    "future": True,
    "pool_pre_ping": True,
}
if is_testing:
    engine_kwargs["poolclass"] = NullPool
elif "sqlite" not in primary_url:
    engine_kwargs["poolclass"] = AsyncAdaptedQueuePool
    engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
    engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
    engine_kwargs["pool_timeout"] = settings.DB_POOL_TIMEOUT
    engine_kwargs["pool_recycle"] = settings.DB_POOL_RECYCLE

engine = create_async_engine(primary_url, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining an asynchronous database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def check_db_health() -> dict:
    """Verifies database connectivity and returns status metadata."""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            val = result.scalar()
            return {
                "status": "connected" if val == 1 else "unhealthy",
                "engine": engine.url.drivername,
                "database": engine.url.database or "default",
            }
    except Exception as exc:
        logger.warning(f"Database health check failed on primary connection: {exc!s}")
        return {
            "status": "disconnected",
            "engine": engine.url.drivername,
            "error": str(exc),
            "note": "Ensure Docker Compose is running ('docker compose up -d postgres') or configure DATABASE_FALLBACK_URL.",
        }
