"""Pydantic schemas for authentication tokens."""

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    """Token response returned upon successful authentication or refresh."""

    access_token: str = Field(..., description="Signed JWT access token")
    refresh_token: str = Field(..., description="Signed JWT refresh token")
    token_type: str = Field(default="bearer", description="Token scheme type")
    expires_in: int = Field(..., description="Access token expiration in seconds")


class RefreshTokenRequest(BaseModel):
    """Request payload for rotating a refresh token."""

    refresh_token: str = Field(..., description="Valid refresh token previously issued")
