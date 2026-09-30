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
