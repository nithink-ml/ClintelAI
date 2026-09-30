"""Central API router mounting all versioned endpoint sub-routers."""

from fastapi import APIRouter

from app.api.v1 import health

api_router = APIRouter()

# Mount health routes
api_router.include_router(health.router, tags=["Health & Diagnostics"])
