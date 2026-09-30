"""Central API router mounting all versioned endpoint sub-routers."""

from fastapi import APIRouter

from app.api.v1 import auth, health, users

api_router = APIRouter()

# Mount health routes
api_router.include_router(health.router, tags=["Health & Diagnostics"])

# Mount authentication routes
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# Mount users and preferences routes
api_router.include_router(users.router, prefix="/users", tags=["Users & Preferences"])
