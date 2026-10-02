"""Main FastAPI Application Entrypoint for ClintelAI."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management."""
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT}]")
    logger.info(f"Configured LLM Provider: {settings.LLM_PROVIDER}")
    logger.info(f"Configured Vector Store: {settings.VECTOR_DB_TYPE}")

    # Initialize RAG knowledge ingestion and vector indexing
    try:
        from app.rag.pipeline import RAGPipeline

        pipeline = RAGPipeline.get_instance()
        await pipeline.initialize()
    except Exception as e:
        logger.error(f"Failed to eagerly initialize RAG pipeline during startup: {e}")

    # Initialize Provider Seeder if database has no facilities yet
    try:
        from sqlalchemy import func, select

        from app.db.session import AsyncSessionLocal
        from app.models.provider import Facility
        from app.providers.seeder import ProviderSeeder

        async with AsyncSessionLocal() as session:
            count_res = await session.execute(select(func.count(Facility.id)))
            fac_count = count_res.scalar() or 0
            if fac_count == 0:
                logger.info("No healthcare providers detected in database. Seeding canonical Phase 3 providers...")
                await ProviderSeeder.seed(db=session, force_reload=False)
                logger.info("Phase 3 canonical providers seeded successfully.")
    except Exception as e:
        logger.warning(f"Provider seeder startup check skipped: {e}")

    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}")



app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Multilingual, Trusted-Source Healthcare Intelligence Platform API",
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/healthz",
    status_code=status.HTTP_200_OK,
    tags=["Root"],
    summary="Liveness Probe",
    description="Minimal endpoint for container orchestrators and load balancers.",
)
async def liveness_probe():
    return {"status": "alive", "app": settings.PROJECT_NAME}


# Mount API V1 Router
app.include_router(api_router, prefix=settings.API_V1_STR)
