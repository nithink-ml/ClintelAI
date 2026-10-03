"""Central API router mounting all versioned endpoint sub-routers."""

from fastapi import APIRouter

from app.api.v1 import alerts, auth, health, providers, rag, users

api_router = APIRouter()

# Mount health routes
api_router.include_router(health.router, tags=["Health & Diagnostics"])

# Mount authentication routes
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# Mount users and preferences routes
api_router.include_router(users.router, prefix="/users", tags=["Users & Preferences"])

# Mount clinical RAG and knowledge retrieval routes
api_router.include_router(rag.router, prefix="/rag", tags=["Clinical RAG & Knowledge Retrieval"])

# Mount provider discovery and verification routes
api_router.include_router(providers.router, prefix="/providers", tags=["Doctor & Clinic Discovery"])

# Mount regional health alerts routes
api_router.include_router(alerts.router, prefix="/alerts", tags=["Regional Health Alerts"])

