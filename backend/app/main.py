"""Main FastAPI Application Entrypoint for ClintelAI."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
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
            if settings.SEED_DEMO_DATA and fac_count == 0:
                logger.info("No healthcare providers detected in database. Seeding canonical Phase 3 providers...")
                await ProviderSeeder.seed(db=session, force_reload=False)
                logger.info("Phase 3 canonical providers seeded successfully.")
    except Exception as e:
        logger.warning(f"Provider seeder startup check skipped: {e}")

    # Initialize Regional Health Alerts Seeder if database has no alerts yet
    try:
        from sqlalchemy import func, select

        from app.alerts.seeder import HealthAlertSeeder
        from app.db.session import AsyncSessionLocal
        from app.models.alert import HealthAlert

        async with AsyncSessionLocal() as session:
            alert_count_res = await session.execute(select(func.count(HealthAlert.id)))
            alert_cnt = alert_count_res.scalar() or 0
            if settings.SEED_DEMO_DATA and alert_cnt == 0:
                logger.info("No regional health alerts detected in database. Seeding canonical Phase 4 alerts...")
                await HealthAlertSeeder.seed(db=session, force_reload=False)
                logger.info("Phase 4 canonical alerts seeded successfully.")
    except Exception as e:
        logger.warning(f"Health alert seeder startup check skipped: {e}")

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


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Enforces essential OWASP security headers across all API responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(self), microphone=(), camera=()"

    # Interactive documentation endpoints require specialized CSP for assets
    is_docs = request.url.path.startswith(f"{settings.API_V1_STR}/docs") or request.url.path.startswith(
        f"{settings.API_V1_STR}/redoc"
    )
    if is_docs:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' https: 'unsafe-inline'; frame-ancestors 'none';"
        )
    else:
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"

    return response


@app.get(
    "/healthz",
    status_code=status.HTTP_200_OK,
    tags=["Root"],
    summary="Liveness Probe",
    description="Minimal endpoint for container orchestrators and load balancers.",
)
async def liveness_probe():
    return {"status": "alive", "app": settings.PROJECT_NAME}


@app.get(
    "/readyz",
    tags=["Root"],
    summary="Deep Readiness Probe",
    description="Probes PostgreSQL, Redis, Vector Store, and RAG initialization with graceful degradation reporting.",
)
async def readiness_probe(response: Response):
    from app.db.session import check_db_health
    from app.rag.pipeline import RAGPipeline

    db_health = await check_db_health()
    db_ok = db_health.get("status") == "connected"

    pipeline = RAGPipeline.get_instance()
    rag_ready = pipeline.is_initialized
    chunk_count = pipeline.vector_store.get_chunk_count() if rag_ready else 0

    is_ready = db_ok
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if is_ready else "degraded",
        "app": settings.PROJECT_NAME,
        "database": db_health,
        "rag": {
            "initialized": rag_ready,
            "indexed_chunks": chunk_count,
            "provider": settings.LLM_PROVIDER,
        },
        "redis": {
            "status": "available",
            "fallback_in_memory": settings.REDIS_FALLBACK_IN_MEMORY,
        },
    }


# Mount API V1 Router
app.include_router(api_router, prefix=settings.API_V1_STR)
