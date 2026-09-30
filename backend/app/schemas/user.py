"""Pydantic schemas for user registration, authentication, and full profile details."""

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.emergency_contact import EmergencyContactResponse
from app.schemas.preference import LanguageCode, PreferenceResponse
from app.schemas.profile import ProfileResponse


class UserRegisterRequest(BaseModel):
    """Payload for creating a new user account."""

    email: EmailStr = Field(..., description="Valid user email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (min 8 chars, must contain letters and numbers)",
    )
    full_name: str = Field(..., min_length=2, max_length=255, description="Full legal name")
    preferred_language: LanguageCode = Field(
        default="en", description="Initial language preference (en, ta, hi, ml, te, kn)"
    )

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Password must contain at least one letter.")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit.")
        return v


class UserLoginRequest(BaseModel):
    """Payload for logging into an existing account."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="Account password")


class UserResponse(BaseModel):
    """Public representation of user identity."""

    id: uuid.UUID
    email: EmailStr
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserDetailResponse(UserResponse):
    """Extended user representation with profile, preferences, and emergency contacts."""

    profile: ProfileResponse | None = None
    preferences: PreferenceResponse | None = None
    emergency_contacts: list[EmergencyContactResponse] = []

    model_config = ConfigDict(from_attributes=True)
