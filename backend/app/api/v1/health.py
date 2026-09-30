"""Health check endpoints for ClintelAI."""

from fastapi import APIRouter, status

from app.core.config import settings
from app.db.session import check_db_health
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Comprehensive Service Health Check",
    description="Returns the operational status of the core API, database connectivity, and subsystems.",
)
async def get_health_status() -> HealthResponse:
    db_health = await check_db_health()

    services_status = {
        "api": {"status": "operational", "version": settings.VERSION},
        "database": db_health,
        "redis": {
            "status": "configured",
            "url": settings.REDIS_URL,
            "in_memory_fallback": settings.REDIS_FALLBACK_IN_MEMORY,
        },
        "llm_provider": {
            "status": "configured",
            "provider": settings.LLM_PROVIDER,
            "mock_mode": settings.LLM_PROVIDER == "mock",
        },
        "vector_store": {
            "status": "configured",
            "type": settings.VECTOR_DB_TYPE,
            "persist_dir": settings.CHROMA_PERSIST_DIR,
        },
    }

    # Overall system status
    overall_status = "ok" if db_health.get("status") == "connected" else "degraded"

    return HealthResponse(
        status=overall_status,
        app_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        services=services_status,
    )
