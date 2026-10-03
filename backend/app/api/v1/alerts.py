"""API Endpoints for Regional Health Alerts, Advisories, and Epidemiological Notifications."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.alerts.schemas import (
    HealthAlertCreateRequest,
    HealthAlertDetail,
    HealthAlertSearchResponse,
    HealthAlertUpdateRequest,
)
from app.alerts.seeder import HealthAlertSeeder
from app.alerts.service import HealthAlertService
from app.api.deps import get_db, log_audit_event, require_role
from app.core.logging import logger
from app.models.alert import AlertCategory, AlertSeverity, AlertStatus
from app.models.user import User

router = APIRouter()
alert_service = HealthAlertService()


@router.get(
    "/search",
    response_model=HealthAlertSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search Regional Health Alerts",
    description=(
        "Queries official, trusted public health alerts and bulletins using geospatial proximity or regional boundaries. "
        "Provides temporal freshness ratings, multilingual localization, and emergency red-flag escalation interception. "
        "Note: Health alerts are informative public notices and never constitute individual diagnosis or clinical advice."
    ),
)
async def search_alerts(
    request: Request,
    query: str | None = Query(None, description="Search term (condition, pathogen, or advisory keyword)"),
    lat: float | None = Query(None, ge=-90.0, le=90.0, description="User latitude for distance sorting"),
    lon: float | None = Query(None, ge=-180.0, le=180.0, description="User longitude for distance sorting"),
    state: str | None = Query(None, description="State filter (e.g., Tamil Nadu, Kerala, Karnataka)"),
    district: str | None = Query(None, description="District filter (e.g., Chennai, Kozhikode, Bengaluru)"),
    city: str | None = Query(None, description="City filter"),
    category: str | None = Query(
        None,
        description="Filter by category: infectious_disease, outbreak, air_quality, heatwave, seasonal_epidemic, etc.",
    ),
    severity: str | None = Query(
        None,
        description="Filter by severity: CRITICAL, HIGH, MODERATE, LOW, INFORMATIONAL",
    ),
    alert_status: str | None = Query(
        "ACTIVE",
        alias="status",
        description="Filter by status: ACTIVE, EXPIRED, DRAFT, INFORMATIONAL, or empty for all",
    ),
    language: str = Query("en", description="Target language ('en', 'ta', 'hi', 'ml', 'te', 'kn')"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=50, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> HealthAlertSearchResponse:
    try:
        # Privacy Guardrail: Log coarse search context only without persisting exact coordinates
        coarse_loc = city or district or state or ("spatial_lookup" if (lat and lon) else "national")
        logger.info(
            f"Alert search requested: query='{query}', location='{coarse_loc}', "
            f"category='{category}', severity='{severity}', status='{alert_status}', lang='{language}'"
        )

        response = await alert_service.search_alerts(
            db=db,
            query=query,
            lat=lat,
            lon=lon,
            state=state,
            district=district,
            city=city,
            category=category,
            severity=severity,
            status=None if (alert_status and alert_status.upper() == "ALL") else alert_status,
            language=language,
            page=page,
            page_size=page_size,
        )
        return response
    except Exception as exc:
        logger.error(f"Error executing health alert search: {exc!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while retrieving regional health alerts: {exc!s}",
        ) from exc


@router.get(
    "/meta/categories",
    status_code=status.HTTP_200_OK,
    summary="List Alert Metadata and Filtering Enums",
    description="Returns available categories, severities, and status options for UI filters.",
)
async def get_alert_metadata():
    return {
        "categories": [c.value for c in AlertCategory],
        "severities": [s.value for s in AlertSeverity],
        "statuses": [st.value for st in AlertStatus],
    }


@router.get(
    "/{alert_id}",
    response_model=HealthAlertDetail,
    status_code=status.HTTP_200_OK,
    summary="Get Health Alert Dossier",
    description="Fetches full advisory dossier including symptoms, precautionary measures, helplines, and localized content.",
)
async def get_alert_detail(
    alert_id: UUID,
    language: str = Query("en", description="Target language ('en', 'ta', 'hi', 'ml', 'te', 'kn')"),
    db: AsyncSession = Depends(get_db),
) -> HealthAlertDetail:
    alert = await alert_service.get_alert_detail(db, alert_id=alert_id, language=language)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Health alert with ID '{alert_id}' was not found.",
        )
    return alert


@router.post(
    "",
    response_model=HealthAlertDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest Official Public Health Alert (RBAC Protected)",
    description=(
        "Restricted to administrators and accredited public health authorities. "
        "Strictly verifies trusted institutional origin (MoHFW, NCDC, WHO, State Health Depts). "
        "Rejects unverified claims, rumors, and social media posts."
    ),
)
async def create_alert(
    req: HealthAlertCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "health_authority")),
) -> HealthAlertDetail:
    try:
        alert = await alert_service.create_alert(db=db, req=req)
        await log_audit_event(
            db=db,
            action="HEALTH_ALERT_INGESTED",
            user_id=current_user.id,
            request=request,
            details={
                "alert_id": str(alert.id),
                "title": alert.title,
                "source_name": alert.source_name,
                "source_url": alert.source_url,
                "severity": alert.severity,
                "category": alert.category,
                "state": alert.state,
                "is_demo_data": alert.is_demo_data,
            },
        )
        return alert
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        ) from ve
    except Exception as exc:
        logger.error(f"Failed to ingest health alert: {exc!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest health alert: {exc!s}",
        ) from exc


@router.patch(
    "/{alert_id}",
    response_model=HealthAlertDetail,
    status_code=status.HTTP_200_OK,
    summary="Update Health Alert Advisory (RBAC Protected)",
    description="Allows administrators and health authorities to update status, validity, or clinical guidance.",
)
async def update_alert(
    alert_id: UUID,
    req: HealthAlertUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "health_authority")),
) -> HealthAlertDetail:
    alert = await alert_service.update_alert(db=db, alert_id=alert_id, req=req)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Health alert with ID '{alert_id}' was not found.",
        )
    await log_audit_event(
        db=db,
        action="HEALTH_ALERT_UPDATED",
        user_id=current_user.id,
        request=request,
        details={
            "alert_id": str(alert_id),
            "updated_by": current_user.email,
        },
    )
    return alert


@router.post(
    "/sync",
    status_code=status.HTTP_200_OK,
    summary="Synchronize Canonical Public Health Alerts (Admin Only)",
    description="Loads or refreshes the baseline verified canonical public health advisories dataset into PostGIS.",
)
async def sync_canonical_alerts(
    request: Request,
    force_reload: bool = Query(True, description="Overwrite existing records with canonical file contents"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    stats = await HealthAlertSeeder.seed(db=db, force_reload=force_reload)
    await log_audit_event(
        db=db,
        action="HEALTH_ALERTS_SYNCHRONIZED",
        user_id=current_user.id,
        request=request,
        details=stats,
    )
    return {
        "status": "success",
        "message": "Canonical public health alerts successfully synchronized.",
        "stats": stats,
    }
